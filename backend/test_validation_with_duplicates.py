"""
Test validation with duplicate responses to trigger rephrase loop
This should take 30-40 seconds due to uniqueness checks and rephrasing
"""
import os
import django
import time
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.services.ai_generation import generate_reply
from accounts.services.response_validator import ResponseValidator
from accounts.services.novelty import normalize_text, fingerprint_text
from accounts.services.similarity import get_embedding

print("=" * 80)
print("VALIDATION TEST WITH DUPLICATE DETECTION - REPHRASE LOOP TIMING")
print("=" * 80)

# Clean database
print("\n🧹 Cleaning database...")
AIReply.objects.all().delete()
ConversationUpload.objects.all().delete()

# Create test user
test_user, _ = User.objects.get_or_create(
    username='timing_test_user',
    defaults={'email': 'timing@test.com'}
)
print(f"✅ Created test user: {test_user.username}")

# Create test conversation
test_text = "No thanks. I ONLY WANT ONE woman."
print(f"\n📝 Test conversation: {test_text}")

upload = ConversationUpload.objects.create(
    user=test_user,
    original_text=test_text
)
print(f"✅ Created upload: {upload.id}")

# Generate FIRST response
print(f"\n🚀 Generating FIRST response (should be unique)...")
start_time = datetime.now()
response1 = generate_reply(test_text, user=test_user, attempt_number=1)
first_response_time = (datetime.now() - start_time).total_seconds()
print(f"⏱️  First response generated in {first_response_time:.1f} seconds")
print(f"📝 Response 1: {response1}")
print(f"   Length: {len(response1)} chars")

# Store FIRST response in database to simulate previous reply
norm1 = normalize_text(response1)
fp1 = fingerprint_text(response1)
emb1 = get_embedding(response1)

reply1 = AIReply.objects.create(
    user=test_user,
    upload=upload,
    original_text=response1,
    normalized_text=norm1,
    fingerprint=fp1,
    embedding=emb1,
    summary=response1[:50],
    intent='test',
    expires_at=datetime.now() + timedelta(days=45),
    status='complete'
)
print(f"✅ Stored response 1 in DB (will trigger duplicate detection)")

# Generate SECOND response (should trigger rephrase loop)
print(f"\n🚀 Generating SECOND response (should trigger rephrase loop)...")
print(f"   Testing against first response in database...")
start_time = datetime.now()
response2 = generate_reply(test_text, user=test_user, attempt_number=2)
second_response_time = (datetime.now() - start_time).total_seconds()
print(f"⏱️  Second response generated in {second_response_time:.1f} seconds")
print(f"📝 Response 2: {response2}")
print(f"   Length: {len(response2)} chars")

# Store SECOND response
norm2 = normalize_text(response2)
fp2 = fingerprint_text(response2)
emb2 = get_embedding(response2)

reply2 = AIReply.objects.create(
    user=test_user,
    upload=upload,
    original_text=response2,
    normalized_text=norm2,
    fingerprint=fp2,
    embedding=emb2,
    summary=response2[:50],
    intent='test',
    expires_at=datetime.now() + timedelta(days=45),
    status='complete'
)
print(f"✅ Stored response 2 in DB")

# Generate THIRD response (should also trigger rephrase loop)
print(f"\n🚀 Generating THIRD response (against 2 previous responses)...")
start_time = datetime.now()
response3 = generate_reply(test_text, user=test_user, attempt_number=3)
third_response_time = (datetime.now() - start_time).total_seconds()
print(f"⏱️  Third response generated in {third_response_time:.1f} seconds")
print(f"📝 Response 3: {response3}")
print(f"   Length: {len(response3)} chars")

# Generate FOURTH response (should have most rephrase attempts)
print(f"\n🚀 Generating FOURTH response (against 3 previous responses)...")
start_time = datetime.now()
response4 = generate_reply(test_text, user=test_user, attempt_number=4)
fourth_response_time = (datetime.now() - start_time).total_seconds()
print(f"⏱️  Fourth response generated in {fourth_response_time:.1f} seconds")
print(f"📝 Response 4: {response4}")
print(f"   Length: {len(response4)} chars")

# Validate FOURTH response with validator
print(f"\n🔍 Validating FOURTH response against all 7 rules:")
validator = ResponseValidator(test_user)
is_valid, final_response, logs = validator.validate_and_refine(response4)

print("\n".join(logs))

print(f"\n📝 FINAL APPROVED RESPONSE:")
print(f"  Original length: {len(response4)} chars")
print(f"  Original: {response4}")
print(f"\n  Final length: {len(final_response)} chars")
print(f"  Final: {final_response}")

# Print summary
print(f"\n{'=' * 80}")
print("📊 TIMING SUMMARY:")
print(f"{'=' * 80}")
print(f"  Response 1 (no db entries):  {first_response_time:.1f}s")
print(f"  Response 2 (1 db entry):     {second_response_time:.1f}s")
print(f"  Response 3 (2 db entries):   {third_response_time:.1f}s")
print(f"  Response 4 (3 db entries):   {fourth_response_time:.1f}s")
print(f"\n  Total time for all 4:        {first_response_time + second_response_time + third_response_time + fourth_response_time:.1f}s")
print(f"  Average per response:        {(first_response_time + second_response_time + third_response_time + fourth_response_time)/4:.1f}s")

print(f"\n✅ EXPECTED: 30-40 seconds for responses with high uniqueness checking")
if fourth_response_time > 15:
    print(f"✅ ACTUAL: {fourth_response_time:.1f}s - Good! Rephrase loop is active")
else:
    print(f"⚠️  ACTUAL: {fourth_response_time:.1f}s - Fast (low DB entries or cache hit)")

# Check if responses are different
print(f"\n{'=' * 80}")
print("📊 RESPONSE UNIQUENESS CHECK:")
print(f"{'=' * 80}")
responses = [response1, response2, response3, response4]
for i, resp in enumerate(responses, 1):
    print(f"\nResponse {i} ({len(resp)} chars):")
    print(f"  {resp}")

# Check similarity between responses
from difflib import SequenceMatcher
print(f"\n📊 PAIRWISE SIMILARITY:")
for i in range(len(responses)):
    for j in range(i+1, len(responses)):
        sim = SequenceMatcher(None, responses[i], responses[j]).ratio()
        print(f"  Response {i+1} vs {j+1}: {sim:.1%} similar")

print(f"\n✅ TEST COMPLETE")
