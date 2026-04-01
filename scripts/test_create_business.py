#!/usr/bin/env python3
"""
Quick test script to call the create-test-business endpoint and see the exact response.
"""

import requests
import json

# Test the create-test-business endpoint
url = 'http://127.0.0.1:5001/api/hmrc/create-test-business'

payload = {
    'nino': 'OA965288C'
}

headers = {
    'Content-Type': 'application/json'
}

print("Testing create-test-business endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error: {e}")
