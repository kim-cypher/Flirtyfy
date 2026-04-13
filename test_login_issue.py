#!/usr/bin/env python
"""
Test login issue
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api"

# Create a test user first
print("=== TESTING LOGIN ISSUE ===\n")

TEST_USER = {
    "username": f"login_test_user_{int(time.time())}",
    "email": f"login_test_user_{int(time.time())}@test.com",
    "password": "TestPassword123!",
    "confirmPassword": "TestPassword123!",
    "date_of_birth": (datetime.now() - timedelta(days=365*25)).strftime("%Y-%m-%d"),
}

# Step 1: Register
print("1. REGISTERING USER...")
resp = requests.post(f"{BASE_URL}/register/", json=TEST_USER)
print(f"   Status: {resp.status_code}")
print(f"   Response: {json.dumps(resp.json(), indent=2)}")

if resp.status_code != 201:
    print("   FAILED - Cannot proceed with login test")
    exit(1)

reg_data = resp.json()
print(f"   SUCCESS - User registered with token")

# Step 2: Try login with same credentials
print("\n2. TESTING LOGIN WITH SAME CREDENTIALS...")
login_data = {
    "email": TEST_USER['email'],
    "password": TEST_USER['password']
}
print(f"   Email: {login_data['email']}")
print(f"   Password: {login_data['password']}")

resp = requests.post(f"{BASE_URL}/login/", json=login_data)
print(f"\n   Status: {resp.status_code}")
print(f"   Response: {json.dumps(resp.json(), indent=2)}")

if resp.status_code == 200:
    print("   SUCCESS - Login works!")
else:
    print("   *** LOGIN FAILED ***")
    print("\n   Full error details:")
    try:
        error_data = resp.json()
        for key, value in error_data.items():
            print(f"   - {key}: {value}")
    except:
        print(f"   Response text: {resp.text}")
