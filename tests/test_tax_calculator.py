"""
Unit tests for app.services.tax_calculator.

These tests exercise the pure calculation primitives in isolation (no DB
access). Full end-to-end tests that hit the database live in a separate
integration-test file.
"""

from datetime import date

import pytest

from app.constants.tax_rates import get_current_tax_year_key, get_rates
from app.services.tax_calculator import (
    _apply_bands,
    calculate_class_4_ni,
    calculate_income_tax,
    expense_tax_year,
    payslip_tax_year,
    tapered_personal_allowance,
    tax_year_bounds,
    tax_year_progress,
)

RATES_2026_27 = get_rates('2026-27')


# ---------------------------------------------------------------------------
# Tax-year key conversions
# ---------------------------------------------------------------------------
class TestTaxYearKey:
    def test_current_tax_year_before_6_april(self):
        assert get_current_tax_year_key(date(2026, 4, 5)) == '2025-26'

    def test_current_tax_year_on_6_april(self):
        assert get_current_tax_year_key(date(2026, 4, 6)) == '2026-27'

    def test_current_tax_year_midyear(self):
        assert get_current_tax_year_key(date(2026, 11, 15)) == '2026-27'

    def test_payslip_tax_year_format(self):
        assert payslip_tax_year('2026-27') == '2026'

    def test_expense_tax_year_format(self):
        assert expense_tax_year('2026-27') == '2026/2027'

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError):
            payslip_tax_year('2026/27')
        with pytest.raises(ValueError):
            payslip_tax_year('not-a-year')

    def test_bounds_cover_full_year(self):
        start, end = tax_year_bounds('2026-27')
        assert start == date(2026, 4, 6)
        assert end == date(2027, 4, 5)


# ---------------------------------------------------------------------------
# Personal allowance taper
# ---------------------------------------------------------------------------
class TestPersonalAllowanceTaper:
    def test_under_threshold_returns_full_allowance(self):
        assert tapered_personal_allowance(50000, RATES_2026_27) == 12570

    def test_at_threshold_returns_full_allowance(self):
        assert tapered_personal_allowance(100000, RATES_2026_27) == 12570

    def test_partial_taper(self):
        # 110k gross: (110000-100000)/2 = 5000 reduction.
        assert tapered_personal_allowance(110000, RATES_2026_27) == 12570 - 5000

    def test_fully_tapered_at_125140(self):
        # PA reaches zero at exactly 125,140.
        assert tapered_personal_allowance(125140, RATES_2026_27) == 0.0

    def test_never_goes_negative(self):
        assert tapered_personal_allowance(500000, RATES_2026_27) == 0.0


# ---------------------------------------------------------------------------
# Income tax
# ---------------------------------------------------------------------------
class TestIncomeTax:
    def test_zero_profit_zero_tax(self):
        tax, bands = calculate_income_tax(0, RATES_2026_27)
        assert tax == 0.0
        assert bands == []

    def test_negative_profit_zero_tax(self):
        tax, _ = calculate_income_tax(-500, RATES_2026_27)
        assert tax == 0.0

    def test_basic_rate_only(self):
        # Taxable profit 10k (already excluding PA).
        # Basic-rate band is 0-37,700 at 20% (after PA shift).
        tax, _ = calculate_income_tax(10000, RATES_2026_27)
        assert tax == pytest.approx(2000.00)

    def test_straddles_basic_and_higher(self):
        # Taxable profit 50k: 37,700 @ 20% + 12,300 @ 40% = 7,540 + 4,920 = 12,460.
        tax, _ = calculate_income_tax(50000, RATES_2026_27)
        assert tax == pytest.approx(7540 + 4920)

    def test_full_spectrum(self):
        # Taxable profit 150k:
        #   37,700 @ 20%  =  7,540
        #   74,870 @ 40%  = 29,948  (112,570 - 37,700)
        #   37,430 @ 45%  = 16,843.50 (150,000 - 112,570)
        tax, bands = calculate_income_tax(150000, RATES_2026_27)
        assert tax == pytest.approx(7540 + 29948 + 16843.50)
        # Three bands expected.
        assert len(bands) == 3


# ---------------------------------------------------------------------------
# Class 4 NI
# ---------------------------------------------------------------------------
class TestClass4NI:
    def test_zero_profit_zero_ni(self):
        ni, _ = calculate_class_4_ni(0, RATES_2026_27)
        assert ni == 0.0

    def test_under_lower_profits_limit_zero_ni(self):
        ni, _ = calculate_class_4_ni(10000, RATES_2026_27)
        assert ni == 0.0

    def test_main_rate_only(self):
        # Profit 20k: (20000 - 12570) @ 6% = 7,430 * 0.06 = 445.80.
        ni, _ = calculate_class_4_ni(20000, RATES_2026_27)
        assert ni == pytest.approx(445.80)

    def test_straddles_main_and_upper(self):
        # Profit 60k: (50270 - 12570) @ 6% + (60000 - 50270) @ 2%
        #   = 37,700 * 0.06 + 9,730 * 0.02
        #   = 2,262 + 194.60 = 2,456.60.
        ni, _ = calculate_class_4_ni(60000, RATES_2026_27)
        assert ni == pytest.approx(2262.00 + 194.60)


# ---------------------------------------------------------------------------
# Band mechanics
# ---------------------------------------------------------------------------
class TestApplyBands:
    def test_amount_entirely_in_first_band(self):
        bands = [(10000, 0.10), (50000, 0.20), (None, 0.30)]
        total, detail = _apply_bands(5000, bands)
        assert total == 500.0
        assert detail[0]['amount_in_band'] == 5000
        assert detail[1]['amount_in_band'] == 0
        assert detail[2]['amount_in_band'] == 0

    def test_amount_in_open_ended_band(self):
        bands = [(10000, 0.10), (None, 0.30)]
        total, detail = _apply_bands(25000, bands)
        # 10,000 * 0.10 + 15,000 * 0.30 = 1,000 + 4,500 = 5,500.
        assert total == pytest.approx(5500)
        assert detail[1]['amount_in_band'] == 15000


# ---------------------------------------------------------------------------
# Tax-year progress
# ---------------------------------------------------------------------------
class TestTaxYearProgress:
    def test_first_day(self):
        p = tax_year_progress('2026-27', today=date(2026, 4, 6))
        assert p['days_elapsed'] == 1
        assert p['percent_complete'] > 0

    def test_last_day(self):
        p = tax_year_progress('2026-27', today=date(2027, 4, 5))
        assert p['days_elapsed'] == p['total_days']
        assert p['percent_complete'] == 100.0

    def test_midyear(self):
        # 21 April 2026 = day 16 of 365.
        p = tax_year_progress('2026-27', today=date(2026, 4, 21))
        assert p['days_elapsed'] == 16

    def test_before_tax_year_starts(self):
        p = tax_year_progress('2026-27', today=date(2026, 4, 1))
        assert p['days_elapsed'] == 0
        assert p['percent_complete'] == 0.0
