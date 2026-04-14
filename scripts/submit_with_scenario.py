#!/usr/bin/env python3
"""Submit Q1 with HMRC test scenario."""

import sys
import json
sys.path.insert(0, '/Users/danielhanson/CascadeProjects/Wages-App')

from app.services.hmrc_mapper import HMRCMapper
from app.services.hmrc_client import HMRCClient

print('=' * 70)
print('Q1 2025/26 HMRC SANDBOX SUBMISSION (with test scenario)')
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

# Calculate totals
total_expenses = sum(
    exp['amount'] for exp in submission['expenses'].values()
)
net_profit = submission['incomes']['turnover'] - total_expenses

print('\n--- SUMMARY ---')
print(f'Income: £{submission["incomes"]["turnover"]:,.2f}')
print(f'Total Expenses: £{total_expenses:,.2f}')
print(f'Net Profit: £{net_profit:,.2f}')

# Validate
validation = HMRCMapper.validate_submission(submission)
print(f'\nValidation: {"✓ PASSED" if validation["valid"] else "✗ FAILED"}')

if not validation['valid']:
    print(f'Errors: {validation["errors"]}')
    sys.exit(1)

# Try with stateful test scenario
print('\n--- ATTEMPTING SUBMISSION ---')
print('Note: HMRC Sandbox requires pre-configured test data')
print('Trying with XAIS00000000001 (standard test business ID)...')

client = HMRCClient()
nino = 'BW029467A'
business_id = 'XAIS00000000001'

# Try direct submission
result = client.create_period(nino, business_id, submission)

print('\n' + '=' * 70)
print('HMRC RESPONSE')
print('=' * 70)
print(json.dumps(result, indent=2))

if result.get('success'):
    print('\n✓ SUBMISSION SUCCESSFUL')
    print(f'Status Code: {result.get("status_code")}')
else:
    print('\n✗ SUBMISSION FAILED')
    print(f'Status Code: {result.get("status_code")}')
    print(f'Error: {result.get("error")}')
    
    # Provide guidance
    print('\n' + '=' * 70)
    print('SANDBOX SETUP REQUIRED')
    print('=' * 70)
    print('The HMRC sandbox requires test data to be pre-configured.')
    print('You need to either:')
    print('1. Use HMRC Developer Hub to create test data for BW029467A')
    print('2. Use a different test user with pre-configured data')
    print('3. Use the API Test Support endpoints to set up test data')
    print('\nThe submission payload is valid and ready to send.')
    print('Once sandbox test data is configured, re-run this script.')
