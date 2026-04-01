#!/usr/bin/env python3
"""
Create a new HMRC sandbox test user with self-employment income.

This script uses the HMRC Create Test User API to generate a fresh test user
with MTD Income Tax Self Assessment capabilities.

API Documentation:
https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/api-platform-test-user/1.0
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# HMRC API Configuration
HMRC_CLIENT_ID = os.getenv('HMRC_CLIENT_ID')
HMRC_CLIENT_SECRET = os.getenv('HMRC_CLIENT_SECRET')
HMRC_ENVIRONMENT = os.getenv('HMRC_ENVIRONMENT', 'sandbox')

if HMRC_ENVIRONMENT == 'sandbox':
    BASE_URL = 'https://test-api.service.hmrc.gov.uk'
else:
    BASE_URL = 'https://api.service.hmrc.gov.uk'


def get_server_token():
    """
    Get a server-to-server OAuth token using client credentials grant.
    This is used for the Create Test User API which doesn't require user authorization.
    """
    print("🔑 Getting server token...")
    
    token_url = f"{BASE_URL}/oauth/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': HMRC_CLIENT_ID,
        'client_secret': HMRC_CLIENT_SECRET,
        'scope': 'create:test-user'
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            print(f"✅ Server token obtained (expires in {token_data.get('expires_in')} seconds)")
            return access_token
        else:
            print(f"❌ Failed to get server token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting server token: {e}")
        return None


def create_test_user(access_token):
    """
    Create a new HMRC sandbox test user with self-employment.
    
    Args:
        access_token: OAuth server token
        
    Returns:
        dict: Test user details including NINO, credentials, and business IDs
    """
    print("\n👤 Creating new test user...")
    
    create_user_url = f"{BASE_URL}/create-test-user/individuals"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.hmrc.1.0+json'
    }
    
    # Request a test user with self-employment capabilities
    payload = {
        'serviceNames': [
            'national-insurance',
            'self-assessment',
            'mtd-income-tax'
        ]
    }
    
    try:
        response = requests.post(create_user_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            user_data = response.json()
            print("✅ Test user created successfully!")
            return user_data
        else:
            print(f"❌ Failed to create test user: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return None


def save_test_user_details(user_data):
    """
    Save test user details to HMRC_TEST_USER_DETAILS.txt
    
    Args:
        user_data: Test user data from HMRC API
    """
    print("\n💾 Saving test user details...")
    
    docs_dir = Path(__file__).parent.parent / 'docs'
    output_file = docs_dir / 'HMRC_TEST_USER_DETAILS.txt'
    
    # Create backup of existing file
    if output_file.exists():
        backup_file = docs_dir / f'HMRC_TEST_USER_DETAILS_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        output_file.rename(backup_file)
        print(f"📦 Backed up existing file to: {backup_file.name}")
    
    # Format the output
    content = f"""================================================================================
HMRC MTD TEST USER CREDENTIALS
================================================================================

IMPORTANT: These are SANDBOX test credentials only. Do NOT use in production.

Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

--------------------------------------------------------------------------------
TEST USER LOGIN
--------------------------------------------------------------------------------
User ID:           {user_data.get('userId', 'N/A')}
Password:          {user_data.get('password', 'N/A')}
Email:             {user_data.get('emailAddress', 'N/A')}

--------------------------------------------------------------------------------
INDIVIDUAL DETAILS
--------------------------------------------------------------------------------
National Insurance Number (NINO):  {user_data.get('nino', 'N/A')}
Name:                               {user_data.get('individualDetails', {}).get('firstName', 'N/A')} {user_data.get('individualDetails', {}).get('lastName', 'N/A')}
Date of Birth:                      {user_data.get('individualDetails', {}).get('dateOfBirth', 'N/A')}
Address:                            {user_data.get('individualDetails', {}).get('address', {}).get('line1', 'N/A')}
                                    {user_data.get('individualDetails', {}).get('address', {}).get('line2', '')}
                                    {user_data.get('individualDetails', {}).get('address', {}).get('postcode', 'N/A')}

Self Assessment UTR:                {user_data.get('saUtr', 'N/A')}
MTD Income Tax ID:                  {user_data.get('mtdItId', 'N/A')}

--------------------------------------------------------------------------------
SELF-EMPLOYMENT BUSINESS DETAILS
--------------------------------------------------------------------------------
"""
    
    # Add self-employment business details if present
    if 'selfEmployments' in user_data and user_data['selfEmployments']:
        for idx, business in enumerate(user_data['selfEmployments'], 1):
            content += f"""
Business {idx}:
  Business ID:                      {business.get('businessId', 'N/A')}
  Trading Name:                     {business.get('tradingName', 'N/A')}
  Business Description:             {business.get('businessDescription', 'N/A')}
  Business Start Date:              {business.get('businessStartDate', 'N/A')}
  Accounting Type:                  {business.get('accountingType', 'N/A')}
"""
    else:
        content += """
No self-employment businesses created automatically.
Use the standard test business ID: XAIS00000000001
Or create one via: POST /test-support/self-assessment/ni/{nino}/self-employments
"""
    
    content += f"""
--------------------------------------------------------------------------------
HMRC APPLICATION CREDENTIALS
--------------------------------------------------------------------------------
Client ID:          {HMRC_CLIENT_ID}
Client Secret:      [Stored in .env file]
Redirect URI:       http://localhost:5001/api/hmrc/auth/callback
Environment:        {HMRC_ENVIRONMENT}

--------------------------------------------------------------------------------
API SUBSCRIPTIONS REQUIRED
--------------------------------------------------------------------------------
✓ Business Income Source Summary (MTD) - v3.0 (Beta)
✓ Create Test User - v1.0 (Beta)
✓ Individual Calculations (MTD) - v8.0 (Beta)
✓ Obligations (MTD) - v3.0 (Beta)
✓ Self Assessment Accounts (MTD) - v4.0 (Beta)
✓ Self Employment Business (MTD) - v5.0 (Beta)

--------------------------------------------------------------------------------
CONFIGURATION STEPS
--------------------------------------------------------------------------------

1. OAuth Connection:
   - Go to Settings > HMRC MTD
   - Click "Connect to HMRC"
   - Login with User ID: {user_data.get('userId', 'N/A')}
   - Password: {user_data.get('password', 'N/A')}
   - Authorize the application

2. Configure NINO and Business ID:
   - In HMRC Settings, click "Configure"
   - Enter NINO: {user_data.get('nino', 'N/A')}
   - Enter Business ID: XAIS00000000001 (or fetch from API)
   - Click Save

3. Fetch Business ID (if needed):
   - Open browser console (F12)
   - Run: fetch('/api/hmrc/businesses?nino={user_data.get('nino', 'N/A')}').then(r=>r.json()).then(console.log)
   - Copy the businessId from the response
   - Update in HMRC settings

4. Test Submission:
   - Go to Expenses page
   - Click "Submit to HMRC MTD"
   - Select tax year and quarter
   - Preview and submit

--------------------------------------------------------------------------------
RAW API RESPONSE
--------------------------------------------------------------------------------
{json.dumps(user_data, indent=2)}

================================================================================
"""
    
    # Write to file
    output_file.write_text(content)
    print(f"✅ Test user details saved to: {output_file}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("HMRC Sandbox Test User Creation")
    print("=" * 80)
    print()
    
    # Verify environment variables
    if not HMRC_CLIENT_ID or not HMRC_CLIENT_SECRET:
        print("❌ Error: HMRC_CLIENT_ID and HMRC_CLIENT_SECRET must be set in .env file")
        sys.exit(1)
    
    print(f"Environment: {HMRC_ENVIRONMENT}")
    print(f"Base URL: {BASE_URL}")
    print(f"Client ID: {HMRC_CLIENT_ID}")
    print()
    
    # Step 1: Get server token
    access_token = get_server_token()
    if not access_token:
        print("\n❌ Failed to obtain server token. Cannot proceed.")
        sys.exit(1)
    
    # Step 2: Create test user
    user_data = create_test_user(access_token)
    if not user_data:
        print("\n❌ Failed to create test user. Cannot proceed.")
        sys.exit(1)
    
    # Step 3: Display results
    print("\n" + "=" * 80)
    print("NEW TEST USER CREDENTIALS")
    print("=" * 80)
    print(f"\n📧 Email:        {user_data.get('emailAddress', 'N/A')}")
    print(f"🆔 User ID:      {user_data.get('userId', 'N/A')}")
    print(f"🔑 Password:     {user_data.get('password', 'N/A')}")
    print(f"🏢 NINO:         {user_data.get('nino', 'N/A')}")
    print(f"📋 SA UTR:       {user_data.get('saUtr', 'N/A')}")
    print(f"💼 MTD IT ID:    {user_data.get('mtdItId', 'N/A')}")
    
    if 'selfEmployments' in user_data and user_data['selfEmployments']:
        print(f"\n🏪 Self-Employment Businesses:")
        for idx, business in enumerate(user_data['selfEmployments'], 1):
            print(f"   {idx}. Business ID: {business.get('businessId', 'N/A')}")
            print(f"      Trading Name: {business.get('tradingName', 'N/A')}")
    else:
        print(f"\n🏪 Business ID:  XAIS00000000001 (standard test ID)")
    
    # Step 4: Save to file
    save_test_user_details(user_data)
    
    print("\n" + "=" * 80)
    print("✅ SUCCESS - Test user created and saved!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Go to http://127.0.0.1:5001/settings/hmrc")
    print("2. Click 'Connect to HMRC'")
    print(f"3. Login with User ID: {user_data.get('userId', 'N/A')}")
    print(f"4. Password: {user_data.get('password', 'N/A')}")
    print("5. Authorize the application")
    print(f"6. Configure NINO: {user_data.get('nino', 'N/A')}")
    print("7. Configure Business ID: XAIS00000000001")
    print()


if __name__ == '__main__':
    main()
