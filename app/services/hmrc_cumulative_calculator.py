"""
HMRC cumulative period summary calculator.

Self-Employment Business (MTD) API v5.0 replaced the per-quarter
POST /period endpoint with a cumulative model. Each quarter the trader
submits the running total of income and expenses from 6 April of the
tax year up to the end of the current quarter. The figures sent at the
end of Q2 must include Q1's amounts; Q3 must include Q1 + Q2; Q4
covers the full tax year.

This service is the single source of truth for those running totals.
It deliberately does not call HMRC - it only assembles the dict that
the API client will POST. Keeping it pure makes it cheap to unit-test
without mocking the HMRC sandbox.
"""

import logging
from datetime import date, datetime, timedelta

from ..database import execute_query
from ..models.expense import ExpenseModel
from .hmrc_mapper import HMRCMapper

logger = logging.getLogger('hmrc')


# Quarter end dates (relative to the tax-year start year). HMRC's
# self-employment quarters end on 5 Jul, 5 Oct, 5 Jan, 5 Apr.
_QUARTER_ENDS = (
    ('Q1', 7, 5, 0),    # 5 July of start year
    ('Q2', 10, 5, 0),   # 5 October of start year
    ('Q3', 1, 5, 1),    # 5 January of start year + 1
    ('Q4', 4, 5, 1),    # 5 April of start year + 1
)


def parse_tax_year(tax_year):
    """Normalise a tax year string and return its start year as int.

    Accepts:
        - 'YYYY-YY'   (HMRC canonical, e.g. '2025-26')
        - 'YYYY/YYYY' (legacy app format, e.g. '2025/2026')

    Returns:
        int: the start year (e.g. 2025).

    Raises:
        ValueError: if the format is not recognised.
    """
    if not tax_year or not isinstance(tax_year, str):
        raise ValueError(f'Invalid tax year: {tax_year!r}')

    if '/' in tax_year:
        parts = tax_year.split('/')
        if len(parts) != 2 or not parts[0].isdigit():
            raise ValueError(f'Invalid tax year format: {tax_year!r}')
        return int(parts[0])

    if '-' in tax_year:
        parts = tax_year.split('-')
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f'Invalid tax year format: {tax_year!r}')
        return int(parts[0])

    raise ValueError(f'Unrecognised tax year format: {tax_year!r}')


def tax_year_start(tax_year):
    """Return the date of 6 April for the given tax year (start)."""
    start_year = parse_tax_year(tax_year)
    return date(start_year, 4, 6)


def quarter_end_date(tax_year, period_id):
    """Return the inclusive end date for a given quarter of a tax year.

    Args:
        tax_year: 'YYYY-YY' or 'YYYY/YYYY'.
        period_id: 'Q1', 'Q2', 'Q3' or 'Q4' (case-insensitive).

    Returns:
        datetime.date: the last day covered by the cumulative window.

    Raises:
        ValueError: if `period_id` is not one of Q1..Q4.
    """
    start_year = parse_tax_year(tax_year)
    pid = (period_id or '').upper()

    for qid, month, day, year_offset in _QUARTER_ENDS:
        if qid == pid:
            return date(start_year + year_offset, month, day)

    raise ValueError(f'Unknown period_id: {period_id!r}')


def _income_between(start_date, end_date):
    """Sum payslip income between two ISO dates (inclusive).

    Payslips store ``period_end`` as DD/MM/YYYY text, so the query has
    to reconstruct an ISO date for the comparison.
    """
    query = """
        SELECT COALESCE(SUM(gross_subcontractor_payment), 0) AS total
        FROM payslips
        WHERE date(substr(period_end, 7, 4) || '-' ||
                   substr(period_end, 4, 2) || '-' ||
                   substr(period_end, 1, 2))
              BETWEEN ? AND ?
    """
    row = execute_query(query, (start_date, end_date), fetch_one=True)
    if not row:
        return 0.0
    total = row['total'] if 'total' in row.keys() else row[0]
    return round(float(total or 0), 2)


def _expenses_between(start_date, end_date):
    """Return the list of expense rows between two ISO dates (inclusive).

    `ExpenseModel.get_expenses` already does a direct string comparison
    on the YYYY-MM-DD `expenses.date` column, so we feed it the ISO
    dates straight through.
    """
    return ExpenseModel.get_expenses(start_date=start_date, end_date=end_date)


def calculate_cumulative_totals(tax_year, period_end_date=None, period_id=None):
    """Build the cumulative period summary payload for a tax year.

    The returned dict is in the exact shape HMRC's
    `POST /individuals/business/self-employment/{nino}/{businessId}/period/cumulative/{taxYear}`
    endpoint expects (Self-Employment Business v5.0).

    Args:
        tax_year: 'YYYY-YY' or 'YYYY/YYYY'.
        period_end_date: Inclusive cumulative window end (str
            'YYYY-MM-DD' or datetime.date). Mutually exclusive with
            ``period_id``.
        period_id: Convenience shortcut - 'Q1'..'Q4'. Resolved via
            :func:`quarter_end_date`.

    Returns:
        dict with keys:
            ``periodDates`` -> {periodStartDate, periodEndDate}
            ``periodIncome`` -> {turnover, other}
            ``periodExpenses`` -> {only non-zero HMRC expense fields}
            ``meta`` -> calculator metadata not sent to HMRC
                (``tax_year``, ``period_id``, ``breakdown_by_quarter``).

    Raises:
        ValueError: if neither, or both, of period_end_date /
            period_id are given, or if the resulting window is empty.
    """
    if (period_end_date is None) == (period_id is None):
        raise ValueError(
            'Provide exactly one of period_end_date or period_id'
        )

    if period_id is not None:
        end_date = quarter_end_date(tax_year, period_id)
    elif isinstance(period_end_date, date):
        end_date = period_end_date
    else:
        end_date = datetime.strptime(period_end_date, '%Y-%m-%d').date()

    start_date = tax_year_start(tax_year)
    if end_date < start_date:
        raise ValueError(
            f'period_end_date {end_date.isoformat()} is before tax year start '
            f'{start_date.isoformat()}'
        )

    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    turnover = _income_between(start_iso, end_iso)
    expenses = _expenses_between(start_iso, end_iso)
    expense_data = HMRCMapper.map_expenses_to_hmrc_format(expenses)

    breakdown = _per_quarter_breakdown(tax_year, end_date)

    submission = {
        'periodDates': {
            'periodStartDate': start_iso,
            'periodEndDate': end_iso,
        },
        'periodIncome': {
            'turnover': turnover,
            'other': 0,
        },
        'periodExpenses': expense_data,
        'meta': {
            'tax_year': tax_year,
            'period_id': (period_id or '').upper() or None,
            'tax_year_start': start_iso,
            'breakdown_by_quarter': breakdown,
        },
    }

    logger.info(
        'Cumulative payload built: tax_year=%s window=%s..%s turnover=%.2f',
        tax_year, start_iso, end_iso, turnover,
    )
    return submission


def strip_meta(payload):
    """Return a shallow copy of ``payload`` without the ``meta`` key.

    The API client must never POST our internal ``meta`` block to HMRC.
    """
    return {k: v for k, v in payload.items() if k != 'meta'}


def _per_quarter_breakdown(tax_year, end_date):
    """Compute the per-quarter contribution up to ``end_date``.

    Used by the UI to show "previous quarters' contributions vs this
    quarter" without re-running the cumulative aggregation client-side.
    Quarters whose end falls after ``end_date`` are clipped to
    ``end_date`` and only included if they contain at least one day.
    """
    start_year = parse_tax_year(tax_year)
    breakdown = []
    prev_end = date(start_year, 4, 5)  # day before tax year start

    for qid, month, day, year_offset in _QUARTER_ENDS:
        q_end = date(start_year + year_offset, month, day)
        window_start = prev_end + timedelta(days=1)
        window_end = min(q_end, end_date)

        if window_end < window_start:
            break

        start_iso = window_start.isoformat()
        end_iso = window_end.isoformat()
        income = _income_between(start_iso, end_iso)
        expenses = _expenses_between(start_iso, end_iso)
        expense_total = round(sum(float(e['amount']) for e in expenses), 2)

        breakdown.append({
            'period_id': qid,
            'start_date': start_iso,
            'end_date': end_iso,
            'is_partial': window_end < q_end,
            'turnover': income,
            'expenses_total': expense_total,
        })
        prev_end = q_end

        if window_end >= end_date:
            break

    return breakdown
