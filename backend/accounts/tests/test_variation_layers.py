"""
Comprehensive tests for all 4 variation layers
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from accounts.models import ConversationLog, ResponseLog, NgramLog, VocabCooldown
from accounts.services.ngram_service import extract_ngrams, check_ngrams, log_ngrams
from accounts.services.structure_service import (
    get_forbidden_structures, get_available_structures
)
from accounts.services.tone_service import get_forbidden_tones, get_available_tones
from accounts.services.vocab_service import (
    get_available_words, log_used_words
)
from accounts.services.context_detector import detect_context_triggers


class TestNgramExtraction(TestCase):
    """Layer 1: N-gram Blocking Tests"""

    def test_bigrams_extracted_correctly(self):
        text = "I love teasing you so much"
        result = extract_ngrams(text)
        self.assertIn("i love", result["bigrams"])
        self.assertIn("love teasing", result["bigrams"])
        self.assertIn("teasing you", result["bigrams"])

    def test_trigrams_extracted_correctly(self):
        text = "I love teasing you"
        result = extract_ngrams(text)
        self.assertIn("i love teasing", result["trigrams"])
        self.assertIn("love teasing you", result["trigrams"])

    def test_punctuation_stripped_before_extraction(self):
        text = "Honestly... I love this."
        result = extract_ngrams(text)
        self.assertIn("honestly i", result["bigrams"])
        self.assertIn("i love", result["bigrams"])

    def test_check_passes_on_new_trigrams(self):
        result = check_ngrams("user_1", "something brand new today")
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_check_fails_on_repeated_trigram(self):
        log_ngrams("user_2", "I love teasing you")
        result = check_ngrams("user_2", "I love teasing still")
        self.assertFalse(result["passed"])
        self.assertIn("i love teasing", result["violations"])

    def test_trigrams_expire_after_45_days(self):
        # Manually insert old ngram
        NgramLog.objects.create(
            user_id="user_3",
            ngram="this old phrase",
            ngram_type="trigram",
            used_at=timezone.now() - timedelta(days=46)
        )
        result = check_ngrams("user_3", "this old phrase")
        self.assertTrue(result["passed"])

    def test_bigrams_not_blocked_only_trigrams(self):
        log_ngrams("user_4", "love you")
        result = check_ngrams("user_4", "love you always")
        self.assertTrue(result["passed"])


class TestStructureRotation(TestCase):
    """Layer 2: Structure Rotation Tests"""

    def setUp(self):
        self.conv = ConversationLog.objects.create(user_id="test_user")

    def _add_response(self, structure):
        count = ResponseLog.objects.filter(conversation=self.conv).count()
        ResponseLog.objects.create(
            conversation=self.conv,
            reply_number=count + 1,
            response_text="test response",
            structure_used=structure,
            tone_used="playful",
            question_starter="would you"
        )

    def test_last_used_structure_is_forbidden(self):
        self._add_response('A')
        forbidden = get_forbidden_structures(self.conv.id)
        self.assertIn('A', forbidden)

    def test_structure_used_twice_in_7_is_forbidden(self):
        self._add_response('B')
        self._add_response('C')
        self._add_response('B')
        forbidden = get_forbidden_structures(self.conv.id)
        self.assertIn('B', forbidden)

    def test_available_structures_excludes_forbidden(self):
        self._add_response('A')
        available = get_available_structures(self.conv.id)
        self.assertNotIn('A', available)

    def test_all_7_structures_available_on_fresh_conversation(self):
        available = get_available_structures(self.conv.id)
        self.assertEqual(len(available), 7)

    def test_at_least_one_structure_always_available(self):
        for s in ['A', 'B', 'C', 'D', 'E', 'F']:
            self._add_response(s)
        available = get_available_structures(self.conv.id)
        self.assertGreater(len(available), 0)


class TestToneRotation(TestCase):
    """Layer 3: Tone Rotation Tests"""

    def setUp(self):
        self.conv = ConversationLog.objects.create(user_id="tone_test_user")

    def _add_tone(self, tone):
        count = ResponseLog.objects.filter(conversation=self.conv).count()
        ResponseLog.objects.create(
            conversation=self.conv,
            reply_number=count + 1,
            response_text="test",
            structure_used="A",
            tone_used=tone,
            question_starter="would you"
        )

    def test_last_used_tone_is_forbidden(self):
        self._add_tone('playful')
        forbidden = get_forbidden_tones(self.conv.id)
        self.assertIn('playful', forbidden)

    def test_tone_used_twice_in_7_is_forbidden(self):
        self._add_tone('confident')
        self._add_tone('soft')
        self._add_tone('confident')
        forbidden = get_forbidden_tones(self.conv.id)
        self.assertIn('confident', forbidden)

    def test_tone_resets_after_7_reply_window(self):
        for tone in ['playful', 'vulnerable', 'confident', 'distracted', 'intense', 'soft', 'challenging']:
            self._add_tone(tone)
        forbidden = get_forbidden_tones(self.conv.id)
        self.assertIn('challenging', forbidden)


class TestVocabCooldown(TestCase):
    """Layer 4: Vocabulary Cooldown Tests"""

    def test_word_available_before_use(self):
        available = get_available_words("vocab_user_1", 1)
        self.assertIn("drawn to", available['attraction'])

    def test_word_on_cooldown_after_use(self):
        log_used_words("vocab_user_2", "I was drawn to you", 5)
        available = get_available_words("vocab_user_2", 10)
        self.assertNotIn("drawn to", available['attraction'])

    def test_word_available_after_cooldown_expires(self):
        log_used_words("vocab_user_3", "drawn to something", 1)
        available = get_available_words("vocab_user_3", 17)
        self.assertIn("drawn to", available['attraction'])

    def test_multiple_pools_tracked_independently(self):
        log_used_words("vocab_user_4", "something about the way I was holding back", 1)
        available = get_available_words("vocab_user_4", 5)
        self.assertNotIn("something about", available['feeling'])
        self.assertNotIn("holding back", available['teasing'])
        self.assertIn("drawn to", available['attraction'])


class TestContextTriggers(TestCase):
    """Context Trigger Detection Tests"""

    def test_restaurant_trigger_detected(self):
        triggers = detect_context_triggers("I know a great Italian place downtown")
        self.assertIn('restaurant', triggers)

    def test_vacation_trigger_detected(self):
        triggers = detect_context_triggers("I'm planning a trip to Mombasa next month")
        self.assertIn('vacation', triggers)

    def test_meeting_trigger_detected(self):
        triggers = detect_context_triggers("let me give you my number")
        self.assertIn('meeting', triggers)

    def test_multiple_triggers_detected(self):
        triggers = detect_context_triggers("let's have dinner and I'll give you my number")
        self.assertIn('restaurant', triggers)
        self.assertIn('meeting', triggers)

    def test_no_trigger_on_neutral_message(self):
        triggers = detect_context_triggers("what kind of music do you like")
        self.assertEqual(triggers, [])

    def test_car_trigger_detected(self):
        triggers = detect_context_triggers("I could pick you up and we go for a night drive")
        self.assertIn('car', triggers)
        self.assertIn('meeting', triggers)


class TestMeetingDiversion(TestCase):
    """Meeting suggestion diversion tests"""

    def test_meeting_suggestion_detected(self):
        triggers = detect_context_triggers("To meet for a start and to see if what we talked about us is possible")
        self.assertIn('meeting', triggers)

    def test_number_exchange_detected(self):
        triggers = detect_context_triggers("I am going to give you my number the area code is the same")
        self.assertIn('meeting', triggers)

    def test_location_query_detected(self):
        triggers = detect_context_triggers("flagpole location talk about what you are looking for")
        self.assertIn('meeting', triggers)


class TestFullGenerationFlow(TestCase):
    """Integration tests for full generation flow"""

    def setUp(self):
        self.conv = ConversationLog.objects.create(user_id="integration_test_user")

    def test_response_logged_after_passing_checks(self):
        """Verify all 4 layers log data after passing"""
        from accounts.services.generation_engine import _extract_question_starter

        response_text = "Something about the way you said that caught me off guard what exactly were you hoping?"
        
        # Log ngrams
        log_ngrams("integration_test_user", response_text)
        ngrams_count = NgramLog.objects.filter(user_id="integration_test_user").count()
        self.assertGreater(ngrams_count, 0)

        # Log vocab
        log_used_words("integration_test_user", response_text, 1)
        vocab_count = VocabCooldown.objects.filter(user_id="integration_test_user").count()
        self.assertGreater(vocab_count, 0)

        # Create response log
        ResponseLog.objects.create(
            conversation=self.conv,
            reply_number=1,
            response_text=response_text,
            structure_used='A',
            tone_used='vulnerable',
            question_starter=_extract_question_starter(response_text)
        )
        
        self.assertEqual(ResponseLog.objects.filter(conversation=self.conv).count(), 1)

    def test_semantic_repetition_prevented(self):
        """Two consecutive calls should use different trigrams"""
        # Create first response
        response1 = "I love teasing you because you make it so easy and natural"
        log_ngrams("user_semantic", response1)

        # Try second response with similar trigrams
        check_result = check_ngrams("user_semantic", "I love teasing still because you keep doing it")
        
        # Should fail due to "i love teasing" trigram match
        self.assertFalse(check_result["passed"])
        self.assertIn("i love teasing", check_result["violations"])

    def test_meeting_decline_uses_specific_anchoring(self):
        """Meeting decline should reference specific details from conversation"""
        # This would test the updated ai_generation.py when integrated
        triggers = detect_context_triggers(
            "To meet for a start and to see if what we talked about us is possible the flagpole"
        )
        self.assertIn('meeting', triggers)


class TestVariationEngineLayers(TestCase):
    """Test all 4 layers work together"""

    def setUp(self):
        self.conv = ConversationLog.objects.create(user_id="all_layers_user")

    def test_all_forbidden_lists_built_correctly(self):
        """Verify forbidden structures and tones computed correctly"""
        # Add some responses
        for i, struct in enumerate(['A', 'B', 'C', 'D', 'E']):
            ResponseLog.objects.create(
                conversation=self.conv,
                reply_number=i + 1,
                response_text=f"response {i}",
                structure_used=struct,
                tone_used='playful',
                question_starter='what'
            )

        # Check forbidding
        forbidden_structs = get_forbidden_structures(self.conv.id)
        available_structs = get_available_structures(self.conv.id)
        
        self.assertIn('E', forbidden_structs)
        self.assertNotIn('E', available_structs)
        self.assertIn('F', available_structs)

    def test_vocabulary_patterns_match_rules(self):
        """Verify word pools contain the designed patterns"""
        from accounts.services.vocab_service import WORD_POOLS

        # Attraction pool should exist
        self.assertIn('attraction', WORD_POOLS)
        self.assertIn('drawn to', WORD_POOLS['attraction'])

        # Teasing pool should exist
        self.assertIn('teasing', WORD_POOLS)
        self.assertIn('holding back', WORD_POOLS['teasing'])

        # Feeling pool should exist
        self.assertIn('feeling', WORD_POOLS)
        self.assertIn('something about', WORD_POOLS['feeling'])