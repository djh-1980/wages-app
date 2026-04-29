"""Annual Submission cache helper.

The Annual Submission endpoint accepts allowances + adjustments +
nonFinancials for a tax year. Most sole traders on cash basis will
submit zeroes; HMRC still requires the PUT to be exercised.

This module persists two related artefacts in the existing ``settings``
table - no new migration required:

  hmrc_annual_draft_<business_id>_<tax_year>
      A locally edited draft that has NOT been sent to HMRC yet. Created
      by 'Save Draft' in the UI, cleared after a successful submit.

  hmrc_annual_last_<business_id>_<tax_year>
      The last successfully submitted payload + timestamp + HMRC echo.
      Updated as Phase 2 of the two-phase write in the route layer.

Both values are JSON-encoded dicts.
"""

import json
import logging
from datetime import datetime, timezone

from ..database import get_db_connection


logger = logging.getLogger(__name__)


_DRAFT_PREFIX = 'hmrc_annual_draft'
_LAST_PREFIX = 'hmrc_annual_last'


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _key(prefix, business_id, tax_year):
    if not business_id or not tax_year:
        raise ValueError('business_id and tax_year are required')
    return f'{prefix}_{business_id}_{tax_year}'


def _read(key):
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
        logger.warning(f'Corrupt annual-submission cache entry for {key}: {e}')
        return None


def _write(key, payload):
    with get_db_connection() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            (key, json.dumps(payload)),
        )
        conn.commit()


def _delete(key):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM settings WHERE key = ?', (key,))
        conn.commit()


# ---- draft -----------------------------------------------------------------

def get_draft(business_id, tax_year):
    """Return the local draft, or None if absent."""
    return _read(_key(_DRAFT_PREFIX, business_id, tax_year))


def set_draft(business_id, tax_year, annual_data):
    """Upsert a local draft. Returns the stored payload."""
    if not isinstance(annual_data, dict):
        raise ValueError('annual_data must be a dict')
    payload = {
        'annual_data': annual_data,
        'updated_at': _now_iso(),
    }
    _write(_key(_DRAFT_PREFIX, business_id, tax_year), payload)
    return payload


def clear_draft(business_id, tax_year):
    """Remove the local draft, if any."""
    _delete(_key(_DRAFT_PREFIX, business_id, tax_year))


# ---- last-submitted --------------------------------------------------------

def get_last_submitted(business_id, tax_year):
    """Return the last-submitted record, or None if no submission on file."""
    return _read(_key(_LAST_PREFIX, business_id, tax_year))


def set_last_submitted(business_id, tax_year, annual_data, hmrc_response=None):
    """Record a successful HMRC submission. Returns the stored payload."""
    if not isinstance(annual_data, dict):
        raise ValueError('annual_data must be a dict')
    payload = {
        'annual_data': annual_data,
        'submitted_at': _now_iso(),
        'hmrc_response': hmrc_response if isinstance(hmrc_response, dict) else None,
    }
    _write(_key(_LAST_PREFIX, business_id, tax_year), payload)
    return payload
