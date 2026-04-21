"""
Health check endpoints for external monitoring.

/healthz - basic liveness (is the process alive?)
/readyz  - readiness (can the app actually serve requests?)

These are unauthenticated by design - monitoring systems (Uptime Kuma,
healthchecks.io, Cloudflare health monitors, Kubernetes, etc.) need to
ping them without credentials.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify

from ..database import get_db_connection

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/healthz')
def healthz():
    """Basic liveness check - confirms the Flask app is responding.

    Always returns 200 if the process is alive. Does not touch the
    database, filesystem, or any external service, so it remains fast
    and available even when downstream systems are degraded.
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
    }), 200


@health_bp.route('/readyz')
def readyz():
    """Readiness check - verifies all dependencies are healthy.

    Returns 200 if every check passes, 503 otherwise. The response body
    includes per-check diagnostics so an operator can see which
    dependency is unhealthy without SSH access.
    """
    checks = {
        'database': _check_database(),
        'disk_space': _check_disk_space(),
        'sync_recent': _check_sync_recency(),
        'gmail_auth': _check_gmail_auth(),
    }

    all_healthy = all(check['healthy'] for check in checks.values())

    response = {
        'status': 'ok' if all_healthy else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'checks': checks,
    }

    status_code = 200 if all_healthy else 503
    return jsonify(response), status_code


def _check_database():
    """Verify the database is accessible by running a trivial query."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
        return {
            'healthy': True,
            'message': f'Database accessible, {count} users',
        }
    except Exception as e:
        logger.error(f'Database health check failed: {e}')
        return {
            'healthy': False,
            'message': f'Database error: {str(e)}',
        }


def _check_disk_space():
    """Verify at least 1 GB of free disk space on the working volume."""
    try:
        stat = os.statvfs('.')
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        healthy = free_gb > 1.0
        return {
            'healthy': healthy,
            'message': f'{free_gb:.2f} GB free',
            'free_gb': round(free_gb, 2),
        }
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Disk check error: {str(e)}',
        }


def _check_sync_recency():
    """Verify the periodic sync has run in the last 48 hours.

    Not a hard failure: the sync may legitimately not run if tomorrow's
    data is already in the DB, so a missing ``last_sync_time`` or an
    exception reading the service reports healthy.
    """
    try:
        from ..services.periodic_sync import periodic_sync_service
        last_sync = periodic_sync_service.last_sync_time
        if last_sync is None:
            return {
                'healthy': True,
                'message': 'Sync not yet run (service just started)',
            }

        age_hours = (datetime.now() - last_sync).total_seconds() / 3600
        healthy = age_hours < 48
        return {
            'healthy': healthy,
            'message': f'Last sync {age_hours:.1f} hours ago',
            'last_sync': last_sync.isoformat(),
            'age_hours': round(age_hours, 1),
        }
    except Exception as e:
        return {
            'healthy': True,  # Don't fail readiness on sync check errors
            'message': f'Sync check error: {str(e)}',
        }


def _check_gmail_auth():
    """Verify a Gmail OAuth token file exists and is not empty."""
    try:
        token_path = Path('token.json')
        if not token_path.exists():
            return {
                'healthy': False,
                'message': 'Gmail token.json missing',
            }
        # Don't parse the token content - just verify it exists and isn't empty.
        size = token_path.stat().st_size
        healthy = size > 100  # Valid tokens are several hundred bytes.
        return {
            'healthy': healthy,
            'message': f'Gmail token present ({size} bytes)',
        }
    except Exception as e:
        return {
            'healthy': True,  # Don't fail readiness on auth check errors
            'message': f'Gmail check error: {str(e)}',
        }
