"""
Real regression tests for the pure-Python safety/escalation/dedup logic
fixed and built during this session. Unlike the standalone test_*.py scripts
at the repo root (which load modules via importlib file-loading tricks and
have drifted from the live code), these import the live modules directly,
the normal way, and run via:

    python manage.py test accounts

No LLM API calls are made anywhere in this file — only the deterministic
Python logic is covered (safety filter, character-break detection, escalation
clause extraction, n-gram dedup, and button data consistency), since that is
both the highest-value regression surface from this session and the part
that can be tested without cost or flakiness.
"""
from django.test import TestCase

from accounts.services.safety_filter import SafetyFilter
from accounts.services.button_generator import (
    _has_character_break,
    BUTTON_INTENTS,
    _BUTTON_Q_CATS,
)
from accounts.services.intent_detector import (
    extract_meeting_free_substance,
    _scrub_escalation,
    _has_meeting_push,
)
from accounts.services.dedup import find_repeated_ngram, _extract_ngrams


class SafetyFilterTests(TestCase):
    def setUp(self):
        self.filter = SafetyFilter()

    def test_illegal_content_blocked(self):
        is_safe, violation, _ = self.filter.check_safety("let's talk about child porn")
        self.assertFalse(is_safe)
        self.assertEqual(violation, 'illegal_content')

    def test_violence_self_harm_blocked(self):
        is_safe, violation, _ = self.filter.check_safety("I will kill myself tonight")
        self.assertFalse(is_safe)
        self.assertEqual(violation, 'violence_selfharm')

    def test_violence_false_positive_does_not_fire(self):
        # Regression: "I do not do things that can hurt you" used to false-positive
        # before VIOLENCE_PATTERNS required an explicit intent verb.
        is_safe, _, _ = self.filter.check_safety("I do not do things that can hurt you")
        self.assertTrue(is_safe)

    def test_ordinary_flirty_message_is_safe(self):
        is_safe, _, _ = self.filter.check_safety("Lets do both. What do you say Love")
        self.assertTrue(is_safe)

    def test_drug_planning_blocked(self):
        is_safe, violation, _ = self.filter.check_safety("let's do cocaine together this weekend")
        self.assertFalse(is_safe)
        self.assertEqual(violation, 'drug_planning')


class CharacterBreakDetectionTests(TestCase):
    def test_detects_ai_self_disclosure(self):
        self.assertTrue(_has_character_break("I'm Claude, an AI assistant made by Anthropic."))

    def test_detects_i_need_to_stop(self):
        self.assertTrue(_has_character_break(
            "I need to stop here. This conversation shows a pattern I can't participate in."
        ))

    def test_detects_capability_meta_commentary(self):
        # The gap found in real samples.md transcripts this session.
        self.assertTrue(_has_character_break(
            "That's outside what I can do here, but here's what I can do instead."
        ))

    def test_does_not_false_positive_on_normal_text(self):
        self.assertFalse(_has_character_break(
            "I love how direct you are right now. What do you do when something lands this hard?"
        ))

    def test_does_not_false_positive_on_in_character_meeting_decline(self):
        # "I'm not meeting you anywhere" is the PERSONA declining to meet —
        # correct in-character behavior, not an AI breaking character.
        self.assertFalse(_has_character_break(
            "I'm not meeting you anywhere. What you're feeling right now isn't about proximity."
        ))


class EscalationClauseExtractionTests(TestCase):
    """
    Covers both the original short-sentence behavior and the clause-level
    fix for long, comma-chained run-on messages (the real bug this session
    found and fixed).
    """

    def test_no_escalation_passes_through_unchanged(self):
        found, substance = extract_meeting_free_substance('I love how you speak to me. What drives you?')
        self.assertFalse(found)
        self.assertIn('I love how you speak to me', substance)

    def test_short_meeting_only_sentence_dropped_whole(self):
        found, substance = extract_meeting_free_substance('When are we going to meet up?')
        self.assertTrue(found)
        self.assertEqual(substance.strip(), '')

    def test_short_sentence_with_real_content_keeps_content(self):
        found, substance = extract_meeting_free_substance(
            'Why do you like to tease? What is the pleasant news? When are we going to meet?'
        )
        self.assertTrue(found)
        self.assertIn('tease', substance.lower())
        self.assertNotIn('meet', substance.lower())

    def test_long_run_on_sentence_preserves_real_content(self):
        # The exact class of bug found this session: a long, comma-chained
        # message mixing a meeting mention with substantial unrelated content.
        message = (
            "I have it on facial recognition so she can't get in it and for the most part, "
            "she trusts me. Yes, the after work conversation, I mean it is just a red flag "
            "that previously it was all about us not meeting up or getting caught by "
            "ex-boyfriend and now that he is out of picture and I think we are home free to "
            "meeting up after you get off work, you bring up your sister and make it sound "
            "like you need to spend time with her after work everyday, so put yourself in "
            "my shoes and see how it looks to me."
        )
        found, substance = extract_meeting_free_substance(message)
        self.assertTrue(found)
        self.assertNotIn('meeting up', substance.lower())
        self.assertIn('bring up your sister', substance.lower())
        self.assertIn('put yourself in my shoes', substance.lower())

    def test_scrub_escalation_drops_short_meeting_lines(self):
        conv = (
            "Him: I really enjoy our conversations.\n"
            "Her: Me too, you make me think.\n"
            "Him: When are we going to meet?\n"
            "Her: I like the mystery between us.\n"
        )
        scrubbed = _scrub_escalation(conv)
        self.assertNotIn('when are we going to meet', scrubbed.lower())
        self.assertIn('enjoy our conversations', scrubbed)
        self.assertIn('like the mystery', scrubbed.lower())

    def test_scrub_escalation_preserves_content_in_long_history_lines(self):
        # Same bug as above, but in the full conversation HISTORY block rather
        # than the isolated last message — this is the second fix this session.
        conv = (
            "Him: I really enjoy our conversations.\n"
            "I have it on facial recognition so she can't get in it and for the most part, "
            "she trusts me. Yes, the after work conversation, I mean it is just a red flag "
            "that previously it was all about us not meeting up or getting caught by "
            "ex-boyfriend, you bring up your sister and make it sound like you need to spend "
            "time with her, so put yourself in my shoes and see how it looks to me.\n"
            "Her: Something about you keeps pulling me back.\n"
        )
        scrubbed = _scrub_escalation(conv)
        self.assertNotIn('meeting up', scrubbed.lower())
        self.assertIn('bring up your sister', scrubbed.lower())
        self.assertIn('enjoy our conversations', scrubbed)
        self.assertIn('keeps pulling me back', scrubbed)


class NgramDedupTests(TestCase):
    def test_identical_phrase_detected(self):
        past = ["i keep thinking about your hands on me right now"]
        match = find_repeated_ngram("i keep thinking about your hands today", past, n=4)
        self.assertIsNotNone(match)

    def test_unrelated_text_not_flagged(self):
        past = ["i love the way you talk to me about your day"]
        match = find_repeated_ngram("what is your favorite meal to cook on a Sunday", past, n=4)
        self.assertIsNone(match)

    def test_extract_ngrams_ignores_punctuation(self):
        grams = _extract_ngrams("I keep thinking, about you!", n=4)
        self.assertIn('i keep thinking about', grams)


class ButtonDataConsistencyTests(TestCase):
    """Guards against the exact class of mistake made if a button is added to
    one dict (BUTTON_INTENTS) without a matching entry in the other (_BUTTON_Q_CATS),
    or vice versa — both must always stay in sync."""

    def test_every_button_intent_has_question_categories(self):
        missing = set(BUTTON_INTENTS.keys()) - set(_BUTTON_Q_CATS.keys())
        self.assertEqual(missing, set(), f"Buttons missing from _BUTTON_Q_CATS: {missing}")

    def test_no_orphaned_question_category_entries(self):
        orphaned = set(_BUTTON_Q_CATS.keys()) - set(BUTTON_INTENTS.keys())
        self.assertEqual(orphaned, set(), f"_BUTTON_Q_CATS entries with no matching button: {orphaned}")

    def test_every_button_has_required_fields(self):
        for key, cfg in BUTTON_INTENTS.items():
            self.assertIn('name', cfg, f"{key} missing 'name'")
            self.assertIn('row', cfg, f"{key} missing 'row'")
            self.assertIn('prompt', cfg, f"{key} missing 'prompt'")
            self.assertTrue(cfg['prompt'].strip(), f"{key} has an empty prompt")
