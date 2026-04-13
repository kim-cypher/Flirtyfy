#!/usr/bin/env python
"""
Test frontend login flow - exactly as the UI does it
"""

import requests
import json
from datetime import datetime, timedelta

# This is what the frontend apiClient.js uses
API_BASE_URL = "http://localhost:8000/api"

print("=== FRONTEND LOGIN FLOW TEST ===\n")

# Create test user
TEST_USER = {
    "username": "frontend_test_user",
    "email": "frontend_test_user@test.com",
    "password": "TestPassword123!",
    "confirmPassword": "TestPassword123!",
    "date_of_birth": (datetime.now() - timedelta(days=365*25)).strftime("%Y-%m-%d"),
}

print(f"API Base URL: {API_BASE_URL}\n")

# Step 1: Register
print("1. REGISTER (mimicking Register.js)")
print(f"   URL: {API_BASE_URL}/register/")
print(f"   Method: POST")
print(f"   Body: {json.dumps(TEST_USER, indent=6)}")

resp = requests.post(f"{API_BASE_URL}/register/", json=TEST_USER)
print(f"   Status: {resp.status_code}")

if resp.status_code != 201:
    print(f"   ERROR: {json.dumps(resp.json(), indent=2)}")
    exit(1)

reg_data = resp.json()
token_from_register = reg_data.get('token')
print(f"   Token received: {token_from_register[:20]}...")
print("   SUCCESS\n")

# Step 2: Login (exactly as Login.js does it)
print("2. LOGIN (mimicking Login.js)")
login_payload = {
    "email": TEST_USER['email'],
    "password": TEST_USER['password']
}
print(f"   URL: {API_BASE_URL}/login/")
print(f"   Method: POST")
print(f"   Headers:")
print(f"     Content-Type: application/json")
print(f"   Body: {json.dumps(login_payload, indent=6)}")

resp = requests.post(f"{API_BASE_URL}/login/", json=login_payload)
print(f"\n   Status: {resp.status_code}")
print(f"   Response Headers: {dict(resp.headers)}")
print(f"   Response Body:")
print(json.dumps(resp.json(), indent=4))

if resp.status_code == 200:
    login_data = resp.json()
    token_from_login = login_data.get('token')
    print(f"\n   SUCCESS!")
    print(f"   Token: {token_from_login[:20]}...")
    print(f"   Tokens match? {token_from_register == token_from_login}")
else:
    print(f"\n   FAILED with status {resp.status_code}")
    error_resp = resp.json()
    print(f"   Full error:")
    for key, val in error_resp.items():
        print(f"     {key}: {val}")

# Step 3: Use token to access protected endpoint (like frontend would)
print("\n3. TEST TOKEN - Access protected endpoint (mimicking Chat.js)")
if resp.status_code == 200:
    token = login_data.get('token')
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    print(f"   URL: {API_BASE_URL}/novelty/replies/")
    print(f"   Method: GET")
    print(f"   Headers:")
    print(f"     Authorization: Token {token[:20]}...")
    print(f"     Content-Type: application/json")
    
    resp = requests.get(f"{API_BASE_URL}/novelty/replies/", headers=headers)
    print(f"\n   Status: {resp.status_code}")
    
    if resp.status_code == 200:
        print("   SUCCESS - Token is valid and works!")
    else:
        print(f"   ERROR - Token not working: {resp.json()}")
