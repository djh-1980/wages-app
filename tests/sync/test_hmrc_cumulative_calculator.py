"""Unit tests for app.services.hmrc_cumulative_calculator.

These tests do not call the HMRC sandbox - they only exercise the
local cumulative aggregation against a seeded test database.
"""

import pytest

from app.database import execute_query, get_db_connection


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _category_id(name):
    """Resolve a seeded HMRC expense category id by name."""
    row = execute_query(
        'SELECT id FROM expense_categories WHERE name = ?',
        (name,),
        fetch_one=True,
    )
    assert row is not None, f'Category {name} missing from seed data'
    return row['id']


def _add_expense(iso_date, category_name, amount):
    """Insert one expense row at ``iso_date`` (YYYY-MM-DD)."""
    cat_id = _category_id(category_name)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO expenses (date, category_id, description, amount)
            VALUES (?, ?, ?, ?)
            """,
            (iso_date, cat_id, f'Test {category_name}', amount),
        )
        conn.commit()


def _add_payslip(period_end_ddmmyyyy, gross):
    """Insert a payslip whose period_end falls on the given DD/MM/YYYY."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO payslips (period_end, gross_subcontractor_payment)
            VALUES (?, ?)
            """,
            (period_end_ddmmyyyy, gross),
        )
        conn.commit()


def _seed_full_year(app, tax_year_start_year):
    """Seed one payslip + one vehicle/admin expense per quarter.

    Q1 (May): £1000 income, £50 Vehicle Costs (-> travelCosts).
    Q2 (Aug): £2000 income, £75 Admin Costs    (-> adminCosts).
    Q3 (Nov): £3000 income, £100 Admin Costs   (-> adminCosts).
    Q4 (Feb of next year): £4000 income, £125 Admin Costs.
    """
    sy = tax_year_start_year
    ny = sy + 1
    with app.app_context():
        # Q1 - May
        _add_expense(f'{sy}-05-15', 'Vehicle Costs', 50.00)
        _add_payslip(f'15/05/{sy}', 1000.00)
        # Q2 - August
        _add_expense(f'{sy}-08-15', 'Admin Costs', 75.00)
        _add_payslip(f'15/08/{sy}', 2000.00)
        # Q3 - November
        _add_expense(f'{sy}-11-15', 'Admin Costs', 100.00)
        _add_payslip(f'15/11/{sy}', 3000.00)
        # Q4 - February of the next calendar year
        _add_expense(f'{ny}-02-15', 'Admin Costs', 125.00)
        _add_payslip(f'15/02/{ny}', 4000.00)


# ---------------------------------------------------------------------------
# tax-year helpers
# ---------------------------------------------------------------------------

def test_parse_tax_year_accepts_both_formats():
    from app.services.hmrc_cumulative_calculator import parse_tax_year

    assert parse_tax_year('2025-26') == 2025
    assert parse_tax_year('2025/2026') == 2025


@pytest.mark.parametrize('bad', ['', None, 'twenty-twenty', '2025'])
def test_parse_tax_year_rejects_garbage(bad):
    from app.services.hmrc_cumulative_calculator import parse_tax_year

    with pytest.raises(ValueError):
        parse_tax_year(bad)


def test_quarter_end_dates_are_correct():
    from app.services.hmrc_cumulative_calculator import quarter_end_date

    assert quarter_end_date('2025-26', 'Q1').isoformat() == '2025-07-05'
    assert quarter_end_date('2025-26', 'Q2').isoformat() == '2025-10-05'
    assert quarter_end_date('2025-26', 'Q3').isoformat() == '2026-01-05'
    assert quarter_end_date('2025-26', 'Q4').isoformat() == '2026-04-05'


def test_tax_year_start_is_six_april():
    from app.services.hmrc_cumulative_calculator import tax_year_start

    assert tax_year_start('2025-26').isoformat() == '2025-04-06'


# ---------------------------------------------------------------------------
# Q1..Q4 cumulative arithmetic
# ---------------------------------------------------------------------------

def test_calculate_cumulative_totals_q1(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    _seed_full_year(app, 2025)

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q1')

    assert payload['periodDates'] == {
        'periodStartDate': '2025-04-06',
        'periodEndDate': '2025-07-05',
    }
    assert payload['periodIncome']['turnover'] == 1000.00
    # Vehicle Costs maps to travelCosts in the HMRC mapper.
    assert payload['periodExpenses'] == {'travelCosts': 50.00}


def test_calculate_cumulative_totals_q2_includes_q1(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    _seed_full_year(app, 2025)

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q2')

    assert payload['periodDates']['periodStartDate'] == '2025-04-06'
    assert payload['periodDates']['periodEndDate'] == '2025-10-05'
    assert payload['periodIncome']['turnover'] == 3000.00  # Q1 + Q2
    assert payload['periodExpenses'] == {
        'travelCosts': 50.00,   # Q1
        'adminCosts': 75.00,    # Q2
    }


def test_calculate_cumulative_totals_q3_includes_q1_and_q2(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    _seed_full_year(app, 2025)

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q3')

    assert payload['periodDates']['periodEndDate'] == '2026-01-05'
    assert payload['periodIncome']['turnover'] == 6000.00  # Q1 + Q2 + Q3
    assert payload['periodExpenses'] == {
        'travelCosts': 50.00,
        'adminCosts': 175.00,   # 75 + 100
    }


def test_calculate_cumulative_totals_q4_is_full_tax_year(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    _seed_full_year(app, 2025)

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q4')

    assert payload['periodDates']['periodStartDate'] == '2025-04-06'
    assert payload['periodDates']['periodEndDate'] == '2026-04-05'
    assert payload['periodIncome']['turnover'] == 10000.00  # all four quarters
    assert payload['periodExpenses'] == {
        'travelCosts': 50.00,
        'adminCosts': 300.00,   # 75 + 100 + 125
    }


# ---------------------------------------------------------------------------
# tax-year boundary edge case
# ---------------------------------------------------------------------------

def test_tax_year_boundary_excludes_5_april_includes_6_april(app):
    """Records dated 5 April belong to the previous tax year; 6 April
    belongs to the new one."""
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    with app.app_context():
        # Last day of 2024-25 - must NOT appear in 2025-26 totals.
        _add_expense('2025-04-05', 'Vehicle Costs', 999.00)
        _add_payslip('05/04/2025', 999.00)
        # First day of 2025-26 - must appear.
        _add_expense('2025-04-06', 'Vehicle Costs', 11.00)
        _add_payslip('06/04/2025', 22.00)

        payload = calculate_cumulative_totals('2025-26', period_id='Q1')

    assert payload['periodIncome']['turnover'] == 22.00
    assert payload['periodExpenses'] == {'travelCosts': 11.00}


# ---------------------------------------------------------------------------
# leap year edge case
# ---------------------------------------------------------------------------

def test_leap_year_29_feb_included_in_q4(app):
    """29 February 2024 falls in TY 2023-24 Q4 and must be aggregated."""
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    with app.app_context():
        _add_expense('2024-02-29', 'Vehicle Costs', 42.00)
        _add_payslip('29/02/2024', 1234.00)

        payload = calculate_cumulative_totals('2023-24', period_id='Q4')

    assert payload['periodDates']['periodStartDate'] == '2023-04-06'
    assert payload['periodDates']['periodEndDate'] == '2024-04-05'
    assert payload['periodIncome']['turnover'] == 1234.00
    assert payload['periodExpenses'] == {'travelCosts': 42.00}


# ---------------------------------------------------------------------------
# empty tax year edge case
# ---------------------------------------------------------------------------

def test_empty_tax_year_returns_zero_totals(app):
    """A tax year with no income or expenses still produces a valid
    payload - turnover 0 and an empty periodExpenses dict (the mapper
    drops zero-valued fields)."""
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q2')

    assert payload['periodDates'] == {
        'periodStartDate': '2025-04-06',
        'periodEndDate': '2025-10-05',
    }
    assert payload['periodIncome'] == {'turnover': 0.0, 'other': 0}
    assert payload['periodExpenses'] == {}


# ---------------------------------------------------------------------------
# breakdown + meta + strip_meta
# ---------------------------------------------------------------------------

def test_breakdown_shows_per_quarter_contributions(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    _seed_full_year(app, 2025)

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q3')

    breakdown = payload['meta']['breakdown_by_quarter']
    by_id = {entry['period_id']: entry for entry in breakdown}

    assert set(by_id) == {'Q1', 'Q2', 'Q3'}
    assert by_id['Q1']['turnover'] == 1000.00
    assert by_id['Q1']['expenses_total'] == 50.00
    assert by_id['Q2']['turnover'] == 2000.00
    assert by_id['Q2']['expenses_total'] == 75.00
    assert by_id['Q3']['turnover'] == 3000.00
    assert by_id['Q3']['expenses_total'] == 100.00
    # Q3 ends exactly on 5 January - not partial.
    assert by_id['Q3']['is_partial'] is False


def test_breakdown_with_mid_quarter_end_date_is_marked_partial(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    with app.app_context():
        _add_payslip('30/04/2025', 100.00)   # in Q1
        _add_payslip('30/06/2025', 200.00)   # in Q1, but after our cutoff

        payload = calculate_cumulative_totals(
            '2025-26', period_end_date='2025-05-31'
        )

    breakdown = payload['meta']['breakdown_by_quarter']
    assert len(breakdown) == 1
    assert breakdown[0]['period_id'] == 'Q1'
    assert breakdown[0]['end_date'] == '2025-05-31'
    assert breakdown[0]['is_partial'] is True
    assert breakdown[0]['turnover'] == 100.00


def test_strip_meta_removes_internal_block(app):
    from app.services.hmrc_cumulative_calculator import (
        calculate_cumulative_totals,
        strip_meta,
    )

    with app.app_context():
        payload = calculate_cumulative_totals('2025-26', period_id='Q1')

    cleaned = strip_meta(payload)
    assert 'meta' not in cleaned
    assert set(cleaned.keys()) == {'periodDates', 'periodIncome', 'periodExpenses'}


# ---------------------------------------------------------------------------
# argument validation
# ---------------------------------------------------------------------------

def test_calculate_requires_exactly_one_window_argument(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    with app.app_context():
        with pytest.raises(ValueError):
            calculate_cumulative_totals('2025-26')
        with pytest.raises(ValueError):
            calculate_cumulative_totals(
                '2025-26', period_id='Q1', period_end_date='2025-05-01'
            )


def test_calculate_rejects_end_before_tax_year_start(app):
    from app.services.hmrc_cumulative_calculator import calculate_cumulative_totals

    with app.app_context():
        with pytest.raises(ValueError):
            calculate_cumulative_totals(
                '2025-26', period_end_date='2025-04-05'
            )


def test_quarter_end_date_rejects_unknown_period_id():
    from app.services.hmrc_cumulative_calculator import quarter_end_date

    with pytest.raises(ValueError):
        quarter_end_date('2025-26', 'Q5')
