"""Wages page analytics API.

Aggregation endpoints powering the KPI cards and Chart.js widgets on the
Analytics tab of ``/wages``. All figures are scoped to a UK tax year using
the ``YYYY-YY`` key format produced by
:func:`app.services.tax_calculator.get_current_tax_year_key`.
"""

import logging
from collections import OrderedDict
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..constants.tax_rates import get_current_tax_year_key
from ..database import get_db_connection
from ..services.tax_calculator import (
    DEPRECIATION_BOX_NUMBER,
    expense_tax_year,
    get_ytd_expenses,
    get_ytd_income,
    payslip_tax_year,
    tax_year_bounds,
)

logger = logging.getLogger(__name__)

wages_analytics_bp = Blueprint('wages_analytics_api', __name__, url_prefix='/api/wages')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_ddmmyyyy(value):
    """Parse a ``DD/MM/YYYY`` string into a :class:`date`, or ``None``."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def _format_tax_year_label(key):
    """``"2026-27"`` -> ``"2026/27"`` for human-friendly UI labels."""
    try:
        start, end = key.split('-')
        return f'{start}/{end}'
    except (ValueError, AttributeError):
        return key


def _available_tax_year_keys():
    """Return all tax year keys in ``YYYY-YY`` form, newest first.

    Combines starting years from ``payslips`` and ``expenses`` so the
    dropdown always covers every year with data.
    """
    starts = set()
    try:
        with get_db_connection() as conn:
            for row in conn.execute('SELECT DISTINCT tax_year FROM payslips'):
                try:
                    starts.add(int(row['tax_year']))
                except (TypeError, ValueError):
                    continue
            for row in conn.execute('SELECT DISTINCT tax_year FROM expenses WHERE tax_year IS NOT NULL'):
                raw = row['tax_year']
                if not raw:
                    continue
                try:
                    # Expenses store as "YYYY/YYYY"; take the first part.
                    starts.add(int(str(raw).split('/')[0]))
                except (TypeError, ValueError):
                    continue
    except Exception as e:
        logger.error(f'Error listing tax years: {e}')

    keys = [f'{s}-{(s + 1) % 100:02d}' for s in sorted(starts, reverse=True)]
    # Always include the current tax year so the UI has something to select
    # even on a brand-new install with no data yet.
    current = get_current_tax_year_key()
    if current not in keys:
        keys.insert(0, current)
    return keys


# ---------------------------------------------------------------------------
# Aggregation queries
# ---------------------------------------------------------------------------
def _weekly_earnings(tax_year_key, limit=12):
    """Return the last ``limit`` weeks of gross earnings for this tax year."""
    pay_year = payslip_tax_year(tax_year_key)
    with get_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT week_number,
                   COALESCE(gross_subcontractor_payment, 0.0) AS gross,
                   pay_date
            FROM payslips
            WHERE tax_year = ?
            ORDER BY week_number DESC
            LIMIT ?
            ''',
            (pay_year, limit),
        ).fetchall()
    # Reverse so the chart reads oldest -> newest left to right.
    return [
        {
            'week_number': int(r['week_number']),
            'gross': float(r['gross'] or 0.0),
            'pay_date': r['pay_date'],
        }
        for r in reversed(rows)
    ]


def _year_comparison(current_key, num_years=3):
    """Return cumulative weekly gross for the current + previous ``n-1`` years.

    Shape: ``{'2024-25': [{'week': 1, 'cumulative': 1234.56}, ...], ...}``
    """
    try:
        start_year = int(payslip_tax_year(current_key))
    except ValueError:
        return {}
    years = [start_year - i for i in range(num_years)]

    result = OrderedDict()
    with get_db_connection() as conn:
        for y in years:
            rows = conn.execute(
                '''
                SELECT week_number,
                       COALESCE(gross_subcontractor_payment, 0.0) AS gross
                FROM payslips
                WHERE tax_year = ?
                ORDER BY week_number ASC
                ''',
                (str(y),),
            ).fetchall()
            cumulative = 0.0
            series = []
            for r in rows:
                cumulative += float(r['gross'] or 0.0)
                series.append({
                    'week': int(r['week_number']),
                    'cumulative': round(cumulative, 2),
                })
            key = f'{y}-{(y + 1) % 100:02d}'
            result[key] = series
    return result


def _monthly_income_expenses(tax_year_key):
    """Return 12 months of gross income and allowable expenses for this year.

    Months run April (month 1) -> March (month 12) so the x-axis matches the
    UK tax year and not the calendar year.
    """
    start_date, end_date = tax_year_bounds(tax_year_key)
    pay_year = payslip_tax_year(tax_year_key)
    exp_year = expense_tax_year(tax_year_key)

    # Build ordered list of (year, month) tuples from April -> March.
    months = []
    y, m = start_date.year, start_date.month
    for _ in range(12):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    income_by_month = {ym: 0.0 for ym in months}
    expenses_by_month = {ym: 0.0 for ym in months}

    with get_db_connection() as conn:
        # Payslip pay_date is DD/MM/YYYY text - parse in Python for reliability.
        pay_rows = conn.execute(
            '''
            SELECT pay_date, COALESCE(gross_subcontractor_payment, 0.0) AS gross
            FROM payslips
            WHERE tax_year = ?
            ''',
            (pay_year,),
        ).fetchall()
        for r in pay_rows:
            d = _parse_ddmmyyyy(r['pay_date'])
            if not d:
                continue
            ym = (d.year, d.month)
            if ym in income_by_month:
                income_by_month[ym] += float(r['gross'] or 0.0)

        exp_rows = conn.execute(
            '''
            SELECT e.date, COALESCE(e.amount, 0.0) AS amount,
                   ec.hmrc_box_number AS hmrc_box_number
            FROM expenses e
            LEFT JOIN expense_categories ec ON ec.id = e.category_id
            WHERE e.tax_year = ?
            ''',
            (exp_year,),
        ).fetchall()
        for r in exp_rows:
            # Exclude depreciation to match tax-calculator "allowable" logic.
            if r['hmrc_box_number'] == DEPRECIATION_BOX_NUMBER:
                continue
            d = _parse_ddmmyyyy(r['date'])
            if not d:
                continue
            ym = (d.year, d.month)
            if ym in expenses_by_month:
                expenses_by_month[ym] += float(r['amount'] or 0.0)

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return [
        {
            'label': f'{month_names[m - 1]} {str(y)[2:]}',
            'year': y,
            'month': m,
            'income': round(income_by_month[(y, m)], 2),
            'expenses': round(expenses_by_month[(y, m)], 2),
        }
        for (y, m) in months
    ]


def _top_expense_categories(tax_year_key, limit=5):
    """Top ``limit`` allowable expense categories by spend this year."""
    data = get_ytd_expenses(tax_year_key)
    allowable = [c for c in data.get('by_category', []) if c.get('allowable')]
    allowable.sort(key=lambda c: c.get('total', 0.0), reverse=True)
    return [
        {
            'category_name': c['category_name'],
            'total': round(float(c['total'] or 0.0), 2),
            'count': int(c['count'] or 0),
        }
        for c in allowable[:limit]
    ]


def _jobs_per_day_of_week(tax_year_key):
    """Average number of run_sheet_jobs per weekday within this tax year.

    Returns one entry per weekday (Mon -> Sun). The average is
    ``total_jobs / distinct_dates_worked_for_that_weekday`` so busy days
    aren't penalised by weeks where you didn't work at all.
    """
    start_date, end_date = tax_year_bounds(tax_year_key)
    weekday_jobs = [0] * 7           # Mon=0 .. Sun=6
    weekday_dates = [set() for _ in range(7)]

    with get_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT date, COUNT(*) AS job_count
            FROM run_sheet_jobs
            WHERE date IS NOT NULL AND date != ''
            GROUP BY date
            '''
        ).fetchall()

    for r in rows:
        d = _parse_ddmmyyyy(r['date'])
        if not d or d < start_date or d > end_date:
            continue
        wd = d.weekday()
        weekday_jobs[wd] += int(r['job_count'] or 0)
        weekday_dates[wd].add(d)

    labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    return [
        {
            'day': labels[i],
            'weekday_index': i,
            'total_jobs': weekday_jobs[i],
            'days_worked': len(weekday_dates[i]),
            'avg_jobs': round(weekday_jobs[i] / len(weekday_dates[i]), 2)
            if weekday_dates[i] else 0.0,
        }
        for i in range(7)
    ]


def _kpis(tax_year_key):
    """Headline KPI numbers for the four summary cards."""
    income = get_ytd_income(tax_year_key)
    expenses = get_ytd_expenses(tax_year_key)

    gross = float(income.get('total') or 0.0)
    allowable = float(expenses.get('allowable_total') or 0.0)
    net_profit = gross - allowable
    weeks = int(income.get('payslip_count') or 0)
    avg_weekly = (gross / weeks) if weeks else 0.0

    return {
        'gross_income_ytd': round(gross, 2),
        'allowable_expenses_ytd': round(allowable, 2),
        'net_profit_ytd': round(net_profit, 2),
        'avg_weekly_earnings': round(avg_weekly, 2),
        'weeks_completed': weeks,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@wages_analytics_bp.route('/analytics')
def api_wages_analytics():
    """Return all analytics data for the Wages -> Analytics tab.

    Query params:
        tax_year: ``YYYY-YY`` key (e.g. ``2026-27``). Defaults to the
            current UK tax year.
    """
    try:
        tax_year_key = request.args.get('tax_year') or get_current_tax_year_key()
        # Validate early so a bad client input gives a clean 400.
        try:
            tax_year_bounds(tax_year_key)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        available = _available_tax_year_keys()

        return jsonify({
            'success': True,
            'data': {
                'tax_year': {
                    'key': tax_year_key,
                    'label': _format_tax_year_label(tax_year_key),
                    'current': get_current_tax_year_key(),
                },
                'available_tax_years': [
                    {'key': k, 'label': _format_tax_year_label(k)}
                    for k in available
                ],
                'kpis': _kpis(tax_year_key),
                'weekly_earnings': _weekly_earnings(tax_year_key, limit=12),
                'year_comparison': _year_comparison(tax_year_key, num_years=3),
                'monthly_income_expenses': _monthly_income_expenses(tax_year_key),
                'top_expense_categories': _top_expense_categories(tax_year_key, limit=5),
                'jobs_per_dow': _jobs_per_day_of_week(tax_year_key),
            },
        })
    except Exception as e:
        logger.error(f'Error building wages analytics: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@wages_analytics_bp.route('/tax-years')
def api_wages_tax_years():
    """List available tax years (YYYY-YY) plus the current one.

    Separate from the legacy ``/api/tax_years`` endpoint (which returns raw
    payslip keys) so the wages page can show human-friendly labels without
    breaking other callers.
    """
    try:
        available = _available_tax_year_keys()
        return jsonify({
            'success': True,
            'data': {
                'current': get_current_tax_year_key(),
                'years': [
                    {'key': k, 'label': _format_tax_year_label(k)}
                    for k in available
                ],
            },
        })
    except Exception as e:
        logger.error(f'Error listing wages tax years: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
