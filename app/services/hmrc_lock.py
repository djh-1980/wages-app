"""
HMRC digital-records lock service.

Once a period has been successfully submitted to HMRC, the underlying records
covering that period (expenses, income, etc.) must not be silently edited.
This module answers the question "is this date locked?" and is the single
point of truth for enforcing the lock across the application.

All dates are ISO-format YYYY-MM-DD strings.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..database import get_db_connection

logger = logging.getLogger(__name__)


def _to_iso(date_str: str) -> Optional[str]:
    """Normalise a date to ISO YYYY-MM-DD. Accepts YYYY-MM-DD or DD/MM/YYYY."""
    if not date_str:
        return None
    s = date_str.strip()
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        return s
    if len(s) == 10 and s[2] == '/' and s[5] == '/':
        dd, mm, yyyy = s.split('/')
        return f'{yyyy}-{mm}-{dd}'
    return None


def is_date_locked(date_str: str) -> bool:
    """
    Return True if any successful HMRC submission covers the given date.

    A submission "covers" a date when:
      status = 'submitted'
      AND locked_at IS NOT NULL
      AND period_start_date <= date <= period_end_date
    """
    iso = _to_iso(date_str)
    if not iso:
        return False
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1
                  FROM hmrc_submissions
                 WHERE status = 'submitted'
                   AND locked_at IS NOT NULL
                   AND period_start_date IS NOT NULL
                   AND period_end_date IS NOT NULL
                   AND period_start_date <= ?
                   AND period_end_date >= ?
                 LIMIT 1
                """,
                (iso, iso),
            )
            return cur.fetchone() is not None
    except Exception as e:  # noqa: BLE001
        logger.error(f'Error checking HMRC lock for date {date_str}: {e}')
        # Fail-closed would block edits on any DB error; fail-open preserves
        # usability. We fail OPEN but log loudly.
        return False


def lock_submission(
    submission_id: int,
    period_start_date: str,
    period_end_date: str,
) -> bool:
    """
    Mark a submission as covering the given period and lock it NOW.

    Called from the submission routes after a successful HMRC response.
    """
    iso_start = _to_iso(period_start_date)
    iso_end = _to_iso(period_end_date)
    if not (iso_start and iso_end):
        logger.warning(
            f'Cannot lock submission {submission_id}: invalid dates '
            f'start={period_start_date!r} end={period_end_date!r}'
        )
        return False
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE hmrc_submissions
                   SET period_start_date = ?,
                       period_end_date = ?,
                       locked_at = COALESCE(locked_at, CURRENT_TIMESTAMP)
                 WHERE id = ?
                """,
                (iso_start, iso_end, submission_id),
            )
            conn.commit()
        logger.info(
            f'HMRC submission {submission_id} locked ({iso_start} → {iso_end})'
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f'Error locking HMRC submission {submission_id}: {e}')
        return False
