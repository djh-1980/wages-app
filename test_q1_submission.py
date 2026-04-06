#!/usr/bin/env python3
"""Test Q1 2025/26 HMRC sandbox submission."""

import sys
import json
sys.path.insert(0, '/Users/danielhanson/CascadeProjects/Wages-App')

from app.services.hmrc_mapper import HMRCMapper
from app.services.hmrc_client import HMRCClient

print('=' * 70)
print('Q1 2025/26 HMRC SANDBOX SUBMISSION')
print('=' * 70)

# Build submission
tax_year = '2025/2026'
period_id = 'Q1'

print(f'\nBuilding submission for {tax_year} {period_id}...')
submission = HMRCMapper.build_period_submission(tax_year, period_id)

if not submission:
    print('ERROR: Could not build submission')
    sys.exit(1)

print('\n--- SUBMISSION DATA ---')
print(json.dumps(submission, indent=2))

# Validate
print('\n--- VALIDATION ---')
validation = HMRCMapper.validate_submission(submission)
print(f'Valid: {validation["valid"]}')
if not validation['valid']:
    print(f'Errors: {validation["errors"]}')
    sys.exit(1)

# Submit to HMRC
print('\n--- SUBMITTING TO HMRC SANDBOX ---')
client = HMRCClient()

# Use sandbox test NINO and Business ID
nino = 'BW029467A'  # Jagger Jerry test user
business_id = 'XAIS00000000001'  # Test business ID

print(f'NINO: {nino}')
print(f'Business ID: {business_id}')
print(f'Period: {submission["from"]} to {submission["to"]}')
print(f'Income: £{submission["incomes"]["turnover"]:,.2f}')

result = client.create_period(nino, business_id, submission)

print('\n' + '=' * 70)
print('HMRC SANDBOX RESPONSE')
print('=' * 70)
print(json.dumps(result, indent=2))

if result.get('success'):
    print('\n✓ SUBMISSION SUCCESSFUL')
    print(f'Status Code: {result.get("status_code")}')
    if result.get('data'):
        print(f'Response Data: {json.dumps(result["data"], indent=2)}')
else:
    print('\n✗ SUBMISSION FAILED')
    print(f'Error: {result.get("error")}')
    if result.get('validation_errors'):
        print('\nValidation Errors:')
        for err in result['validation_errors']:
            print(f'  - {err["field"]}: {err["message"]}')
    if result.get('details'):
        print(f'\nDetails: {json.dumps(result["details"], indent=2)}')
