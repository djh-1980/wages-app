"""
Self-employed UK tax estimator.

Given a tax-year key (e.g. ``"2026-27"``) this service sums year-to-date
income from ``payslips`` and allowable expenses from ``expenses``, applies
income tax bands (with personal-allowance taper) and Class 4 NI, and
returns a structured breakdown suitable for rendering on a dashboard.

Everything is a best-effort estimate - see the disclaimer text returned
by :func:`calculate_tax_estimate`. It does not replace a Self Assessment
return.

The calculation is deliberately pure over the rates config in
:mod:`app.constants.tax_rates` so new tax years can be added without
touching this file.
"""

import logging
import sqlite3
from datetime import date, datetime

from ..constants.tax_rates import get_current_tax_year_key, get_rates
from ..database import get_db_connection

logger = logging.getLogger(__name__)


# HMRC box 28 = Depreciation. For sole-trader income tax, depreciation is
# *not* an allowable expense: capital allowances are used instead. Exclude
# this category from allowable-expense totals but still report it so the
# user sees where it's gone.
DEPRECIATION_BOX_NUMBER = 28


# ---------------------------------------------------------------------------
# Tax-year key conversions
# ---------------------------------------------------------------------------
def _parse_key(tax_year_key):
    """Parse a ``YYYY-YY`` key into its integer start year.

    Raises :class:`ValueError` on anything that doesn't look right - callers
    should treat this as a 400 Bad Request.
    """
    try:
        start_str, _end_str = tax_year_key.split('-')
        start = int(start_str)
        if start < 2000 or start > 2100:
            raise ValueError
        return start
    except (ValueError, AttributeError):
        raise ValueError(
            f'Invalid tax_year {tax_year_key!r}; expected format "YYYY-YY" '
            f'(e.g. "2026-27")'
        )


def payslip_tax_year(tax_year_key):
    """Convert ``"2026-27"`` -> ``"2026"`` (the payslips table format)."""
    return str(_parse_key(tax_year_key))


def expense_tax_year(tax_year_key):
    """Convert ``"2026-27"`` -> ``"2026/2027"`` (the expenses table format)."""
    start = _parse_key(tax_year_key)
    return f'{start}/{start + 1}'


def tax_year_bounds(tax_year_key):
    """Return ``(start_date, end_date)`` for the given tax-year key.

    Start is 6 April of the start year; end is 5 April of the following year.
    """
    start = _parse_key(tax_year_key)
    return date(start, 4, 6), date(start + 1, 4, 5)


# ---------------------------------------------------------------------------
# Data-fetching primitives
# ---------------------------------------------------------------------------
def get_ytd_income(tax_year_key):
    """Sum ``gross_subcontractor_payment`` for the given tax year.

    Returns a dict with the total and the number of payslips contributing
    to it so the caller can display both.
    """
    key = payslip_tax_year(tax_year_key)
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                '''
                SELECT
                    COALESCE(SUM(gross_subcontractor_payment), 0.0) AS total,
                    COUNT(*) AS payslip_count,
                    MIN(pay_date) AS first_pay_date,
                    MAX(pay_date) AS last_pay_date
                FROM payslips
                WHERE tax_year = ?
                ''',
                (key,),
            ).fetchone()
            return {
                'total': float(row['total'] or 0.0),
                'payslip_count': int(row['payslip_count'] or 0),
                'first_pay_date': row['first_pay_date'],
                'last_pay_date': row['last_pay_date'],
            }
    except sqlite3.Error as e:
        logger.error(f'Error summing YTD income for {tax_year_key}: {e}')
        return {'total': 0.0, 'payslip_count': 0,
                'first_pay_date': None, 'last_pay_date': None}


def get_ytd_expenses(tax_year_key):
    """Return expense totals grouped by category for the given tax year.

    The result includes ``allowable_total`` (what actually reduces taxable
    profit) and ``excluded_total`` (e.g. Depreciation) so the dashboard can
    show both. The per-category breakdown is ordered by total descending.
    """
    key = expense_tax_year(tax_year_key)
    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                '''
                SELECT
                    ec.id              AS category_id,
                    ec.name            AS category_name,
                    ec.hmrc_box        AS hmrc_box,
                    ec.hmrc_box_number AS hmrc_box_number,
                    COUNT(e.id)        AS count,
                    COALESCE(SUM(e.amount), 0.0) AS total
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                WHERE e.tax_year = ?
                GROUP BY ec.id, ec.name, ec.hmrc_box, ec.hmrc_box_number
                ORDER BY total DESC
                ''',
                (key,),
            ).fetchall()
    except sqlite3.Error as e:
        logger.error(f'Error summing YTD expenses for {tax_year_key}: {e}')
        return {'allowable_total': 0.0, 'excluded_total': 0.0,
                'by_category': [], 'expense_count': 0}

    by_category = []
    allowable_total = 0.0
    excluded_total = 0.0
    expense_count = 0
    for r in rows:
        cat_total = float(r['total'] or 0.0)
        is_allowable = r['hmrc_box_number'] != DEPRECIATION_BOX_NUMBER
        by_category.append({
            'category_id': r['category_id'],
            'category_name': r['category_name'],
            'hmrc_box': r['hmrc_box'],
            'hmrc_box_number': r['hmrc_box_number'],
            'count': int(r['count'] or 0),
            'total': cat_total,
            'allowable': is_allowable,
        })
        expense_count += int(r['count'] or 0)
        if is_allowable:
            allowable_total += cat_total
        else:
            excluded_total += cat_total

    return {
        'allowable_total': allowable_total,
        'excluded_total': excluded_total,
        'by_category': by_category,
        'expense_count': expense_count,
    }


# ---------------------------------------------------------------------------
# Pure calculators (no DB access - trivially unit-testable)
# ---------------------------------------------------------------------------
def tapered_personal_allowance(gross_income, rates):
    """Apply the over-100k taper to the personal allowance.

    For every 2 of gross income over ``pa_taper_threshold`` (currently
    100,000) the personal allowance is reduced by 1, down to a minimum of
    zero. This is applied to *gross* income, not taxable profit - so callers
    must pass the pre-tax income figure.
    """
    base_pa = rates['personal_allowance']
    threshold = rates['pa_taper_threshold']
    if gross_income <= threshold:
        return base_pa
    reduction = (gross_income - threshold) / 2.0
    return max(0.0, base_pa - reduction)


def _apply_bands(amount, bands):
    """Apply progressive bands to ``amount`` and return total + per-band detail.

    ``bands`` is a list of ``(upper_limit, rate)`` tuples. The final entry's
    upper limit may be ``None`` to mean "no ceiling". Amount is the figure
    to be taxed *before* any allowance has been subtracted - the first band
    typically has rate 0 to model the allowance itself.
    """
    detail = []
    total = 0.0
    lower = 0.0
    for upper, rate in bands:
        if upper is None:
            band_amount = max(0.0, amount - lower)
        else:
            band_amount = max(0.0, min(amount, upper) - lower)
        tax = band_amount * rate
        detail.append({
            'lower': lower,
            'upper': upper,
            'rate': rate,
            'amount_in_band': band_amount,
            'tax': tax,
        })
        total += tax
        if upper is None or amount <= upper:
            # Remaining bands contribute nothing - still include them in
            # the detail with zero so the UI can show them.
            lower = upper if upper is not None else lower
            continue
        lower = upper

    return total, detail


def calculate_income_tax(taxable_profit, rates):
    """Apply income-tax bands to ``taxable_profit``.

    ``taxable_profit`` is expected to already have the personal allowance
    subtracted (i.e. it's the amount in the basic/higher/additional bands).
    The zero-rate first band is still included for presentational symmetry.

    Returns ``(total_tax, band_detail_list)``.
    """
    if taxable_profit <= 0:
        return 0.0, []
    # The income-tax bands in TAX_RATES include the personal allowance as
    # the first (0%) band. For tax purposes on *already-allowance-adjusted*
    # profit we skip that band and shift the remaining thresholds down by
    # the PA amount.
    pa = rates['personal_allowance']
    shifted = []
    for upper, rate in rates['income_tax_bands'][1:]:
        shifted.append(
            ((upper - pa) if upper is not None else None, rate)
        )
    return _apply_bands(taxable_profit, shifted)


def calculate_class_4_ni(profit, rates):
    """Apply Class 4 NI bands to pre-allowance profit.

    Class 4 NI uses the same lower profits limit as the income-tax personal
    allowance (12,570 for 2026/27) so we pass the raw profit and let the
    bands take care of it.
    """
    if profit <= 0:
        return 0.0, []
    return _apply_bands(profit, rates['class_4_ni_bands'])


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------
def tax_year_progress(tax_year_key, today=None):
    """Return how far through the tax year we currently are.

    Useful for a "X days of 365 - Y% complete" progress bar.
    """
    today = today or date.today()
    start, end = tax_year_bounds(tax_year_key)
    total_days = (end - start).days + 1
    if today < start:
        days_elapsed = 0
    elif today > end:
        days_elapsed = total_days
    else:
        days_elapsed = (today - start).days + 1
    return {
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'total_days': total_days,
        'days_elapsed': days_elapsed,
        'percent_complete': round((days_elapsed / total_days) * 100, 1),
    }


def calculate_tax_estimate(tax_year_key=None, today=None):
    """Produce a full tax-estimate breakdown for a given tax year.

    If ``tax_year_key`` is not supplied, the current UK tax year is used
    (based on ``today`` or the real system date).

    Returns a JSON-serialisable dict ready to be returned by the API route.
    """
    tax_year_key = tax_year_key or get_current_tax_year_key(today)
    # Raises KeyError with a helpful message if the year isn't configured.
    rates = get_rates(tax_year_key)

    income = get_ytd_income(tax_year_key)
    expenses = get_ytd_expenses(tax_year_key)

    gross_income = income['total']
    allowable_expenses = expenses['allowable_total']

    # Profit before allowance - can be negative if expenses exceed income.
    profit = gross_income - allowable_expenses

    # Personal allowance (with over-100k taper based on gross income).
    pa = tapered_personal_allowance(gross_income, rates)

    # Taxable profit is profit minus personal allowance, but never below zero
    # for the purposes of income tax / NI. A loss is reported separately.
    taxable_profit = max(0.0, profit - pa)
    loss = max(0.0, -profit)

    income_tax_total, income_tax_bands = calculate_income_tax(taxable_profit, rates)
    class_4_ni_total, class_4_ni_bands = calculate_class_4_ni(
        # Class 4 NI ignores the personal-allowance taper - it uses its own
        # lower profits limit (baked into the band structure). Pass raw
        # profit, not taxable profit.
        max(0.0, profit),
        rates,
    )

    total_tax_owed = income_tax_total + class_4_ni_total

    warnings = []
    if profit < 0:
        warnings.append(
            f'Expenses exceed income by \u00a3{loss:,.2f}. A trading loss may '
            f'be offset against other income or carried forward - speak to '
            f'an accountant.'
        )
    if income['payslip_count'] == 0:
        warnings.append('No payslips recorded for this tax year yet.')
    if expenses['excluded_total'] > 0:
        warnings.append(
            f'Depreciation of \u00a3{expenses["excluded_total"]:,.2f} excluded '
            f'from allowable expenses (HMRC uses capital allowances instead).'
        )

    return {
        'tax_year': tax_year_key,
        'generated_at': (today or datetime.now()).isoformat(),
        'progress': tax_year_progress(tax_year_key, today=today),
        'income': {
            'gross': round(gross_income, 2),
            'payslip_count': income['payslip_count'],
            'first_pay_date': income['first_pay_date'],
            'last_pay_date': income['last_pay_date'],
        },
        'expenses': {
            'allowable_total': round(allowable_expenses, 2),
            'excluded_total': round(expenses['excluded_total'], 2),
            'by_category': [
                {**c, 'total': round(c['total'], 2)} for c in expenses['by_category']
            ],
            'expense_count': expenses['expense_count'],
        },
        'profit': {
            'gross_profit': round(profit, 2),
            'personal_allowance': round(pa, 2),
            'taxable_profit': round(taxable_profit, 2),
            'loss': round(loss, 2),
        },
        'income_tax': {
            'total': round(income_tax_total, 2),
            'bands': [
                {**b,
                 'lower': round(b['lower'], 2),
                 'upper': b['upper'],
                 'amount_in_band': round(b['amount_in_band'], 2),
                 'tax': round(b['tax'], 2)}
                for b in income_tax_bands
            ],
        },
        'class_4_ni': {
            'total': round(class_4_ni_total, 2),
            'bands': [
                {**b,
                 'lower': round(b['lower'], 2),
                 'upper': b['upper'],
                 'amount_in_band': round(b['amount_in_band'], 2),
                 'tax': round(b['tax'], 2)}
                for b in class_4_ni_bands
            ],
        },
        'total_tax_owed': round(total_tax_owed, 2),
        'warnings': warnings,
        'disclaimer': (
            'Estimate only. Actual tax owed is calculated by HMRC based on '
            'your Self Assessment return. Figures assume all recorded '
            'expenses are allowable (except Depreciation, which uses '
            'capital allowances), and no other income sources (PAYE, '
            'savings, dividends, etc.).'
        ),
    }
