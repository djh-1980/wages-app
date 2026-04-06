#!/usr/bin/env python3
"""Get business ID from HMRC sandbox."""

import sys
import json
sys.path.insert(0, '/Users/danielhanson/CascadeProjects/Wages-App')

from app.services.hmrc_client import HMRCClient

client = HMRCClient()
nino = 'BW029467A'

print('Checking for existing businesses...')
result = client.get_business_details(nino)

if result.get('success'):
    print('\n✓ Business Details API Response:')
    print(json.dumps(result, indent=2))
else:
    print('\n✗ Business Details API failed, trying Business List API...')
    result = client.get_business_list(nino)
    
    if result.get('success'):
        print('\n✓ Business List API Response:')
        print(json.dumps(result, indent=2))
    else:
        print('\n✗ Business List API also failed')
        print(f'Error: {result.get("error")}')
        print('\nTrying to get obligations (which includes business IDs)...')
        
        result = client.get_obligations(nino, test_scenario='QUARTERLY_PERIOD')
        
        if result.get('success'):
            print('\n✓ Obligations Response:')
            print(json.dumps(result, indent=2))
            
            obligations = result.get('data', {}).get('obligations', [])
            if obligations:
                business_id = obligations[0].get('businessId')
                print(f'\n✓ Found Business ID: {business_id}')
        else:
            print('\n✗ Obligations also failed')
            print(f'Error: {result.get("error")}')
            print('\nAttempting to create test business...')
            
            result = client.create_test_business(nino)
            
            if result.get('success'):
                print('\n✓ Test Business Created:')
                print(json.dumps(result, indent=2))
            else:
                print('\n✗ Failed to create test business')
                print(json.dumps(result, indent=2))
