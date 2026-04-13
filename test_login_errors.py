#!/usr/bin/env python
"""
Test login with wrong credentials to see error message
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

print("=== TESTING LOGIN WITH WRONG CREDENTIALS ===\n")

# Try login with non-existent email
print("1. Login with non-existent email")
resp = requests.post(f"{BASE_URL}/login/", json={
    "email": "nonexistent@test.com",
    "password": "SomePassword123!"
})
print(f"   Status: {resp.status_code}")
print(f"   Response: {json.dumps(resp.json(), indent=2)}")

print("\n2. Login with wrong password")
resp = requests.post(f"{BASE_URL}/login/", json={
    "email": "frontend_test_user@test.com",  # This user exists
    "password": "WrongPassword123!"
})
print(f"   Status: {resp.status_code}")
print(f"   Response: {json.dumps(resp.json(), indent=2)}")

print("\n3. Login with missing email")
resp = requests.post(f"{BASE_URL}/login/", json={
    "password": "TestPassword123!"
})
print(f"   Status: {resp.status_code}")
print(f"   Response: {json.dumps(resp.json(), indent=2)}")

print("\n4. Login with missing password")
resp = requests.post(f"{BASE_URL}/login/", json={
    "email": "frontend_test_user@test.com"
})
print(f"   Status: {resp.status_code}")
print(f"   Response: {json.dumps(resp.json(), indent=2)}")
