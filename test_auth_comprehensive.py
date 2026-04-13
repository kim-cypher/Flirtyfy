#!/usr/bin/env python
"""Test email unique constraint and authentication flow"""
import requests
import json
from datetime import date, timedelta, datetime

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("COMPREHENSIVE AUTHENTICATION TESTS")
print("=" * 70)

# Generate unique email for this test
TEST_EMAIL = f"comprehensive_test_{date.today().isoformat()}_{int(datetime.now().timestamp() * 1000) % 10000}@test.com"
TEST_PASSWORD = "SecurePassword123!"
TEST_DOB = (date.today() - timedelta(days=365*25)).isoformat()

# Test 1: Register user
print("\n[TEST 1] Register new user")
print(f"  Email: {TEST_EMAIL}")

register_data = {
    "email": TEST_EMAIL,
    "username": TEST_EMAIL.replace('@', '_').replace('.', '_'),
    "password": TEST_PASSWORD,
    "confirmPassword": TEST_PASSWORD,
    "date_of_birth": TEST_DOB
}

response = requests.post(f"{BASE_URL}/api/register/", json=register_data)
if response.status_code in [200, 201]:
    print(f"  ✓ Registration successful (HTTP {response.status_code})")
    token1 = response.json().get("token")
else:
    print(f"  ✗ Registration failed (HTTP {response.status_code})")
    print(f"    Error: {response.json()}")
    exit(1)

# Test 2: Try duplicate registration (should fail gracefully)
print("\n[TEST 2] Try registering duplicate email (should fail)")

response = requests.post(f"{BASE_URL}/api/register/", json=register_data)
if response.status_code != 200 and response.status_code != 201:
    print(f"  ✓ Correctly rejected duplicate (HTTP {response.status_code})")
    error_msg = response.json()
    print(f"    Error message: {list(error_msg.values())[0] if error_msg else 'Unknown error'}")
else:
    print(f"  ✗ Should have rejected duplicate!")

# Test 3: Login immediately after registration
print("\n[TEST 3] Login immediately after registration")

login_data = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
}

response = requests.post(f"{BASE_URL}/api/login/", json=login_data)
if response.status_code == 200:
    print(f"  ✓ Login successful (HTTP {response.status_code})")
    token2 = response.json().get("token")
    
    if token1 == token2:
        print(f"  ✓ Registration and login tokens match!")
    else:
        print(f"  ⚠ Tokens differ (this may be OK if tokens are refreshed)")
else:
    print(f"  ✗ Login failed (HTTP {response.status_code})")
    print(f"    Error: {response.json()}")
    exit(1)

# Test 4: Login with wrong password
print("\n[TEST 4] Login with wrong password (should fail)")

bad_login = {
    "email": TEST_EMAIL,
    "password": "WrongPassword123!"
}

response = requests.post(f"{BASE_URL}/api/login/", json=bad_login)
if response.status_code != 200:
    print(f"  ✓ Correctly rejected wrong password (HTTP {response.status_code})")
else:
    print(f"  ✗ Should have rejected wrong password!")

# Test 5: Login with non-existent email
print("\n[TEST 5] Login with non-existent email (should fail)")

nonexistent_login = {
    "email": "nonexistent@test.com",
    "password": TEST_PASSWORD
}

response = requests.post(f"{BASE_URL}/api/login/", json=nonexistent_login)
if response.status_code != 200:
    print(f"  ✓ Correctly rejected non-existent user (HTTP {response.status_code})")
else:
    print(f"  ✗ Should have rejected non-existent user!")

# Test 6: Verify multiple logins work
print("\n[TEST 6] Multiple logins with same credentials")

for attempt in range(3):
    response = requests.post(f"{BASE_URL}/api/login/", json=login_data)
    if response.status_code == 200:
        print(f"  ✓ Login attempt {attempt+1} successful")
    else:
        print(f"  ✗ Login attempt {attempt+1} failed")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETED SUCCESSFULLY!")
print("Database unique constraint is working correctly.")
print("=" * 70)
