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
import socket
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    # Only fields that map to a header HMRC expects for WEB_APP_VIA_SERVER.
    # 'plugins' and 'do_not_track' were sent by older builds but are NOT part
    # of the WEB_APP_VIA_SERVER spec - we no longer persist them.
    allowed = {
        'js_user_agent',
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


def _client_public_ip_timestamp() -> str:
    """
    Timestamp at which Gov-Client-Public-IP was collected.

    HMRC requires UTC ISO 8601 with milliseconds and a trailing 'Z':
    ``yyyy-MM-ddThh:mm:ss.sssZ``.
    """
    if not _in_request_context():
        return ''
    now = datetime.now(timezone.utc)
    # %f gives microseconds; trim to milliseconds.
    return now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{now.microsecond // 1000:03d}Z'


def _client_public_port() -> str:
    if not _in_request_context():
        return ''
    # behind nginx this is X-Forwarded-Port; otherwise request.environ
    return request.headers.get('X-Forwarded-Port') or str(request.environ.get('REMOTE_PORT') or '')


def _format_utc_offset(td) -> str:
    """Format a `timedelta` UTC offset as ``UTC±hh:mm`` per HMRC spec."""
    total = int(td.total_seconds())
    sign = '+' if total >= 0 else '-'
    total = abs(total)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f'UTC{sign}{hours:02d}:{minutes:02d}'


def _client_timezone() -> str:
    """
    Browser-reported timezone, normalised to HMRC's required ``UTC±hh:mm``
    format.

    The JS captures an IANA name (e.g. ``Europe/London``); HMRC rejects
    that form, so resolve it against the current instant to obtain the
    actual offset (which correctly handles DST).
    """
    tz = _ctx().get('timezone') or ''
    if tz:
        try:
            offset = datetime.now(ZoneInfo(tz)).utcoffset()
            if offset is not None:
                return _format_utc_offset(offset)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    # Fallback: server's local offset.
    offset = datetime.now(timezone.utc).astimezone().utcoffset()
    return _format_utc_offset(offset) if offset is not None else 'UTC+00:00'


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


def _client_user_ids() -> str:
    """
    Identifiers for the user driving the request, percent-encoded per
    RFC 3986. Format: ``<account-key>=<identifier>``.

    HMRC requires this for WEB_APP_VIA_SERVER. We expose the locally
    authenticated Flask-Login user (username, falling back to email or
    user id). Separators (``=`` and ``&``) are kept literal; values are
    percent-encoded.
    """
    if not _in_request_context():
        return ''
    try:
        from flask_login import current_user
        if not getattr(current_user, 'is_authenticated', False):
            return ''
        identifier = (
            getattr(current_user, 'username', None)
            or getattr(current_user, 'email', None)
            or str(getattr(current_user, 'id', '') or '')
        )
        if not identifier:
            return ''
        return f'tvs-wages={_pct(str(identifier))}'
    except Exception:  # noqa: BLE001
        return ''


def _client_multi_factor() -> str:
    # We do not yet enforce MFA. HMRC accepts the header being absent
    # provided the application authenticates with username + password
    # only - which is our case (see the 'missing data' guidance).
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
    # Per HMRC spec the value must be percent-encoded.
    return _pct('TVS Wages')


def _vendor_version() -> str:
    return f"TVS-Wages={Config.VERSION}"


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
    # Only headers listed by HMRC for WEB_APP_VIA_SERVER. Anything else
    # the validator team flags as 'unexpected'.
    headers = {
        'Gov-Client-Connection-Method': 'WEB_APP_VIA_SERVER',
        'Gov-Client-Browser-JS-User-Agent': _client_browser_js_user_agent(),
        'Gov-Client-Device-ID': _client_device_id(),
        'Gov-Client-Multi-Factor': _client_multi_factor(),
        'Gov-Client-Public-IP': _client_public_ip(),
        'Gov-Client-Public-IP-Timestamp': _client_public_ip_timestamp(),
        'Gov-Client-Public-Port': _client_public_port(),
        'Gov-Client-Screens': _client_screens(),
        'Gov-Client-Timezone': _client_timezone(),
        'Gov-Client-User-IDs': _client_user_ids(),
        'Gov-Client-Window-Size': _client_window_size(),
        'Gov-Vendor-Forwarded': _vendor_forwarded(),
        'Gov-Vendor-License-IDs': _vendor_license_ids(),
        'Gov-Vendor-Product-Name': _vendor_product_name(),
        'Gov-Vendor-Public-IP': _vendor_public_ip(),
        'Gov-Vendor-Version': _vendor_version(),
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
            'Gov-Client-User-IDs',
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
