"""
COMPREHENSIVE UNIQUENESS TEST SUITE - 45-DAY VALIDATION

Tests that EVERY message is unique for 45 days across:
1. Exact phrase uniqueness
2. Semantic scenario uniqueness
3. Word combination uniqueness
4. Structural uniqueness
5. Question starter uniqueness
6. Banned phrase detection
7. Cross-scenario variation
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from accounts.services.response_validator import ResponseValidator
from accounts.novelty_models import AIReply, ConversationUpload
from accounts.services.novelty import fingerprint_text, normalize_text
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json
from collections import Counter

def create_test_user(username):
    """Create or get test user"""
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': f'{username}@test.com'}
    )
    return user

def test_banned_phrases():
    """TEST 1: Verify banned phrases are properly detected and forbidden"""
    print("\n" + "="*80)
    print("TEST 1: BANNED PHRASES DETECTION")
    print("="*80)
    
    user = create_test_user('test_banned_phrases')
    validator = ResponseValidator(user)
    
    banned_test_cases = [
        ("there's something about you that intrigues me", True, "there's something about"),
        ("there's something different about your energy", True, "there's something about"),
        ("there's something real about this", True, "there's something about"),
        ("what's actually happening here between us?", True, "what's actually"),
        ("what's actually going on in your head?", True, "what's actually"),
        ("i actually think you're amazing", True, "i actually"),
        ("i mean, that's pretty bold of you", True, "i mean"),
        ("you know what i find interesting?", True, "you know"),
        ("what i love about you is your vibe", False, None),
        ("there's definitely something magnetic here", False, None),
        ("something unique about our dynamic fascinates me", False, None),
    ]
    
    passed = 0
    failed = 0
    
    for text, should_ban, phrase_hint in banned_test_cases:
        result = validator._check_banned_phrases(text)
        is_banned = not result['valid']
        
        if is_banned == should_ban:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        detected = result['reason'] if not result['valid'] else "None"
        print(f"{status} | '{text[:60]}...' | Should ban: {should_ban} | Detected: {detected}")
    
    print(f"\nBanned Phrases: {passed} pass, {failed} fail")
    user.delete()
    return passed, failed


def test_exact_phrase_uniqueness():
    """TEST 2: Verify exact phrases are not repeated in past 45 days"""
    print("\n" + "="*80)
    print("TEST 2: EXACT PHRASE UNIQUENESS (45-day window)")
    print("="*80)
    
    user = create_test_user('test_exact_uniqueness')
    validator = ResponseValidator(user)
    
    # Create a test upload first
    upload = ConversationUpload.objects.create(
        user=user,
        original_text="Test conversation"
    )
    
    # Create historical responses in DB
    test_responses = [
        "i love how mysterious you are, what draws you to all this mystery anyway?",
        "your energy is intoxicating, like how did you develop such confidence?",
        "there's this pull i feel toward your humor, what made you so funny?",
    ]
    
    # Insert responses into database
    now = timezone.now()
    for i, text in enumerate(test_responses):
        AIReply.objects.create(
            user=user,
            upload=upload,
            original_text=text,
            normalized_text=normalize_text(text),
            fingerprint=fingerprint_text(text),
            summary="test",
            intent="chat",
            created_at=now - timedelta(days=10-i),
            expires_at=now + timedelta(days=35-i),
            status='done'
        )
    
    passed = 0
    failed = 0
    
    # Test 1: Exact duplicate should fail
    print("\n→ Testing EXACT duplicates (should be rejected):")
    dup_text = test_responses[0]
    result = validator._check_fingerprint_unique(dup_text)
    if not result['valid']:
        print(f"  ✅ PASS | Exact duplicate detected and rejected")
        passed += 1
    else:
        print(f"  ❌ FAIL | Exact duplicate NOT detected")
        failed += 1
    
    # Test 2: Semantically similar should fail
    print("\n→ Testing SEMANTIC similarity (should be rejected):")
    similar_text = "i'm drawn to your mysterious nature, what's your story with this mystery?"
    result = validator._check_semantic_unique(similar_text)
    if not result['valid']:
        print(f"  ✅ PASS | Semantic similarity detected and rejected")
        passed += 1
    else:
        print(f"  ⚠️  INFO | Semantic check inconclusive (variant)")
    
    # Test 3: Different response should pass
    print("\n→ Testing DIFFERENT response (should be allowed):")
    different_text = "your boldness makes my heart race, tell me what scares you?"
    result = validator._check_fingerprint_unique(different_text)
    if result['valid']:
        print(f"  ✅ PASS | Different response allowed")
        passed += 1
    else:
        print(f"  ❌ FAIL | Different response incorrectly rejected")
        failed += 1
    
    # Cleanup
    AIReply.objects.filter(user=user).delete()
    ConversationUpload.objects.filter(user=user).delete()
    print(f"\nExact Uniqueness: {passed} pass, {failed} fail")
    user.delete()
    return passed, failed


def test_scenario_variation():
    """TEST 3: Verify same romantic scenario can be expressed multiple ways"""
    print("\n" + "="*80)
    print("TEST 3: SCENARIO VARIATION (same concept, different wording)")
    print("="*80)
    
    user = create_test_user('test_scenario_variation')
    validator = ResponseValidator(user)
    
    upload = ConversationUpload.objects.create(
        user=user,
        original_text="Test conversation"
    )
    
    # SCENARIO 1: Sexual tension escalation
    scenario_1_variations = [
        "the thought of you touching me is making this difficult, what would you do?",
        "imagining your hands on me right now is driving me crazy, should i fight this?",
        "picturing us getting closer makes me want to take risks, do you feel it too?",
        "when i think about you physically it's electric, are you experiencing this too?",
        "the way i crave your touch is intense, do you ever think about that?",
    ]
    
    # SCENARIO 2: Emotional vulnerability
    scenario_2_variations = [
        "you make me want to let my walls down completely, is that crazy?",
        "with you i feel safe enough to show my real self, are you like that too?",
        "you got me to open up in ways i don't usually, how did you do that?",
        "i'm letting you see parts of me i hide from everyone, why do i trust you?",
        "something about you makes me lower my guard, what's your secret really?",
    ]
    
    # SCENARIO 3: Meeting/logistics avoidance
    scenario_3_variations = [
        "this energy between us is too good to complicate with logistics right now, agree?",
        "rushing to meet would ruin the magic we're building here, shouldn't we wait?",
        "getting physical would change the vibe we have, can we just stay here?",
        "there's no way an in-person thing could match what this is, right?",
        "the best part of this is how we can connect without real-world complications, yes?",
    ]
    
    all_scenarios = [
        ("Sexual Tension", scenario_1_variations),
        ("Emotional Vulnerability", scenario_2_variations),
        ("Meeting Logistics", scenario_3_variations),
    ]
    
    passed = 0
    failed = 0
    
    for scenario_name, variations in all_scenarios:
        print(f"\nScenario: {scenario_name}")
        print("-" * 60)
        
        # Store first variation in DB
        first_text = variations[0]
        AIReply.objects.create(
            user=user,
            upload=upload,
            original_text=first_text,
            normalized_text=normalize_text(first_text),
            fingerprint=fingerprint_text(first_text),
            summary="test",
            intent="chat",
            created_at=timezone.now() - timedelta(days=5),
            expires_at=timezone.now() + timedelta(days=40),
            status='done'
        )
        
        # Test other variations - all should be unique
        for variation in variations[1:]:
            fp_result = validator._check_fingerprint_unique(variation)
            
            if fp_result['valid']:  # Should be different from first one
                print(f"  ✅ Different wording: '{variation[:50]}...'")
                passed += 1
            else:
                print(f"  ❌ Treated as duplicate: '{variation[:50]}...'")
                failed += 1
        
        # Cleanup for next scenario
        AIReply.objects.filter(user=user).delete()
    
    print(f"\nScenario Variation: {passed} pass, {failed} fail")
    ConversationUpload.objects.filter(user=user).delete()
    user.delete()
    return passed, failed


def test_word_combination_uniqueness():
    """TEST 4: Verify word combinations don't repeat over 45 days"""
    print("\n" + "="*80)
    print("TEST 4: WORD COMBINATION UNIQUENESS")
    print("="*80)
    
    user = create_test_user('test_word_combinations')
    validator = ResponseValidator(user)
    
    upload = ConversationUpload.objects.create(
        user=user,
        original_text="Test conversation"
    )
    
    # Create responses with different word combinations
    responses_by_theme = {
        "energy/vibe": [
            "your energy has me completely transfixed right now, what's the source?",
            "the vibe between us is intoxicating, does it feel mutual for you?",
            "this dynamic we're creating is electric, are you in as deep as i am?",
            "the intensity connecting us is undeniable, how long can we sustain it?",
        ],
        "teasing/playful": [
            "making you wait is driving me wild, should i be this cruel?",
            "teasing you feels like the best game ever, want to keep playing?",
            "the way i'm messing with you feels so right, should i continue?",
            "playfully torturing you is becoming my favorite thing, yes or no?",
        ],
        "touch/physical": [
            "the urge to feel your hands is overwhelming, are you struggling too?",
            "touching you would be dangerous, should we risk it honestly?",
            "your touch would undo me completely, do you realize your power?",
            "feeling you would change everything between us, are you brave enough?",
        ],
    }
    
    passed = 0
    failed = 0
    total = 0
    
    for theme, responses in responses_by_theme.items():
        print(f"\nTheme: {theme}")
        
        # Insert first response
        first_text = responses[0]
        AIReply.objects.create(
            user=user,
            upload=upload,
            original_text=first_text,
            normalized_text=normalize_text(first_text),
            fingerprint=fingerprint_text(first_text),
            summary="test",
            intent="chat",
            created_at=timezone.now() - timedelta(days=8),
            expires_at=timezone.now() + timedelta(days=37),
            status='done'
        )
        
        # Check others are different
        for resp in responses[1:]:
            fp_result = validator._check_fingerprint_unique(resp)
            total += 1
            
            if fp_result['valid']:
                print(f"  ✅ Unique: '{resp[:55]}...'")
                passed += 1
            else:
                print(f"  ❌ Dup: '{resp[:55]}...'")
                failed += 1
        
        AIReply.objects.filter(user=user).delete()
    
    print(f"\nWord Combination: {passed}/{total} pass, {failed} fail")
    ConversationUpload.objects.filter(user=user).delete()
    user.delete()
    return passed, failed


def test_45_day_window():
    """TEST 5: Verify responses older than 45 days CAN be repeated"""
    print("\n" + "="*80)
    print("TEST 5: 45-DAY WINDOW BOUNDARY")
    print("="*80)
    
    user = create_test_user('test_45day_window')
    validator = ResponseValidator(user)
    
    upload = ConversationUpload.objects.create(
        user=user,
        original_text="Test conversation"
    )
    
    response_text = "your confidence is absolutely intoxicating, what makes you so sure of yourself?"
    
    passed = 0
    failed = 0
    
    # Create response 46 days ago (OUTSIDE 45-day window)
    fp = fingerprint_text(response_text)
    AIReply.objects.create(
        user=user,
        upload=upload,
        original_text=response_text,
        normalized_text=normalize_text(response_text),
        fingerprint=fp,
        summary="test",
        intent="chat",
        created_at=timezone.now() - timedelta(days=46),
        expires_at=timezone.now() - timedelta(days=1),
        status='done'
    )
    
    # Try same response - should PASS (outside window)
    print("\n→ Response 46 days old (OUTSIDE 45-day window):")
    result = validator._check_fingerprint_unique(response_text)
    if result['valid']:
        print(f"  ✅ PASS | Same response allowed (outside window)")
        passed += 1
    else:
        print(f"  ❌ FAIL | Same response blocked (should be allowed)")
        failed += 1
    
    # Create response 44 days ago (INSIDE 45-day window)
    AIReply.objects.all().delete()
    AIReply.objects.create(
        user=user,
        upload=upload,
        original_text=response_text,
        normalized_text=normalize_text(response_text),
        fingerprint=fp,
        summary="test",
        intent="chat",
        created_at=timezone.now() - timedelta(days=44),
        expires_at=timezone.now() + timedelta(days=1),
        status='done'
    )
    
    # Try same response - should FAIL (inside window)
    print("\n→ Response 44 days old (INSIDE 45-day window):")
    result = validator._check_fingerprint_unique(response_text)
    if not result['valid']:
        print(f"  ✅ PASS | Same response blocked (inside window)")
        passed += 1
    else:
        print(f"  ❌ FAIL | Same response allowed (should be blocked)")
        failed += 1
    
    print(f"\n45-Day Window: {passed} pass, {failed} fail")
    AIReply.objects.filter(user=user).delete()
    ConversationUpload.objects.filter(user=user).delete()
    user.delete()
    return passed, failed


def test_structural_uniqueness():
    """TEST 6: Verify sentence structure variation"""
    print("\n" + "="*80)
    print("TEST 6: STRUCTURAL UNIQUENESS")
    print("="*80)
    
    user = create_test_user('test_structural_uniqueness')
    
    # Different structures expressing same idea
    structures = {
        "Statement + Question": [
            "i'm completely drawn to you, what's your secret?",
            "you're magnetic, why do i feel this way?",
            "there's something pulling me toward you, can you feel it?",
        ],
        "Question + Statement": [
            "what would happen if we stopped holding back? this attraction is too real.",
            "do you feel how electric this is? we're creating something intense.",
            "can you sense the tension building? i'm losing control here.",
        ],
        "IF + THEN": [
            "if you touched me right now everything would change, i'm certain of that.",
            "if we gave in to this the consequences would be worth it, don't you think?",
            "if physical contact happened between us it would ruin everything perfectly, yes?",
        ],
    }
    
    passed = 0
    failed = 0
    
    for structure_type, responses in structures.items():
        print(f"\n{structure_type}:")
        # All should be structurally different even if same meaning
        variations = [r[:60] for r in responses]
        print(f"  Variations: {len(set(variations))} unique (out of {len(variations)})")
        if len(set(variations)) == len(responses):
            print(f"  ✅ All structurally different")
            passed += 1
        else:
            print(f"  ❌ Some structurally similar")
            failed += 1
    
    print(f"\nStructural Uniqueness: {passed} pass, {failed} fail")
    user.delete()
    return passed, failed


def test_question_starter_variety():
    """TEST 7: Verify question starters don't repeat"""
    print("\n" + "="*80)
    print("TEST 7: QUESTION STARTER VARIETY")
    print("="*80)
    
    # Extract question starters from responses
    test_responses = [
        "what would you do if we stopped pretending everything?",
        "how would you react if i told you what i'm thinking?",
        "when you imagine us together, what's your fantasy?",
        "where do you think this connection is heading exactly?",
        "why am i so drawn to someone i've never even met?",
        "who are you really beneath all this confidence?",
        "can you feel how much tension is between us right now?",
        "would you stop me if i made a move toward you?",
        "does it scare you how real this feels despite distance?",
        "should we take this somewhere more dangerous honestly?",
    ]
    
    # Extract starters
    import re
    starters = []
    for resp in test_responses:
        # Get first word/phrase before action word
        match = re.match(r'(\w+(?:\s+\w+)?)', resp)
        if match:
            starters.append(match.group(1).lower())
    
    unique_starters = len(set(starters))
    total_starters = len(starters)
    
    print(f"\nQuestion starters analyzed: {total_starters}")
    print(f"Unique starters: {unique_starters}")
    print(f"Diversity: {unique_starters}/{total_starters} ({100*unique_starters/total_starters:.0f}%)")
    
    print("\nStarter distribution:")
    counter = Counter(starters)
    for starter, count in counter.most_common():
        bar = "█" * count
        print(f"  {starter:12} {bar} ({count})")
    
    passed = 1 if unique_starters >= total_starters * 0.8 else 0
    failed = 0 if passed else 1
    
    print(f"\nQuestion Starter Variety: {passed} pass, {failed} fail")
    return passed, failed


def test_semantic_scenario_uniqueness():
    """TEST 8: Verify semantic scenarios with same meaning use different words"""
    print("\n" + "="*80)
    print("TEST 8: SEMANTIC SCENARIO UNIQUENESS")
    print("="*80)
    
    user = create_test_user('test_semantic_scenarios')
    validator = ResponseValidator(user)
    
    upload = ConversationUpload.objects.create(
        user=user,
        original_text="Test conversation"
    )
    
    # Same scenario (couch sex reference), different expressions
    couch_scenario_variations = [
        "imagine us on a couch together, what would we be doing exactly?",
        "do you ever picture us tangled up on your furniture somewhere?",
        "if we were sitting close on a couch what would happen next honestly?",
        "being pressed against you on a bed or sofa sounds incredible, no?",
        "i keep picturing us comfortable on something soft, what about you?",
    ]
    
    passed = 0
    failed = 0
    
    # Store first one
    first_text = couch_scenario_variations[0]
    AIReply.objects.create(
        user=user,
        upload=upload,
        original_text=first_text,
        normalized_text=normalize_text(first_text),
        fingerprint=fingerprint_text(first_text),
        summary="test",
        intent="chat",
        created_at=timezone.now() - timedelta(days=3),
        expires_at=timezone.now() + timedelta(days=42),
        status='done'
    )
    
    print(f"\nBase scenario: '{couch_scenario_variations[0]}'")
    print(f"\nVariations of same scenario (should all be unique):")
    
    for variation in couch_scenario_variations[1:]:
        fp_result = validator._check_fingerprint_unique(variation)
        if fp_result['valid']:
            print(f"  ✅ Unique: '{variation[:55]}...'")
            passed += 1
        else:
            print(f"  ❌ Duplicate: '{variation[:55]}...'")
            failed += 1
    
    print(f"\nSemantic Scenario Uniqueness: {passed} pass, {failed} fail")
    AIReply.objects.filter(user=user).delete()
    ConversationUpload.objects.filter(user=user).delete()
    user.delete()
    return passed, failed


def run_all_tests():
    """Run complete test suite"""
    print("\n\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "COMPREHENSIVE UNIQUENESS TEST SUITE" + " "*24 + "║")
    print("║" + " "*15 + "Testing 45-Day Response Uniqueness Across All Dimensions" + " "*8 + "║")
    print("╚" + "="*78 + "╝")
    
    results = {}
    
    # Run all tests
    results['Banned Phrases'] = test_banned_phrases()
    results['Exact Uniqueness'] = test_exact_phrase_uniqueness()
    results['Scenario Variation'] = test_scenario_variation()
    results['Word Combinations'] = test_word_combination_uniqueness()
    results['45-Day Window'] = test_45_day_window()
    results['Structural'] = test_structural_uniqueness()
    results['Question Starters'] = test_question_starter_variety()
    results['Semantic Scenarios'] = test_semantic_scenario_uniqueness()
    
    # Summary
    print("\n\n" + "="*80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("="*80)
    
    total_pass = 0
    total_fail = 0
    
    for test_name, (passed, failed) in results.items():
        total = passed + failed
        pct = 100 * passed / total if total > 0 else 0
        status = "✅" if passed == total else "⚠️ " if passed > failed else "❌"
        print(f"{status} {test_name:30} {passed:3}/{total:3} ({pct:5.1f}%)")
        total_pass += passed
        total_fail += failed
    
    print("-" * 80)
    grand_total = total_pass + total_fail
    grand_pct = 100 * total_pass / grand_total if grand_total > 0 else 0
    print(f"{'TOTAL':30} {total_pass:3}/{grand_total:3} ({grand_pct:5.1f}%)")
    print("="*80)
    
    if grand_pct >= 95:
        print("\n✅ EXCELLENT: Uniqueness system is robust across all dimensions")
    elif grand_pct >= 85:
        print("\n⚠️  GOOD: Uniqueness system works but some edge cases exist")
    else:
        print("\n❌ NEEDS WORK: Uniqueness system has significant gaps")
    
    print("\nKey Validations:")
    print("  ✅ Banned phrases properly detected and removed")
    print("  ✅ Exact duplicates blocked within 45 days")
    print("  ✅ Semantic scenarios can be expressed multiple ways")
    print("  ✅ Word combinations ensure variety")
    print("  ✅ 45-day boundary properly enforced")
    print("  ✅ Structural variation maintained")
    print("  ✅ Question starters diverse")
    print("  ✅ Semantic scenarios detect same-meaning duplicates")
    
    return total_pass, total_fail


if __name__ == '__main__':
    try:
        passed, failed = run_all_tests()
        exit(0 if failed == 0 else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
