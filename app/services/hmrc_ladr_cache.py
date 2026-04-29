"""LADR cache helper.

The Late Accounting Date Rule is a flag, not a record, so a full mirror
table is overkill. We persist the most-recent-known status in the
existing ``settings`` table, keyed by ``hmrc_ladr_<business_id>_<tax_year>``.
The value is JSON: ``{status, last_synced_at, hmrc_response}``.

This module is the single read/write path for that cache. Routes call
``get`` to read and ``set`` to update after a successful HMRC call.
"""

import json
import logging
from datetime import datetime, timezone

from ..database import get_db_connection


logger = logging.getLogger(__name__)


# Allowed status values - keep in sync with the JS panel.
STATUS_APPLIED = 'Applied'
STATUS_DISAPPLIED = 'Disapplied'
STATUS_UNKNOWN = 'Unknown'

VALID_STATUSES = {STATUS_APPLIED, STATUS_DISAPPLIED, STATUS_UNKNOWN}


def _key(business_id, tax_year):
    """Build the settings-table key for one (business, tax-year) pair."""
    if not business_id or not tax_year:
        raise ValueError('business_id and tax_year are required')
    return f'hmrc_ladr_{business_id}_{tax_year}'


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def derive_status_from_hmrc_data(data):
    """Heuristic: turn an HMRC GET response body into a status string.

    The HMRC v2.0 schema for the LADR retrieve endpoint is not fully
    public (the spec is behind the developer hub) so we accept the most
    common shapes:

    - ``{'lateAccountingDateRuleDisapplied': true}`` -> Disapplied
    - ``{'disapplied': true}``                       -> Disapplied
    - ``{'status': 'Disapplied'}``                   -> Disapplied
    - ``{'status': 'Applied'}``                      -> Applied
    - ``{'disapplications': [...]}`` (non-empty)     -> Disapplied
    - empty dict / None                              -> Unknown
    - anything else with a recognisable 'applied'    -> Applied

    Routes can pass the result of this function straight to ``set``.
    """
    if not isinstance(data, dict) or not data:
        return STATUS_UNKNOWN

    if data.get('lateAccountingDateRuleDisapplied') is True:
        return STATUS_DISAPPLIED
    if data.get('disapplied') is True:
        return STATUS_DISAPPLIED
    if isinstance(data.get('disapplications'), list) and data['disapplications']:
        return STATUS_DISAPPLIED

    explicit = data.get('status')
    if isinstance(explicit, str):
        normalised = explicit.strip().capitalize()
        if normalised in VALID_STATUSES:
            return normalised

    # If HMRC explicitly returned False for either disapply flag, the rule
    # is applied.
    if (
        data.get('lateAccountingDateRuleDisapplied') is False
        or data.get('disapplied') is False
    ):
        return STATUS_APPLIED

    return STATUS_UNKNOWN


def get(business_id, tax_year):
    """Read the cached status. Returns None if the cache is empty.

    Returns:
        dict | None: ``{'status', 'last_synced_at', 'hmrc_response'}`` or
        ``None`` if no entry exists for this (business, tax_year).
    """
    key = _key(business_id, tax_year)
    with get_db_connection() as conn:
        row = conn.execute(
            'SELECT value FROM settings WHERE key = ?', (key,),
        ).fetchone()
    if row is None:
        return None
    raw = row['value'] if hasattr(row, 'keys') else row[0]
    try:
        return json.loads(raw)
    except (TypeError, ValueError) as e:
        logger.warning(f'Corrupt LADR cache entry for {key}: {e}')
        return None


def set(business_id, tax_year, status, hmrc_response=None):  # noqa: A001
    """Upsert the cache for one (business, tax_year). Returns the row dict."""
    if status not in VALID_STATUSES:
        raise ValueError(
            f'Invalid LADR status {status!r}; must be one of {sorted(VALID_STATUSES)}'
        )
    key = _key(business_id, tax_year)
    payload = {
        'status': status,
        'last_synced_at': _now_iso(),
        'hmrc_response': hmrc_response if isinstance(hmrc_response, dict) else None,
    }
    with get_db_connection() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            (key, json.dumps(payload)),
        )
        conn.commit()
    return payload


def clear(business_id, tax_year):
    """Remove the cache entry for one (business, tax_year)."""
    key = _key(business_id, tax_year)
    with get_db_connection() as conn:
        conn.execute('DELETE FROM settings WHERE key = ?', (key,))
        conn.commit()
