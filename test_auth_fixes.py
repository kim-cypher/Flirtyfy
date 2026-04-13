#!/usr/bin/env python
"""Test login and registration fixes"""
import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"
TEST_EMAIL = f"testuser_{date.today().isoformat()}@test.com"
TEST_PASSWORD = "TestPassword123!"
TEST_DOB = (date.today() - timedelta(days=365*25)).isoformat()  # 25 years old

print("=" * 60)
print("Testing Login and Registration Fixes")
print("=" * 60)

# Test 1: Register a new user
print("\n[TEST 1] Registering new user...")
print(f"Email: {TEST_EMAIL}")
print(f"Password: {TEST_PASSWORD}")
print(f"Date of Birth: {TEST_DOB}")

register_data = {
    "email": TEST_EMAIL,
    "username": TEST_EMAIL.split("@")[0],
    "password": TEST_PASSWORD,
    "confirmPassword": TEST_PASSWORD,
    "date_of_birth": TEST_DOB
}

response = requests.post(f"{BASE_URL}/api/register/", json=register_data)
print(f"\nResponse status: {response.status_code}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

if response.status_code in [200, 201]:
    print("✓ Registration successful!")
    token = response.json().get("token")
else:
    print("✗ Registration failed!")
    exit(1)

# Test 2: Try to register the same email again (should fail)
print("\n[TEST 2] Attempting to register same email again (should fail)...")
response = requests.post(f"{BASE_URL}/api/register/", json=register_data)
print(f"Response status: {response.status_code}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

if response.status_code != 200 and response.status_code != 201:
    print("✓ Correctly rejected duplicate email!")
else:
    print("✗ Should have rejected duplicate email!")

# Test 3: Login with the new user
print("\n[TEST 3] Logging in with new user...")
login_data = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
}

response = requests.post(f"{BASE_URL}/api/login/", json=login_data)
print(f"Response status: {response.status_code}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    print("✓ Login successful!")
    login_token = response.json().get("token")
    print(f"Token received: {login_token[:20]}...")
else:
    print("✗ Login failed!")
    exit(1)

# Test 4: Verify tokens match
print("\n[TEST 4] Verifying tokens match...")
if token == login_token:
    print("✓ Registration and login tokens match!")
else:
    print("✗ Tokens don't match")

print("\n" + "=" * 60)
print("All tests completed successfully!")
print("=" * 60)
