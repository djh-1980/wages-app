#!/usr/bin/env python3
"""
HMRC Sandbox Integration Test Script

This script performs a comprehensive end-to-end test of all HMRC MTD API endpoints
against the actual HMRC sandbox environment. It is designed to generate testing
activity logs that HMRC can review as part of the Production Approvals Checklist.

IMPORTANT: This script makes REAL API calls to HMRC's sandbox servers.
It requires valid sandbox credentials and an active OAuth access token.

Usage:
    python scripts/hmrc_sandbox_test.py              # Non-stateful (scenario-based)
    python scripts/hmrc_sandbox_test.py --stateful   # Stateful mode (requires test data)

Requirements:
    - HMRC_ENVIRONMENT=sandbox in .env
    - Valid HMRC_CLIENT_ID and HMRC_CLIENT_SECRET
    - Active OAuth access token (authenticate via web UI first)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.config import Config
from app.services.hmrc_client import HMRCClient
from app.services.hmrc_auth import HMRCAuthService


# Configure logging
LOG_FILE = project_root / 'logs' / 'hmrc_sandbox_test_results.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Dummy IDs for non-stateful testing (format-valid but not real)
DUMMY_BUSINESS_ID = 'XAIS12345678901'
DUMMY_CALCULATION_ID = 'f2fb30e5-4ab6-4a29-b3c1-c7264259ff1c'
DUMMY_BSAS_ID = 'f2fb30e5-4ab6-4a29-b3c1-c7264259ff1c'
DUMMY_LOSS_ID = 'AAZZ1234567890a'
DUMMY_PERIOD_ID = '2025-04-06_2026-04-05'


class HMRCSandboxTester:
    """Comprehensive HMRC sandbox integration tester."""

    def __init__(self, stateful_mode=False):
        self.config = Config()
        self.client = HMRCClient()
        self.auth_service = HMRCAuthService()
        self.results = []
        self.test_nino = None
        self.test_business_id = DUMMY_BUSINESS_ID
        self.test_tax_year = '2025-26'
        self.test_calculation_id = DUMMY_CALCULATION_ID
        self.test_bsas_id = DUMMY_BSAS_ID
        self.test_loss_id = DUMMY_LOSS_ID
        self.test_period_id = DUMMY_PERIOD_ID
        self.stateful_mode = stateful_mode

    def log_result(self, endpoint, method, status_code, success, error=None, details=None):
        """Log test result for an API call."""
        result = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'success': success,
            'error': error,
            'details': details
        }
        self.results.append(result)

        status = '✓ PASS' if success else '✗ FAIL'
        logger.info(f"{status} | {method} {endpoint} | Status: {status_code}")
        if error:
            logger.error(f"  Error: {error}")
        if details:
            logger.debug(f"  Details: {json.dumps(details, indent=2)}")

    def check_prerequisites(self):
        """Check that all prerequisites are met."""
        logger.info("=" * 80)
        logger.info("HMRC SANDBOX INTEGRATION TEST - PREREQUISITES CHECK")
        logger.info("=" * 80)

        # Check environment
        if self.config.HMRC_ENVIRONMENT != 'sandbox':
            logger.error(f"HMRC_ENVIRONMENT is '{self.config.HMRC_ENVIRONMENT}', must be 'sandbox'")
            return False

        logger.info(f"✓ HMRC Environment: {self.config.HMRC_ENVIRONMENT}")
        logger.info(f"✓ API Base URL: {self.config.HMRC_API_BASE_URL}")

        # Check credentials
        if not self.config.HMRC_CLIENT_ID or self.config.HMRC_CLIENT_ID == 'your-client-id-here':
            logger.error("HMRC_CLIENT_ID not configured")
            return False

        if not self.config.HMRC_CLIENT_SECRET or self.config.HMRC_CLIENT_SECRET == 'your-client-secret-here':
            logger.error("HMRC_CLIENT_SECRET not configured")
            return False

        logger.info(f"✓ Client ID: {self.config.HMRC_CLIENT_ID[:10]}...")

        # Check OAuth token
        access_token = self.auth_service.get_valid_access_token()
        if not access_token:
            logger.error("No valid OAuth access token found")
            logger.error("Please authenticate via the web UI first:")
            logger.error("  1. Start the web app: ./start_web.sh")
            logger.error("  2. Go to Settings > HMRC")
            logger.error("  3. Click 'Connect to HMRC'")
            logger.error("  4. Complete the OAuth flow")
            return False

        logger.info("✓ OAuth access token is valid")

        # Get test NINO from stored credentials
        credentials = self.auth_service.get_stored_credentials()
        if credentials and credentials.get('nino'):
            self.test_nino = credentials['nino']
            logger.info(f"✓ Test NINO: {self.test_nino}")
        else:
            # Use NINO from environment or default sandbox test NINO
            self.test_nino = os.environ.get('HMRC_TEST_NINO', 'AA123456A')
            logger.info(f"✓ Using test NINO: {self.test_nino}")

        return True

    def setup_test_business(self):
        """Create or retrieve test business for sandbox testing (stateful mode only)."""
        if not self.stateful_mode:
            logger.info(f"\n--- Using dummy business ID: {self.test_business_id} (non-stateful mode) ---")
            return True

        logger.info("\n--- Setup: Create/Retrieve Test Business (Stateful Mode) ---")

        # First, check if a business already exists
        result = self.client.get_business_details(self.test_nino)
        if result.get('success') and result.get('data'):
            businesses = result['data'].get('businessData', [])
            if businesses:
                self.test_business_id = businesses[0].get('businessId')
                logger.info(f"✓ Found existing business ID: {self.test_business_id}")
                return True

        # No business exists, create one using sandbox test support API
        logger.info("No existing business found, creating test business...")
        result = self.client.create_test_business(self.test_nino)

        self.log_result(
            f"/test-support/self-assessment/ni/{self.test_nino}/self-employments",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # Extract business ID from creation response
        if result.get('success') and result.get('data'):
            self.test_business_id = result['data'].get('businessId')
            if self.test_business_id:
                logger.info(f"✓ Created test business ID: {self.test_business_id}")
                return True

        logger.warning("Failed to create or retrieve test business in stateful mode")
        logger.info(f"Falling back to dummy business ID: {DUMMY_BUSINESS_ID}")
        self.test_business_id = DUMMY_BUSINESS_ID
        return True

    def test_business_details_list(self):
        """Test: GET Business Details - list businesses."""
        logger.info("\n--- Test: List Business Details ---")
        result = self.client.get_business_details(self.test_nino)

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/list",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract business ID for subsequent tests
        if self.stateful_mode and result.get('success') and result.get('data'):
            businesses = result['data'].get('businessData', [])
            if businesses:
                self.test_business_id = businesses[0].get('businessId')
                logger.info(f"Using business ID: {self.test_business_id}")

        return result.get('success', False)

    def test_business_detail_get(self):
        """Test: GET Business Detail - retrieve specific business."""
        logger.info("\n--- Test: Get Business Detail ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.get_business_detail(self.test_nino, self.test_business_id)

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_obligations_ie(self):
        """Test: GET Obligations - retrieve I&E obligations."""
        logger.info("\n--- Test: Get Income & Expenses Obligations ---")
        # Use QUARTERLY_FULFILLED scenario for non-stateful, or None for stateful
        test_scenario = None if self.stateful_mode else 'QUARTERLY_FULFILLED'
        result = self.client.get_obligations(
            self.test_nino,
            from_date='2025-04-06',
            to_date='2026-04-05',
            test_scenario=test_scenario
        )

        self.log_result(
            f"/individuals/business/self-employment/{self.test_nino}/obligations",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_obligations_final_declaration(self):
        """Test: GET Obligations - retrieve Final Declaration obligations."""
        logger.info("\n--- Test: Get Final Declaration Obligations ---")
        result = self.client.get_final_declaration_obligations(
            self.test_nino,
            from_date='2025-04-06',
            to_date='2026-04-05'
        )

        self.log_result(
            f"/obligations/details/{self.test_nino}/crystallisation",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_cumulative_period_submit(self):
        """Test: POST Cumulative Period Summary - submit quarterly update."""
        logger.info("\n--- Test: Submit Cumulative Period Summary ---")
        logger.info(f"Using business ID: {self.test_business_id}")

        period_data = {
            'periodDates': {
                'periodStartDate': '2025-04-06',
                'periodEndDate': '2025-07-05'
            },
            'periodIncome': {
                'turnover': 5000.00,
                'other': 100.00
            },
            'periodExpenses': {
                'costOfGoods': 1000.00,
                'adminCosts': 500.00,
                'businessEntertainmentCosts': 50.00,
                'advertisingCosts': 200.00,
                'other': 100.00
            }
        }

        result = self.client.submit_cumulative_period(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year,
            period_data
        )

        self.log_result(
            f"/individuals/business/self-employment/{self.test_nino}/{self.test_business_id}/period/cumulative/{self.test_tax_year}",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_cumulative_period_get(self):
        """Test: GET Cumulative Period Summary - retrieve it back."""
        logger.info("\n--- Test: Get Cumulative Period Summary ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.get_cumulative_period(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year
        )

        self.log_result(
            f"/individuals/business/self-employment/{self.test_nino}/{self.test_business_id}/period/cumulative/{self.test_tax_year}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_annual_submission_get(self):
        """Test: GET Annual Submission - retrieve annual summary."""
        logger.info("\n--- Test: Get Annual Submission ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.get_annual_summary(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year
        )

        self.log_result(
            f"/individuals/business/self-employment/{self.test_nino}/{self.test_business_id}/annual/{self.test_tax_year}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_annual_submission_put(self):
        """Test: PUT Annual Submission - update annual summary."""
        logger.info("\n--- Test: Update Annual Submission ---")
        logger.info(f"Using business ID: {self.test_business_id}")

        annual_data = {
            'allowances': {
                'annualInvestmentAllowance': 1000.00,
                'capitalAllowanceMainPool': 500.00,
                'zeroEmissionsGoodsVehicleAllowance': 200.00
            },
            'adjustments': {
                'includedNonTaxableProfits': 100.00,
                'overlapReliefUsed': 50.00,
                'accountingAdjustment': 25.00
            }
        }

        result = self.client.update_annual_summary(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year,
            annual_data
        )

        self.log_result(
            f"/individuals/business/self-employment/{self.test_nino}/{self.test_business_id}/annual/{self.test_tax_year}",
            "PUT",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_bsas_list(self):
        """Test: GET BSAS - list BSAS summaries."""
        logger.info("\n--- Test: List BSAS Summaries ---")
        result = self.client.list_bsas_summaries(
            self.test_nino,
            tax_year=self.test_tax_year,
            type_of_business='self-employment'
        )

        self.log_result(
            f"/individuals/self-assessment/adjustable-summary/{self.test_nino}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract BSAS ID if available
        if self.stateful_mode and result.get('success') and result.get('data'):
            summaries = result['data'].get('summaries', [])
            if summaries:
                self.test_bsas_id = summaries[0].get('calculationId')
                logger.info(f"Using BSAS ID: {self.test_bsas_id}")

        return result.get('success', False)

    def test_bsas_trigger(self):
        """Test: POST BSAS - trigger a BSAS."""
        logger.info("\n--- Test: Trigger BSAS ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.trigger_bsas(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year,
            type_of_business='self-employment'
        )

        self.log_result(
            f"/individuals/self-assessment/adjustable-summary/{self.test_nino}/trigger",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract BSAS ID from trigger response
        if self.stateful_mode and result.get('success') and result.get('data'):
            self.test_bsas_id = result['data'].get('calculationId')
            logger.info(f"Triggered BSAS ID: {self.test_bsas_id}")

        return result.get('success', False)

    def test_bsas_get(self):
        """Test: GET BSAS - retrieve the triggered summary."""
        logger.info("\n--- Test: Get BSAS Summary ---")
        logger.info(f"Using BSAS ID: {self.test_bsas_id}")
        result = self.client.get_bsas_summary(
            self.test_nino,
            self.test_bsas_id,
            tax_year=self.test_tax_year,
            type_of_business='self-employment'
        )

        self.log_result(
            f"/individuals/self-assessment/adjustable-summary/{self.test_nino}/self-employment/{self.test_bsas_id}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_bsas_submit_adjustments(self):
        """Test: POST BSAS - submit adjustments."""
        logger.info("\n--- Test: Submit BSAS Adjustments ---")
        logger.info(f"Using BSAS ID: {self.test_bsas_id}")

        adjustments = {
            'income': {
                'turnover': 100.00
            },
            'expenses': {
                'costOfGoods': 50.00,
                'adminCosts': 25.00
            }
        }

        result = self.client.submit_bsas_adjustments(
            self.test_nino,
            self.test_bsas_id,
            adjustments
        )

        self.log_result(
            f"/individuals/self-assessment/adjustable-summary/{self.test_nino}/self-employment/{self.test_bsas_id}/adjust",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_losses_list(self):
        """Test: GET Losses - list losses."""
        logger.info("\n--- Test: List Losses ---")
        result = self.client.list_losses(
            self.test_nino,
            tax_year=self.test_tax_year,
            type_of_loss='self-employment'
        )

        self.log_result(
            f"/individuals/losses/{self.test_nino}/brought-forward-losses",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract loss ID if available
        if self.stateful_mode and result.get('success') and result.get('data'):
            losses = result['data'].get('losses', [])
            if losses:
                self.test_loss_id = losses[0].get('lossId')
                logger.info(f"Using loss ID: {self.test_loss_id}")

        return result.get('success', False)

    def test_losses_create(self):
        """Test: POST Losses - create a test loss."""
        logger.info("\n--- Test: Create Loss ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.create_loss(
            self.test_nino,
            '2024-25',  # Previous tax year
            'self-employment',
            self.test_business_id,
            1000.00
        )

        self.log_result(
            f"/individuals/losses/{self.test_nino}/brought-forward-losses",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract loss ID from creation response
        if self.stateful_mode and result.get('success') and result.get('data'):
            self.test_loss_id = result['data'].get('lossId')
            logger.info(f"Created loss ID: {self.test_loss_id}")

        return result.get('success', False)

    def test_losses_get(self):
        """Test: GET Losses - retrieve the created loss."""
        logger.info("\n--- Test: Get Loss ---")
        logger.info(f"Using loss ID: {self.test_loss_id}")
        result = self.client.get_loss(self.test_nino, self.test_loss_id)

        self.log_result(
            f"/individuals/losses/{self.test_nino}/brought-forward-losses/{self.test_loss_id}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_losses_update(self):
        """Test: PUT Losses - update the loss amount."""
        logger.info("\n--- Test: Update Loss ---")
        logger.info(f"Using loss ID: {self.test_loss_id}")
        result = self.client.update_loss(self.test_nino, self.test_loss_id, 1500.00)

        self.log_result(
            f"/individuals/losses/{self.test_nino}/brought-forward-losses/{self.test_loss_id}/change-loss-amount",
            "PUT",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_losses_delete(self):
        """Test: DELETE Losses - delete the test loss."""
        logger.info("\n--- Test: Delete Loss ---")
        logger.info(f"Using loss ID: {self.test_loss_id}")
        result = self.client.delete_loss(self.test_nino, self.test_loss_id)

        self.log_result(
            f"/individuals/losses/{self.test_nino}/brought-forward-losses/{self.test_loss_id}",
            "DELETE",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_trigger_calculation_intent_to_finalise(self):
        """Test: POST Trigger Calculation - with calculationType: 'intent-to-finalise'."""
        logger.info("\n--- Test: Trigger Calculation (Intent to Finalise) ---")
        result = self.client.trigger_crystallisation(
            self.test_nino,
            self.test_tax_year,
            calculation_type='intent-to-finalise'
        )

        self.log_result(
            f"/individuals/calculations/{self.test_nino}/self-assessment",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract calculation ID
        if self.stateful_mode and result.get('success') and result.get('data'):
            self.test_calculation_id = result['data'].get('calculationId')
            logger.info(f"Calculation ID: {self.test_calculation_id}")

        return result.get('success', False)

    def test_list_calculations(self):
        """Test: GET List Calculations."""
        logger.info("\n--- Test: List Calculations ---")
        result = self.client.list_calculations(self.test_nino, self.test_tax_year.replace('-', '/'))

        self.log_result(
            f"/individuals/calculations/{self.test_nino}/self-assessment",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract calculation ID if not already set
        if self.stateful_mode and not self.test_calculation_id and result.get('success') and result.get('data'):
            calculations = result['data'].get('calculations', [])
            if calculations:
                self.test_calculation_id = calculations[0].get('calculationId')
                logger.info(f"Using calculation ID: {self.test_calculation_id}")

        return result.get('success', False)

    def test_retrieve_calculation(self):
        """Test: GET Retrieve Calculation."""
        logger.info("\n--- Test: Retrieve Calculation ---")
        logger.info(f"Using calculation ID: {self.test_calculation_id}")
        result = self.client.retrieve_calculation(self.test_nino, self.test_calculation_id)

        self.log_result(
            f"/individuals/calculations/{self.test_nino}/self-assessment/{self.test_calculation_id}",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_trigger_calculation_intent_to_amend(self):
        """Test: POST Trigger Calculation - with calculationType: 'intent-to-amend'."""
        logger.info("\n--- Test: Trigger Calculation (Intent to Amend) ---")
        result = self.client.trigger_crystallisation(
            self.test_nino,
            self.test_tax_year,
            calculation_type='intent-to-amend'
        )

        self.log_result(
            f"/individuals/calculations/{self.test_nino}/self-assessment",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_submit_final_declaration(self):
        """Test: POST Submit Final Declaration - with declarationType: 'final-declaration'."""
        logger.info("\n--- Test: Submit Final Declaration ---")
        logger.info(f"Using calculation ID: {self.test_calculation_id}")
        result = self.client.submit_final_declaration(
            self.test_nino,
            self.test_tax_year.replace('-', '/'),
            self.test_calculation_id,
            declaration_type='final-declaration'
        )

        self.log_result(
            f"/individuals/declarations/{self.test_nino}/{self.test_tax_year}",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_submit_confirm_amendment(self):
        """Test: POST Submit Final Declaration - with declarationType: 'confirm-amendment'."""
        logger.info("\n--- Test: Submit Confirm Amendment ---")
        logger.info(f"Using calculation ID: {self.test_calculation_id}")
        result = self.client.submit_final_declaration(
            self.test_nino,
            self.test_tax_year.replace('-', '/'),
            self.test_calculation_id,
            declaration_type='confirm-amendment'
        )

        self.log_result(
            f"/individuals/declarations/{self.test_nino}/{self.test_tax_year}",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_periods_of_account_create(self):
        """Test: POST Periods of Account - create."""
        logger.info("\n--- Test: Create Period of Account ---")
        logger.info(f"Using business ID: {self.test_business_id}")

        period_data = {
            'startDate': '2025-04-06',
            'endDate': '2026-04-05'
        }

        result = self.client.create_period_of_account(
            self.test_nino,
            self.test_business_id,
            period_data
        )

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/periods-of-account",
            "POST",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract period ID
        if self.stateful_mode and result.get('success') and result.get('data'):
            self.test_period_id = result['data'].get('periodId')
            logger.info(f"Created period ID: {self.test_period_id}")

        return result.get('success', False)

    def test_periods_of_account_list(self):
        """Test: GET Periods of Account - list."""
        logger.info("\n--- Test: List Periods of Account ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.list_periods_of_account(self.test_nino, self.test_business_id)

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/periods-of-account",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        # In stateful mode, extract period ID if not already set
        if self.stateful_mode and not self.test_period_id and result.get('success') and result.get('data'):
            periods = result['data'].get('periods', [])
            if periods:
                self.test_period_id = periods[0].get('periodId')
                logger.info(f"Using period ID: {self.test_period_id}")

        return result.get('success', False)

    def test_periods_of_account_update(self):
        """Test: PUT Periods of Account - update."""
        logger.info("\n--- Test: Update Period of Account ---")
        logger.info(f"Using business ID: {self.test_business_id}, period ID: {self.test_period_id}")

        period_data = {
            'startDate': '2025-04-06',
            'endDate': '2026-04-05'
        }

        result = self.client.update_period_of_account(
            self.test_nino,
            self.test_business_id,
            self.test_period_id,
            period_data
        )

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/periods-of-account/{self.test_period_id}",
            "PUT",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_periods_of_account_delete(self):
        """Test: DELETE Periods of Account - delete."""
        logger.info("\n--- Test: Delete Period of Account ---")
        logger.info(f"Using business ID: {self.test_business_id}, period ID: {self.test_period_id}")
        result = self.client.delete_period_of_account(
            self.test_nino,
            self.test_business_id,
            self.test_period_id
        )

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/periods-of-account/{self.test_period_id}",
            "DELETE",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_ladr_get(self):
        """Test: GET Late Accounting Date Rule."""
        logger.info("\n--- Test: Get Late Accounting Date Rule ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.get_late_accounting_date_rule(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year
        )

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/{self.test_tax_year}/late-accounting-date-rule",
            "GET",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_ladr_disapply(self):
        """Test: PUT Late Accounting Date Rule - disapply."""
        logger.info("\n--- Test: Disapply Late Accounting Date Rule ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.disapply_late_accounting_date_rule(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year
        )

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/{self.test_tax_year}/late-accounting-date-rule/disapply",
            "PUT",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def test_ladr_withdraw(self):
        """Test: DELETE Late Accounting Date Rule - withdraw."""
        logger.info("\n--- Test: Withdraw Late Accounting Date Rule Disapplication ---")
        logger.info(f"Using business ID: {self.test_business_id}")
        result = self.client.withdraw_late_accounting_date_rule_disapplication(
            self.test_nino,
            self.test_business_id,
            self.test_tax_year
        )

        self.log_result(
            f"/individuals/business/details/{self.test_nino}/{self.test_business_id}/{self.test_tax_year}/late-accounting-date-rule/disapply",
            "DELETE",
            result.get('status_code', 0),
            result.get('success', False),
            result.get('error'),
            result.get('data')
        )

        return result.get('success', False)

    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("HMRC SANDBOX INTEGRATION TEST - SUMMARY")
        logger.info("=" * 80)

        passed = sum(1 for r in self.results if r['success'])
        failed = sum(1 for r in self.results if not r['success'])
        total = len(self.results)

        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"Passed: {passed} ({passed/total*100:.1f}%)")
        logger.info(f"Failed: {failed} ({failed/total*100:.1f}%)")

        if failed > 0:
            logger.info("\nFailed Tests:")
            for result in self.results:
                if not result['success']:
                    logger.info(f"  ✗ {result['method']} {result['endpoint']}")
                    logger.info(f"    Status: {result['status_code']}, Error: {result['error']}")

        logger.info(f"\nFull results saved to: {LOG_FILE}")
        logger.info("\nNote: Some failures are expected in sandbox (e.g., 404 for non-existent data).")
        logger.info("The important thing is that HMRC can see the API calls were made.")

    def run_all_tests(self):
        """Run all integration tests in sequence."""
        logger.info("\n" + "=" * 80)
        logger.info("HMRC SANDBOX INTEGRATION TEST - START")
        logger.info("=" * 80)
        logger.info(f"Test Mode: {'STATEFUL' if self.stateful_mode else 'NON-STATEFUL (Scenario-based)'}")
        logger.info(f"Test NINO: {self.test_nino}")
        logger.info(f"Tax Year: {self.test_tax_year}")
        logger.info(f"Environment: {self.config.HMRC_ENVIRONMENT}")
        logger.info(f"API Base URL: {self.config.HMRC_API_BASE_URL}")

        # Setup: Create or retrieve test business (stateful mode only)
        self.setup_test_business()

        # Run tests in correct dependency order:
        # 1. Business details and obligations
        # 2. Submit data (cumulative period) BEFORE calculations/BSAS
        # 3. Annual submission
        # 4. BSAS (requires submitted data)
        # 5. Losses
        # 6. Calculations (requires submitted data)
        # 7. Final declaration
        # 8. Periods of Account
        # 9. LADR
        test_methods = [
            # Business and obligations
            self.test_business_details_list,
            self.test_business_detail_get,
            self.test_obligations_ie,
            self.test_obligations_final_declaration,
            # Submit data FIRST (other tests depend on this)
            self.test_cumulative_period_submit,
            self.test_cumulative_period_get,
            # Annual submission
            self.test_annual_submission_get,
            self.test_annual_submission_put,
            # BSAS (requires submitted data)
            self.test_bsas_trigger,
            self.test_bsas_list,
            self.test_bsas_get,
            self.test_bsas_submit_adjustments,
            # Losses
            self.test_losses_create,
            self.test_losses_list,
            self.test_losses_get,
            self.test_losses_update,
            self.test_losses_delete,
            # Calculations (requires submitted data)
            self.test_trigger_calculation_intent_to_finalise,
            self.test_list_calculations,
            self.test_retrieve_calculation,
            self.test_trigger_calculation_intent_to_amend,
            # Final declaration
            self.test_submit_final_declaration,
            self.test_submit_confirm_amendment,
            # Periods of Account
            self.test_periods_of_account_create,
            self.test_periods_of_account_list,
            self.test_periods_of_account_update,
            self.test_periods_of_account_delete,
            # LADR
            self.test_ladr_get,
            self.test_ladr_disapply,
            self.test_ladr_withdraw,
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                logger.error(f"Exception in {test_method.__name__}: {str(e)}", exc_info=True)

        self.print_summary()


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='HMRC Sandbox Integration Test - Test all MTD API endpoints'
    )
    parser.add_argument(
        '--stateful',
        action='store_true',
        help='Use stateful mode (requires real test data). Default is non-stateful (scenario-based).'
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("HMRC SANDBOX INTEGRATION TEST")
    print("=" * 80)
    print(f"\nMode: {'STATEFUL' if args.stateful else 'NON-STATEFUL (Scenario-based)'}")
    print("\nThis script will make REAL API calls to HMRC's sandbox environment.")
    print("It will test all required MTD endpoints for the Production Approvals Checklist.")
    print("\nPrerequisites:")
    print("  - HMRC_ENVIRONMENT=sandbox in .env")
    print("  - Valid HMRC_CLIENT_ID and HMRC_CLIENT_SECRET")
    print("  - Active OAuth access token (authenticate via web UI first)")
    if args.stateful:
        print("\nStateful Mode:")
        print("  - Requires test business to exist or be creatable")
        print("  - Tests depend on actual data in sandbox")
    else:
        print("\nNon-Stateful Mode (Recommended):")
        print("  - Uses Gov-Test-Scenario headers for canned responses")
        print("  - Tests run independently without requiring real data")
        print("  - All endpoints called regardless of individual failures")
    print("\nResults will be saved to: logs/hmrc_sandbox_test_results.log")
    print("=" * 80)

    response = input("\nContinue? (y/n): ").strip().lower()
    if response != 'y':
        print("Test cancelled.")
        return

    tester = HMRCSandboxTester(stateful_mode=args.stateful)

    if not tester.check_prerequisites():
        logger.error("\nPrerequisites check failed. Please fix the issues above and try again.")
        sys.exit(1)

    tester.run_all_tests()


if __name__ == '__main__':
    main()
