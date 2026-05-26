# HMRC Sandbox Integration Testing

## Overview

The HMRC sandbox integration test script (`scripts/hmrc_sandbox_test.py`) performs comprehensive end-to-end testing of all HMRC MTD API endpoints against the actual HMRC sandbox environment. This generates testing activity logs that HMRC can review as part of the Production Approvals Checklist.

## Purpose

HMRC requires evidence that your application has successfully called every required MTD endpoint before granting production access. This script:

- Makes real API calls to HMRC's sandbox servers
- Tests all endpoints required by the Production Approvals Checklist
- Logs detailed results for each API call
- Generates a comprehensive test report

## Prerequisites

### 1. Environment Configuration

Ensure your `.env` file contains:

```bash
HMRC_ENVIRONMENT=sandbox
HMRC_CLIENT_ID=your-sandbox-client-id
HMRC_CLIENT_SECRET=your-sandbox-client-secret
HMRC_REDIRECT_URI=http://localhost:5000/api/hmrc/auth/callback
```

### 2. OAuth Authentication

You must have a valid OAuth access token before running the test:

1. Start the web application: `./start_web.sh`
2. Navigate to Settings > HMRC
3. Click "Connect to HMRC"
4. Complete the OAuth authorization flow
5. Verify you see "Connected to HMRC" status

### 3. Sandbox Test Data

The script will attempt to:
- Use your authenticated NINO from the OAuth token
- Create test businesses if needed (using HMRC's test support API)
- Generate test data for losses, BSAS, calculations, etc.

## Running the Test

### Basic Usage

```bash
python scripts/hmrc_sandbox_test.py
```

The script will:
1. Check all prerequisites
2. Prompt for confirmation
3. Run all tests in sequence
4. Generate a detailed report

### What Gets Tested

The script tests **30 different API endpoints** covering:

#### Business Details (2 tests)
- GET Business Details - list businesses
- GET Business Detail - retrieve specific business

#### Obligations (2 tests)
- GET Income & Expenses Obligations
- GET Final Declaration Obligations

#### Cumulative Period Summaries (2 tests)
- POST Cumulative Period Summary
- GET Cumulative Period Summary

#### Annual Submissions (2 tests)
- GET Annual Submission
- PUT Annual Submission (with allowances/adjustments)

#### BSAS - Business Source Adjustable Summary (4 tests)
- GET List BSAS summaries
- POST Trigger BSAS
- GET BSAS summary
- POST Submit BSAS adjustments

#### Losses (5 tests)
- GET List losses
- POST Create loss
- GET Retrieve loss
- PUT Update loss amount
- DELETE Delete loss

#### Tax Calculations (4 tests)
- POST Trigger Calculation (intent-to-finalise)
- GET List Calculations
- GET Retrieve Calculation
- POST Trigger Calculation (intent-to-amend)

#### Final Declarations (2 tests)
- POST Submit Final Declaration
- POST Submit Confirm Amendment

#### Periods of Account (4 tests)
- POST Create Period of Account
- GET List Periods of Account
- PUT Update Period of Account
- DELETE Delete Period of Account

#### Late Accounting Date Rule (3 tests)
- GET Late Accounting Date Rule
- PUT Disapply LADR
- DELETE Withdraw LADR disapplication

## Understanding Results

### Log Output

Results are saved to: `logs/hmrc_sandbox_test_results.log`

Each test logs:
- ✓ PASS or ✗ FAIL status
- HTTP method and endpoint
- Status code returned
- Error message (if failed)
- Response details (in debug mode)

### Expected Behavior

**Some failures are normal in sandbox:**
- 404 errors for non-existent test data
- 403 errors for operations not allowed in current state
- 422 validation errors for incomplete test data

**What matters for HMRC approval:**
- The API calls were made (visible in HMRC's logs)
- Your application handles responses correctly
- Fraud prevention headers are sent properly

### Summary Report

At the end, you'll see:
```
Total Tests: 30
Passed: 25 (83.3%)
Failed: 5 (16.7%)
```

Failed tests are listed with details. Review these to understand if they're:
- Expected sandbox limitations
- Missing test data
- Actual issues requiring fixes

## Troubleshooting

### "No valid OAuth access token found"

**Solution:** Authenticate via the web UI first (see Prerequisites #2)

### "HMRC_ENVIRONMENT is 'production', must be 'sandbox'"

**Solution:** Update your `.env` file to set `HMRC_ENVIRONMENT=sandbox`

### "No business ID available"

**Cause:** The test NINO doesn't have any businesses registered

**Solution:** The script will attempt to create a test business automatically. If this fails, you may need to use HMRC's test support API manually.

### 401 Unauthorized errors

**Cause:** OAuth token has expired

**Solution:** Re-authenticate via the web UI

### 403 Forbidden errors

**Cause:** Sandbox test scenario doesn't allow the operation

**Solution:** This is expected for some endpoints. HMRC can still see the attempt in their logs.

### 422 Validation errors

**Cause:** Test data doesn't meet HMRC's validation rules

**Solution:** Review the validation errors in the log. Adjust test data if needed, or accept that the call was made (which is what HMRC needs to see).

## Test Scenarios

The script uses HMRC's `Gov-Test-Scenario` header to simulate different responses:

- **STATEFUL**: Default scenario, maintains state across calls
- **QUARTERLY_FULFILLED**: Returns fulfilled quarterly obligations

You can modify the script to test other scenarios documented in HMRC's API documentation.

## Production Approvals Checklist

This script helps you complete the **Testing Evidence** section of HMRC's Production Approvals Checklist by demonstrating:

1. ✓ Your application can call all required MTD endpoints
2. ✓ Fraud prevention headers are correctly implemented
3. ✓ OAuth authentication works properly
4. ✓ Error handling is in place
5. ✓ API versioning is correct

## Next Steps

After running the test:

1. **Review the log file** for any unexpected failures
2. **Fix any real issues** (not sandbox limitations)
3. **Re-run the test** to verify fixes
4. **Keep the log file** as evidence for HMRC
5. **Note the test date** - HMRC can verify API calls in their logs

## Important Notes

- **Do NOT run this against production** - it's designed for sandbox only
- **Do NOT commit credentials** - they're in `.env` which is gitignored
- **Do NOT automate this** - it's a manual verification tool
- **Keep logs secure** - they may contain sensitive test data

## Support

If you encounter issues:

1. Check the detailed log file: `logs/hmrc_sandbox_test_results.log`
2. Review HMRC's API documentation for the failing endpoint
3. Verify your sandbox credentials are correct
4. Ensure your OAuth token is fresh and valid

## Last Updated

Script created: May 26, 2026
Last sandbox test run: [To be filled in after running]
