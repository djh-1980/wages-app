"""
UK self-employed tax rates and thresholds, keyed by tax year.

A UK tax year runs from 6 April of the starting year to 5 April of the
following year. The key format used throughout this app is ``YYYY-YY``
(e.g. ``2026-27``) which is the canonical HMRC-style representation.

Internally we sometimes have to deal with two other formats because of
legacy data:

* ``payslips.tax_year`` stores a single starting year, e.g. ``"2026"``.
* ``expenses.tax_year`` stores a slash-separated string, e.g. ``"2026/2027"``.

Use the helpers in :mod:`app.services.tax_calculator` to convert between
these on the fly - do not hard-code any conversion logic in routes or
templates.

When a new tax year begins (6 April), add a new entry to ``TAX_RATES``
below with the current year's figures. Nothing else needs to change.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Rates
# ---------------------------------------------------------------------------
# Sources (verified April 2026):
#   * Income tax thresholds - frozen until April 2028 (Autumn 2024 Budget).
#   * Personal allowance taper above 100k - unchanged since 2010/11.
#   * Class 2 NI abolished from April 2024 (Spring 2024 Budget) - omitted.
#   * Class 4 NI main rate cut 9% -> 8% (Autumn 2023) then 8% -> 6%
#     (Spring 2024 Budget). Upper rate 2% unchanged.

TAX_RATES = {
    '2026-27': {
        'personal_allowance': 12570,
        # PA reduces by 1 for every 2 over this threshold.
        'pa_taper_threshold': 100000,
        # Income-tax bands. Each entry is (upper_limit, rate). The final
        # entry uses ``None`` as the upper limit to mean "no ceiling".
        # Bands are expressed as cumulative income limits, not band widths,
        # so they're easy to compare against taxable profit directly.
        'income_tax_bands': [
            (12570, 0.00),     # Personal allowance (0%)
            (50270, 0.20),     # Basic rate
            (125140, 0.40),    # Higher rate
            (None, 0.45),      # Additional rate
        ],
        # Class 4 National Insurance bands - same structure as income tax.
        'class_4_ni_bands': [
            (12570, 0.00),     # Lower profits limit
            (50270, 0.06),     # Main rate (was 9% before April 2024)
            (None, 0.02),      # Upper rate
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_current_tax_year_key(today=None):
    """Return the canonical ``YYYY-YY`` key for the tax year covering ``today``.

    A UK tax year starts on 6 April. Anything on or after 6 April belongs to
    the tax year whose starting year is that calendar year; anything before
    belongs to the previous starting year.
    """
    today = today or date.today()
    start_year = today.year if (today.month, today.day) >= (4, 6) else today.year - 1
    end_year_short = (start_year + 1) % 100
    return f'{start_year}-{end_year_short:02d}'


def get_rates(tax_year_key):
    """Return the rates dict for ``tax_year_key`` (e.g. ``"2026-27"``).

    Raises ``KeyError`` with a helpful message if the year hasn't been
    configured yet - a clear signal to add it to ``TAX_RATES``.
    """
    try:
        return TAX_RATES[tax_year_key]
    except KeyError:
        available = ', '.join(sorted(TAX_RATES.keys())) or '(none)'
        raise KeyError(
            f'Tax rates not configured for {tax_year_key!r}. '
            f'Available years: {available}. '
            f'Add an entry to app/constants/tax_rates.py when a new year begins.'
        )
