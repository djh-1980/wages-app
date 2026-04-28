"""
Periods of Account service.

A "Period of Account" is the accounting period a sole trader uses for
their business in a given tax year. HMRC's Business Details API v2.0
exposes Retrieve / Create / Update / Delete endpoints for this concept.

For a standard tax-year-aligned sole trader (Daniel's case), the period
of account is simply ``6 April YYYY -> 5 April YYYY+1``. Non-standard
traders may declare a different window (e.g. April->March, calendar
year, etc.).

This service is the single source of truth for the **local** record of
periods of account. It does not call HMRC - the HMRC client and routes
layer takes care of synchronising. Keeping this layer pure keeps it
cheap to unit-test and lets the routes layer compose local writes with
remote calls in a controlled order.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Optional

from ..database import get_db_connection
from .hmrc_cumulative_calculator import parse_tax_year

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _to_iso(value: Any) -> str:
    """Normalise a YYYY-MM-DD or DD/MM/YYYY string (or date) to ISO."""
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError(f'Invalid date value: {value!r}')
    s = value.strip()
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        # Validate it parses
        datetime.strptime(s, '%Y-%m-%d')
        return s
    if len(s) == 10 and s[2] == '/' and s[5] == '/':
        dd, mm, yyyy = s.split('/')
        d = datetime.strptime(f'{yyyy}-{mm}-{dd}', '%Y-%m-%d')
        return d.date().isoformat()
    raise ValueError(f'Invalid date value: {value!r}')


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return {k: row[k] for k in row.keys()}


def _validate_dates(start_iso: str, end_iso: str) -> None:
    """Raise ValueError if start >= end."""
    start = datetime.strptime(start_iso, '%Y-%m-%d').date()
    end = datetime.strptime(end_iso, '%Y-%m-%d').date()
    if start >= end:
        raise ValueError(
            f'Period start ({start_iso}) must be before end ({end_iso})'
        )


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------

def get_for_tax_year(tax_year: str) -> Optional[dict]:
    """Return the active (non-deleted) period for ``tax_year``, or None."""
    if not tax_year:
        return None
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, business_id, period_id, tax_year,
                   period_start_date, period_end_date, period_type,
                   created_at, updated_at, deleted_at
              FROM periods_of_account
             WHERE tax_year = ?
               AND deleted_at IS NULL
             ORDER BY id DESC
             LIMIT 1
            """,
            (tax_year,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def list_periods(include_deleted: bool = False) -> list:
    """Return all periods (most recent first)."""
    query = """
        SELECT id, business_id, period_id, tax_year,
               period_start_date, period_end_date, period_type,
               created_at, updated_at, deleted_at
          FROM periods_of_account
    """
    if not include_deleted:
        query += ' WHERE deleted_at IS NULL'
    query += ' ORDER BY tax_year DESC, id DESC'

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return [_row_to_dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def standard_period_dates(tax_year: str) -> tuple:
    """Return the standard (6 April -> 5 April) ISO date pair for ``tax_year``.

    Raises ValueError on a malformed tax-year string.
    """
    start_year = parse_tax_year(tax_year)
    return (
        date(start_year, 4, 6).isoformat(),
        date(start_year + 1, 4, 5).isoformat(),
    )


def create_standard_period(
    tax_year: str,
    business_id: Optional[str] = None,
) -> dict:
    """Create the default 6 April -> 5 April period for ``tax_year``.

    If an active period already exists for the tax year, returns it
    unchanged (idempotent). The caller can update it explicitly via
    :func:`update_period` if they need different dates.
    """
    existing = get_for_tax_year(tax_year)
    if existing is not None:
        return existing

    start_iso, end_iso = standard_period_dates(tax_year)
    return _insert_period(
        tax_year=tax_year,
        start_iso=start_iso,
        end_iso=end_iso,
        period_type='standard',
        business_id=business_id,
    )


def create_custom_period(
    tax_year: str,
    start_date: Any,
    end_date: Any,
    business_id: Optional[str] = None,
) -> dict:
    """Create a non-standard period with explicit start/end dates."""
    start_iso = _to_iso(start_date)
    end_iso = _to_iso(end_date)
    _validate_dates(start_iso, end_iso)

    # If an active period already exists for this tax year, fail loudly:
    # the caller should call update_period instead.
    if get_for_tax_year(tax_year) is not None:
        raise ValueError(
            f'A period of account already exists for {tax_year}. '
            'Use update_period to change its dates.'
        )

    # Determine period_type: standard if dates equal 6 Apr -> 5 Apr.
    std_start, std_end = standard_period_dates(tax_year)
    period_type = 'standard' if (start_iso == std_start and end_iso == std_end) else 'non-standard'

    return _insert_period(
        tax_year=tax_year,
        start_iso=start_iso,
        end_iso=end_iso,
        period_type=period_type,
        business_id=business_id,
    )


def _insert_period(
    *,
    tax_year: str,
    start_iso: str,
    end_iso: str,
    period_type: str,
    business_id: Optional[str],
) -> dict:
    """Internal: write one row and return the hydrated record."""
    _validate_dates(start_iso, end_iso)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO periods_of_account
                (business_id, tax_year, period_start_date, period_end_date,
                 period_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (business_id, tax_year, start_iso, end_iso, period_type),
        )
        new_id = cur.lastrowid
        conn.commit()
    logger.info(
        'Created period of account id=%s tax_year=%s %s..%s type=%s',
        new_id, tax_year, start_iso, end_iso, period_type,
    )
    record = get_by_id(new_id)
    if record is None:
        # Should be unreachable - we just inserted it.
        raise RuntimeError(
            f'Failed to read back inserted period of account id={new_id}'
        )
    return record


def get_by_id(period_row_id: int) -> Optional[dict]:
    """Look up a period by its local row id (ignores soft-delete)."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, business_id, period_id, tax_year,
                   period_start_date, period_end_date, period_type,
                   created_at, updated_at, deleted_at
              FROM periods_of_account
             WHERE id = ?
            """,
            (period_row_id,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def update_period(
    tax_year: str,
    *,
    start_date: Any = None,
    end_date: Any = None,
    period_type: Optional[str] = None,
    business_id: Optional[str] = None,
    period_id: Optional[str] = None,
) -> dict:
    """Update the active period for ``tax_year``.

    Any field left as ``None`` is preserved. Raises ValueError if no
    active period exists or if the resulting dates are invalid.
    """
    existing = get_for_tax_year(tax_year)
    if existing is None:
        raise ValueError(f'No active period of account for {tax_year}')

    new_start = _to_iso(start_date) if start_date is not None else existing['period_start_date']
    new_end = _to_iso(end_date) if end_date is not None else existing['period_end_date']
    _validate_dates(new_start, new_end)

    new_type = period_type if period_type is not None else existing['period_type']
    new_business_id = business_id if business_id is not None else existing['business_id']
    new_period_id = period_id if period_id is not None else existing['period_id']

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE periods_of_account
               SET period_start_date = ?,
                   period_end_date = ?,
                   period_type = ?,
                   business_id = ?,
                   period_id = ?,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
            """,
            (
                new_start, new_end, new_type,
                new_business_id, new_period_id, existing['id'],
            ),
        )
        conn.commit()

    logger.info(
        'Updated period of account id=%s tax_year=%s %s..%s type=%s',
        existing['id'], tax_year, new_start, new_end, new_type,
    )
    record = get_by_id(existing['id'])
    if record is None:
        raise RuntimeError(
            f'Failed to re-read updated period of account id={existing["id"]}'
        )
    return record


# ---------------------------------------------------------------------------
# delete (soft)
# ---------------------------------------------------------------------------

def delete_period(tax_year: str) -> bool:
    """Soft-delete the active period for ``tax_year``.

    Returns True if a row was marked deleted, False if there was no
    active period to delete.
    """
    existing = get_for_tax_year(tax_year)
    if existing is None:
        return False

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE periods_of_account
               SET deleted_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
            """,
            (existing['id'],),
        )
        conn.commit()

    logger.info(
        'Soft-deleted period of account id=%s tax_year=%s',
        existing['id'], tax_year,
    )
    return True
