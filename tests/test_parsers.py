"""Unit tests for the PDF text parsers.

These tests exercise the pure parsing primitives on `RunSheetImporter` and
`PayslipExtractor` against synthetic line-lists that mimic pdfplumber's
output. No real PDFs, no database, no network - everything runs under 1s.

The importers' ``__init__`` methods connect to SQLite, so we use
``object.__new__`` + manual attribute setup to construct isolated
instances for testing.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

# scripts/production/ is not a Python package, so load the two importer
# modules directly by path.
_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / 'scripts' / 'production'
# `import_run_sheets` transitively imports `camelot_runsheet_parser`
# from the same directory; make that resolvable.
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _load_module(name, relative_path):
    """Load a standalone script as an importable module."""
    spec = importlib.util.spec_from_file_location(name, _ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_runsheet_mod = _load_module(
    'runsheet_importer',
    'scripts/production/import_run_sheets.py',
)
_payslip_mod = _load_module(
    'payslip_extractor',
    'scripts/production/extract_payslips.py',
)

RunSheetImporter = _runsheet_mod.RunSheetImporter
PayslipExtractor = _payslip_mod.PayslipExtractor


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture
def importer():
    """Build a RunSheetImporter without hitting the DB or filesystem."""
    inst = object.__new__(RunSheetImporter)
    inst.overwritten_dates = set()
    inst.activity_patterns = [
        'TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS',
        'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION',
        'DELIVERY', 'INSTALL', 'MAINTENANCE', 'SURVEY', 'INSPECTION',
        'UPGRADE', 'CONFIGURATION', 'TRAINING', 'CONSULTATION',
    ]
    inst.postcode_pattern = re.compile(
        r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b'
    )
    inst.customer_cleanup_patterns = [
        (r'^Customer Signature\s*', ''),
        (r'^Customer Print\s*', ''),
        (r'\*\*\*[^*]*\*\*\*', ''),
        (r'\s+', ' '),
        (r'^\s+|\s+$', ''),
    ]
    return inst


@pytest.fixture
def extractor():
    """Build a PayslipExtractor without hitting the DB."""
    return object.__new__(PayslipExtractor)


# -- Postcode extraction ----------------------------------------------------

class TestExtractPostcode:
    def test_full_postcode_with_space(self, importer):
        assert importer.extract_postcode('51 CHAPEL STREET PR7 5AS') == 'PR7 5AS'

    def test_postcode_without_space_gets_normalised(self, importer):
        # Current behaviour: ensure proper spacing is inserted.
        assert importer.extract_postcode('PR75AS') == 'PR7 5AS'

    def test_no_postcode_returns_none(self, importer):
        assert importer.extract_postcode('just some street name') is None

    def test_lowercase_is_upcased_and_matched(self, importer):
        assert importer.extract_postcode('bb11 1ba') == 'BB11 1BA'


# -- Customer-name cleaning ------------------------------------------------

class TestCleanCustomerName:
    def test_strips_customer_signature_prefix(self, importer):
        assert importer.clean_customer_name('Customer Signature POSTURITE') == 'POSTURITE'

    def test_removes_triple_asterisk_notes(self, importer):
        assert importer.clean_customer_name('FUJITSU ***urgent*** SERVICES') == 'FUJITSU  SERVICES'.replace('  ', ' ')

    def test_collapses_whitespace(self, importer):
        assert importer.clean_customer_name('FUJITSU    SERVICES   LIMITED') == 'FUJITSU SERVICES LIMITED'

    def test_strips_leading_numbers(self, importer):
        assert importer.clean_customer_name('123 POSTURITE') == 'POSTURITE'


# -- Validate-job business rules -------------------------------------------

class TestValidateJob:
    def test_missing_job_number_rejected(self, importer):
        assert importer.validate_job({'customer': 'POSTURITE', 'activity': 'INSTALL'}) is False

    def test_missing_customer_and_activity_rejected(self, importer):
        assert importer.validate_job({'job_number': '123'}) is False

    def test_rico_with_no_activity_rejected(self, importer):
        assert importer.validate_job({
            'job_number': '123', 'customer': 'RICO Depot', 'activity': '',
        }) is False

    def test_paypoint_van_stock_audit_rejected(self, importer):
        assert importer.validate_job({
            'job_number': '123',
            'customer': 'PAYPOINT LIMITED - VAN STOCK AUDIT',
            'activity': 'AUDIT',
        }) is False

    def test_valid_job_accepted(self, importer):
        assert importer.validate_job({
            'job_number': '456', 'customer': 'POSTURITE', 'activity': 'INSTALL',
        }) is True


# -- Customer-specific parsers ---------------------------------------------

class TestParsePosturiteJob:
    def test_desk_install_extracts_activity_address_postcode(self, importer):
        job = {}
        # Shape matches what pdfplumber produces for a POSTURITE job block.
        lines = [
            'Customer Signature POSTURITE',
            'DESK INSTALL',
            'DEL001',
            '07709858783JOANNE CARR',
            '51 CHAPEL STREET',
            'COPPULL',
            'CHORLEY',
            'PR7 5AS',
        ]
        importer.parse_posturite_job(job, lines)

        assert job['activity'] == 'DESK INSTALL'
        assert job['postcode'] == 'PR7 5AS'
        assert 'JOANNE CARR' in job['job_address']
        assert '51 CHAPEL STREET' in job['job_address']
        assert 'CHORLEY' in job['job_address']

    def test_defaults_to_install_when_no_specific_activity(self, importer):
        job = {}
        importer.parse_posturite_job(job, ['Customer Signature POSTURITE'])
        assert job['activity'] == 'INSTALL'


class TestParseEpayJob:
    def test_collection_with_store_and_postcode(self, importer):
        job = {}
        lines = [
            'Customer Signature EPAY LIMITED',
            'COLLECTION',
            '07873640608 FOUNDRY ARMS STORE',
            '42 BIRLEY STREET',
            'BLACKBURN',
            'LANCASHIRE',
            'BB1 5DN',
        ]
        importer.parse_epay_job(job, lines)

        assert job['activity'] == 'COLLECTION'
        assert job['postcode'] == 'BB1 5DN'
        assert 'FOUNDRY ARMS STORE' in job['job_address']
        assert 'BLACKBURN' in job['job_address']


class TestParseTechJob:
    def test_tech_exchange_for_cxm_uk_foods(self, importer):
        job = {}
        lines = [
            'Customer Signature CXM',
            'TECH EXCHANGE',
            '3UK FOODS STORE LIMITED',
            '47 SCOTLAND ROAD',
            'NELSON',
            'BB9 7UT',
        ]
        importer.parse_tech_job(job, lines)

        assert job['activity'] == 'TECH EXCHANGE'
        assert job['postcode'] == 'BB9 7UT'
        assert 'UK FOODS STORE LIMITED' in job['job_address']

    def test_non_tech_exchange_wins_over_tech_exchange(self, importer):
        job = {}
        lines = [
            'Customer Signature FUJITSU SERVICES LIMITED - EE',
            'NON TECH EXCHANGE',
            'ORANGE (BURNLEY)',
            '52 The Mall',
            'BB11 1BA',
        ]
        importer.parse_tech_job(job, lines)

        assert job['activity'] == 'NON TECH EXCHANGE'


# -- Payslip header parser -------------------------------------------------

class TestPayslipHeader:
    def test_extracts_pay_date_and_period_end(self, extractor):
        text = (
            'Verification Number  VAT Number  Pay Date  Periods  Period End\n'
            '12345678  9876543210  06/10/2025  1  03/10/2025\n'
        )
        header = extractor.parse_payslip_header(text)

        assert header.get('pay_date') == '06/10/2025'
        assert header.get('period_end') == '03/10/2025'
        # VAT number regex grabs the first 10-digit sequence in the values line.
        assert header.get('vat_number') == '9876543210'

    def test_missing_header_returns_empty_dict(self, extractor):
        assert extractor.parse_payslip_header('some unrelated text') == {}
