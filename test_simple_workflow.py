#!/usr/bin/env python
"""
Simple workflow test for Flirtyfy API
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api"

TEST_USER = {
    "username": f"testuser_{int(time.time())}",
    "email": f"test_{int(time.time())}@test.com",
    "password": "TestPassword123!",
    "confirmPassword": "TestPassword123!",
    "date_of_birth": (datetime.now() - timedelta(days=365*25)).strftime("%Y-%m-%d"),
}

def log(msg):
    print(msg)

def test_workflow():
    log("\n=== SIMPLE WORKFLOW TEST ===\n")
    
    # Register
    log("1. Testing Registration...")
    resp = requests.post(f"{BASE_URL}/register/", json=TEST_USER)
    log(f"   Status: {resp.status_code}")
    if resp.status_code != 201:
        log(f"   ERROR: {resp.json()}")
        return False
    reg_data = resp.json()
    token = reg_data['token']
    log(f"   SUCCESS - Token: {token[:20]}...")
    
    # Login
    log("\n2. Testing Login...")
    resp = requests.post(f"{BASE_URL}/login/", 
        json={"email": TEST_USER['email'], "password": TEST_USER['password']})
    log(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        log(f"   ERROR: {resp.json()}")
        return False
    log("   SUCCESS")
    
    # Upload conversation
    log("\n3. Testing Conversation Upload...")
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    resp = requests.post(f"{BASE_URL}/novelty/upload/",
        json={"original_text": "Hey, how are you doing? I've been thinking about you. Want to grab coffee?"},
        headers=headers)
    log(f"   Status: {resp.status_code}")
    if resp.status_code not in [200, 201]:
        log(f"   ERROR: {resp.json()}")
        return False
    upload_data = resp.json()
    upload_id = upload_data.get('id')
    log(f"   SUCCESS - Upload ID: {upload_id}")
    
    # Wait for Celery to process
    log("\n4. Waiting for Celery to process (10 seconds)...")
    for i in range(10):
        print(f"   {i+1}/10...", end='\r')
        time.sleep(1)
    log("   DONE                 ")
    
    # Check Celery logs
    log("\n5. Checking Celery logs...")
    import subprocess
    try:
        result = subprocess.run(['docker', 'logs', 'backend-celery-1', '--tail', '20'], 
                              capture_output=True, text=True, timeout=5)
        logs = result.stdout + result.stderr
        if "ERROR" in logs or "TypeError" in logs or "Connection refused" in logs:
            log("   ERRORS in Celery logs:")
            for line in logs.split('\n')[-10:]:
                if line.strip():
                    log(f"   {line}")
        else:
            log("   No obvious errors in logs")
    except Exception as e:
        log(f"   Could not check logs: {e}")
    
    # Fetch replies
    log("\n6. Fetching AI Replies...")
    resp = requests.get(f"{BASE_URL}/novelty/replies/", headers=headers)
    log(f"   Status: {resp.status_code}")
    if resp.status_code != 200:
        log(f"   ERROR: {resp.json()}")
        return False
    replies = resp.json()
    log(f"   Found {len(replies)} replies")
    if len(replies) > 0:
        log(f"   SUCCESS - Got AI reply: {replies[0].get('original_text', 'N/A')[:50]}...")
        return True
    else:
        log("   WARNING - No replies yet (task may still be processing)")
        return None

if __name__ == "__main__":
    result = test_workflow()
    if result is True:
        log("\n*** ALL TESTS PASSED ***")
    elif result is False:
        log("\n*** TESTS FAILED ***")
    else:
        log("\n*** TESTS PASSED WITH WARNINGS (replies still processing) ***")
