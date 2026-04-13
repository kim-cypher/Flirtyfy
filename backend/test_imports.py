#!/usr/bin/env python
"""Test if all modules import correctly"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, r'c:\Users\kiman\Projects\Flirtyfy\backend')

print("Testing imports...")
print("-" * 50)

try:
    print("✓ Importing openai_service...")
    from accounts.openai_service import OpenAIService
    print("  SUCCESS: openai_service imported")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

try:
    print("✓ Importing serializers...")
    from accounts.serializers import RegisterSerializer, LoginSerializer
    print("  SUCCESS: serializers imported")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

try:
    print("✓ Importing novelty_models...")
    from accounts.novelty_models import ConversationUpload, AIReply
    print("  SUCCESS: novelty_models imported")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

print("-" * 50)
print("✅ All imports successful!")
