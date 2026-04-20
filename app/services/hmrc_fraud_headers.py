"""
HMRC MTD fraud prevention header builder.

Implements the WEB_APP_VIA_SERVER connection method per HMRC's
"Fraud prevention headers" specification. The client-side (browser)
details are captured by a small JS snippet that POSTs to
/api/hmrc/fraud-headers/record on page load; they are cached in the
Flask session and replayed on every HMRC API call.

Reference: https://developer.service.hmrc.gov.uk/guides/fraud-prevention/
"""

from __future__ import annotations

import hashlib
import logging
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from flask import request, session

from ..config import Config

logger = logging.getLogger('hmrc')


# -- RFC 3986 encoding helper ------------------------------------------------

def _pct(value: str) -> str:
    """Percent-encode a value per RFC 3986 for structured HMRC headers."""
    return quote(value, safe='')


# -- Session capture (called from the /record endpoint) ---------------------

def record_browser_context(data: dict) -> None:
    """
    Persist browser-supplied fraud-prevention fields into the Flask session.
    Called by the /api/hmrc/fraud-headers/record endpoint on every page load
    of an HMRC page.
    """
    allowed = {
        'js_user_agent', 'plugins', 'do_not_track',
        'window_width', 'window_height',
        'screen_width', 'screen_height', 'screen_scaling', 'screen_colour_depth',
        'timezone', 'device_id',
    }
    fp = session.get('hmrc_fraud_ctx', {})
    for k, v in (data or {}).items():
        if k in allowed and v is not None:
            fp[k] = str(v)[:512]  # safety cap
    fp['captured_at'] = datetime.now(timezone.utc).isoformat()
    session['hmrc_fraud_ctx'] = fp


def _ctx() -> dict:
    return session.get('hmrc_fraud_ctx', {}) if _in_request_context() else {}


def _in_request_context() -> bool:
    try:
        _ = request.path  # noqa: F841
        return True
    except RuntimeError:
        return False


# -- Individual header builders ---------------------------------------------

def _client_public_ip() -> str:
    """The end-user browser's public IP.

    In a reverse-proxied deploy this is in X-Forwarded-For; fall back to
    remote_addr.
    """
    if not _in_request_context():
        return ''
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr or ''


def _client_public_port() -> str:
    if not _in_request_context():
        return ''
    # behind nginx this is X-Forwarded-Port; otherwise request.environ
    return request.headers.get('X-Forwarded-Port') or str(request.environ.get('REMOTE_PORT') or '')


def _client_user_agent() -> str:
    if not _in_request_context():
        return ''
    return request.headers.get('User-Agent', '')


def _client_timezone() -> str:
    """Prefer the browser-reported IANA zone; fall back to server offset."""
    tz = _ctx().get('timezone')
    if tz:
        return tz
    offset = datetime.now(timezone.utc).astimezone().strftime('%z')
    if len(offset) == 5:
        return f"UTC{offset[:3]}:{offset[3:]}"
    return 'UTC+00:00'


def _client_device_id() -> str:
    """
    Stable device ID for the current browser. Browser-sent if available
    (JS generates a UUIDv4 on first visit and stores it in localStorage);
    otherwise derive one from the MAC of the server as a last resort so
    the header is never empty.
    """
    bid = _ctx().get('device_id')
    if bid:
        return bid
    mac = uuid.getnode()
    return hashlib.sha256(f'tvstcms-fallback-{mac}'.encode()).hexdigest()


def _client_screens() -> str:
    c = _ctx()
    w = c.get('screen_width') or ''
    h = c.get('screen_height') or ''
    s = c.get('screen_scaling') or '1'
    d = c.get('screen_colour_depth') or '24'
    if not (w and h):
        return ''
    return f"width={w}&height={h}&scaling-factor={s}&colour-depth={d}"


def _client_window_size() -> str:
    c = _ctx()
    w = c.get('window_width') or ''
    h = c.get('window_height') or ''
    if not (w and h):
        return ''
    return f"width={w}&height={h}"


def _client_browser_js_user_agent() -> str:
    return _ctx().get('js_user_agent', '')


def _client_browser_plugins() -> str:
    # Already comma-separated percent-encoded from the JS side.
    return _ctx().get('plugins', '')


def _client_browser_do_not_track() -> str:
    v = _ctx().get('do_not_track')
    if v in ('1', 'true', 'yes'):
        return 'true'
    if v in ('0', 'false', 'no'):
        return 'false'
    return 'false'


def _client_multi_factor() -> str:
    # We do not yet enforce MFA. HMRC accepts an empty list:
    return ''


# -- Vendor headers (server-side) -------------------------------------------

def _vendor_public_ip() -> str:
    """
    The server's public IP. Cached on the Config instance to avoid a
    per-request external call. Override via HMRC_VENDOR_PUBLIC_IP env var.
    """
    import os
    return os.environ.get('HMRC_VENDOR_PUBLIC_IP', '') or _cached_public_ip()


_CACHED_PUBLIC_IP: Optional[str] = None


def _cached_public_ip() -> str:
    global _CACHED_PUBLIC_IP
    if _CACHED_PUBLIC_IP is not None:
        return _CACHED_PUBLIC_IP
    try:
        import requests
        r = requests.get('https://api.ipify.org?format=json', timeout=5)
        _CACHED_PUBLIC_IP = r.json().get('ip', '')
    except Exception as e:  # noqa: BLE001
        logger.warning(f'Could not determine vendor public IP: {e}')
        _CACHED_PUBLIC_IP = ''
    return _CACHED_PUBLIC_IP


def _vendor_local_ips() -> str:
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except OSError:
        return ''


def _vendor_product_name() -> str:
    return 'TVS TCMS'


def _vendor_version() -> str:
    return f"TVS-TCMS={Config.VERSION}"


def _vendor_license_ids() -> str:
    # No commercial license — single-user self-hosted. Empty is allowed.
    import os
    return os.environ.get('HMRC_VENDOR_LICENSE_IDS', '')


def _vendor_forwarded() -> str:
    """HMRC expects a chain of hops separated by &:  by=<server-ip>&for=<client-ip>."""
    server = _vendor_public_ip()
    client = _client_public_ip()
    if not (server or client):
        return ''
    return f"by={server}&for={client}"


# -- Assembly ---------------------------------------------------------------

def build_fraud_prevention_headers() -> dict:
    """
    Build the full set of fraud prevention headers for WEB_APP_VIA_SERVER.

    Values absent because we are outside a request context (e.g. a batch job)
    or because the browser hasn't reported yet are omitted from the payload.
    HMRC rejects known-required headers if missing, so callers should log a
    warning in production when this set is incomplete.
    """
    headers = {
        'Gov-Client-Connection-Method': 'WEB_APP_VIA_SERVER',
        'Gov-Client-Public-IP': _client_public_ip(),
        'Gov-Client-Public-Port': _client_public_port(),
        'Gov-Client-Device-ID': _client_device_id(),
        'Gov-Client-User-Agent': _client_user_agent(),
        'Gov-Client-Timezone': _client_timezone(),
        'Gov-Client-Screens': _client_screens(),
        'Gov-Client-Window-Size': _client_window_size(),
        'Gov-Client-Browser-JS-User-Agent': _client_browser_js_user_agent(),
        'Gov-Client-Browser-Plugins': _client_browser_plugins(),
        'Gov-Client-Browser-Do-Not-Track': _client_browser_do_not_track(),
        'Gov-Client-Multi-Factor': _client_multi_factor(),
        'Gov-Vendor-Version': _vendor_version(),
        'Gov-Vendor-Product-Name': _vendor_product_name(),
        'Gov-Vendor-License-IDs': _vendor_license_ids(),
        'Gov-Vendor-Public-IP': _vendor_public_ip(),
        'Gov-Vendor-Forwarded': _vendor_forwarded(),
    }

    # Strip empty-string values - HMRC prefers the header absent to being blank.
    headers = {k: v for k, v in headers.items() if v}

    # In production, loudly flag missing browser-sourced values which will
    # cause HMRC to reject the request.
    if Config.HMRC_ENVIRONMENT == 'production':
        required_browser = (
            'Gov-Client-Browser-JS-User-Agent',
            'Gov-Client-Screens',
            'Gov-Client-Window-Size',
        )
        missing = [h for h in required_browser if h not in headers]
        if missing:
            logger.warning(
                'HMRC fraud prevention headers incomplete (missing: %s). '
                'Browser context has not been recorded in the session yet. '
                'Submission may be rejected.',
                ', '.join(missing),
            )

    return headers
