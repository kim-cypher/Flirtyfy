"""
Regression tests for the "make the shape non-identical" work: variable form,
casual question-forms, persona archetypes, the anchor/deep-pivot gate, the
ported God/chest gates, and the governor body-tell caps.

All pure-Python (no LLM calls). Run with:

    python manage.py test accounts.tests.test_persona_shape
"""
from django.test import TestCase

from accounts.services.button_generator import (
    _is_genuine_question,
    ensure_ends_with_question,
    _QUESTION_STARTERS,
    _LOOSE_QUESTION_STARTERS,
)
from accounts.services.intent_detector import (
    _select_archetype,
    _ARCHETYPES,
    _has_deep_pivot,
    _has_banned_opener,
    _reply_violations,
)
from accounts.services import vocab_governor as vg


class CasualQuestionGateTests(TestCase):
    """The gate must ACCEPT casual human questions but still reject bare
    noun-phrase-plus-'?' artifacts."""

    def test_accepts_casual_forms(self):
        for q in [
            "School bus, huh. You into that kind of chaos every morning?",
            "Bold move. So what's your actual move here?",
            "Where'd all that confidence come from?",
            "You're trouble. You gonna make me wait for it?",
            "Ever done anything that reckless?",
        ]:
            self.assertTrue(_is_genuine_question(q), f"should accept: {q}")

    def test_still_accepts_formal_forms(self):
        self.assertTrue(_is_genuine_question("I love that. What are you secretly great at?"))
        self.assertTrue(_is_genuine_question("Tell me one thing. How did that feel?"))

    def test_rejects_bare_noun_phrase(self):
        # The artifact the opener rule exists to catch.
        self.assertFalse(_is_genuine_question("That directness?"))
        self.assertFalse(_is_genuine_question("Your confidence really something?"))

    def test_rejects_non_question(self):
        self.assertFalse(_is_genuine_question("I like that a lot."))


class QuestionRestorerStaysStrictTests(TestCase):
    """ensure_ends_with_question must NOT fake-convert a statement into a
    question just because casual leads were added to the GATE set."""

    def test_loose_set_is_superset_of_strict(self):
        self.assertTrue(_QUESTION_STARTERS.issubset(_LOOSE_QUESTION_STARTERS))
        self.assertIn('you', _LOOSE_QUESTION_STARTERS)
        self.assertNotIn('you', _QUESTION_STARTERS)

    def test_does_not_manufacture_question_from_you_statement(self):
        # "You're the worst." starts with a casual lead but is a statement; the
        # restorer must leave it alone (no '?' appended).
        out = ensure_ends_with_question("You're the worst.", max_chars=300)
        self.assertFalse(out.endswith('?'))

    def test_restores_mark_on_real_formal_question(self):
        out = ensure_ends_with_question("I like that. What do you do for fun", max_chars=300)
        self.assertTrue(out.endswith('?'))


class ArchetypeTests(TestCase):
    def test_stable_per_conversation(self):
        conv = "HIM: I drive a school bus for Hillsborough"
        self.assertEqual(_select_archetype(conv), _select_archetype(conv))
        # Whitespace/case-insensitive stability.
        self.assertEqual(_select_archetype(conv), _select_archetype("  " + conv.upper() + " "))

    def test_varies_across_conversations(self):
        convs = [f"HIM: message number {i} about totally different things {i*7}" for i in range(40)]
        seen = {_select_archetype(c) for c in convs}
        # Over 40 distinct conversations we should hit at least 3 of the 4 voices.
        self.assertGreaterEqual(len(seen), 3)

    def test_always_valid_key(self):
        for c in ["", "hi", "HIM: yes except weekends"]:
            self.assertIn(_select_archetype(c), _ARCHETYPES)


class DeepPivotGateTests(TestCase):
    def test_flags_vulnerability_button_phrasings(self):
        for q in [
            "So you drive a bus. Which part of yourself do you only hand over once you trust someone?",
            "Nice. Is there something you guard closely and never show?",
            "What part of you do you keep hidden from everyone?",
            "Do you have something you protect instead of reveal?",
        ]:
            self.assertTrue(_has_deep_pivot(q), f"should flag deep pivot: {q}")

    def test_spares_normal_questions(self):
        for q in [
            "School bus, huh. What's the worst thing a kid's pulled back there?",
            "What do you do with your mornings when you're free?",
            "You gonna make me wait for it?",
        ]:
            self.assertFalse(_has_deep_pivot(q), f"should NOT flag: {q}")


class LeftPanelGatePortTests(TestCase):
    def test_god_and_ha_openers_flagged(self):
        self.assertTrue(_has_banned_opener("God, you have no idea what that does."))
        self.assertTrue(_has_banned_opener("Honestly, I can't stop thinking about it."))
        self.assertTrue(_has_banned_opener("Ha, you wish."))
        self.assertTrue(_has_banned_opener("Haha okay that's fair."))

    def test_god_opener_not_false_positive_midword(self):
        # "Have you..." must NOT be caught by the 'ha ' opener.
        self.assertFalse(_has_banned_opener("Have you ever done that?"))

    def test_reply_violations_catches_chest_and_pivot_and_god(self):
        # chest tell
        self.assertIn(
            'chest as a physical tell',
            ' '.join(_reply_violations("That warmth in my chest is unreal. What do you do for fun?")),
        )
        # deep pivot
        self.assertTrue(any(
            'deep-pivot' in v for v in
            _reply_violations("Nice bus job. Which part of yourself do you keep hidden from everyone?")
        ))
        # God opener
        self.assertTrue(any(
            'banned opener' in v for v in
            _reply_violations("God, the way you say that. What are you into tonight?")
        ))

    def test_clean_reply_passes(self):
        # Must be >= 18 words to clear the length floor.
        self.assertEqual(
            _reply_violations(
                "School bus, huh, that takes real patience most people don't have. "
                "What's the worst thing a kid has ever pulled on you back there?"
            ),
            [],
        )

    def test_too_short_is_flagged(self):
        short = "Ha, bold move. What's your deal?"  # 6 words
        self.assertTrue(any('at least 18 words' in v for v in _reply_violations(short)))
        # A 20-word reply clears the floor.
        ok = ("School bus, huh, that takes real patience most people don't have. "
              "What's the worst thing a kid has pulled back there?")
        self.assertFalse(any('at least 18 words' in v for v in _reply_violations(ok)))


class GovernorBodyTellTests(TestCase):
    def test_new_body_tells_watched(self):
        for tid in ['thighs', 'squeeze', 'ache_body', 'right_now', 'highlight_reel']:
            self.assertIn(tid, vg._SEED_WATCH)

    def test_terms_detected(self):
        self.assertIn('thighs', vg._terms_in("my thighs pressed together already"))
        self.assertIn('right_now', vg._terms_in("I want you right now"))
        self.assertIn('highlight_reel', vg._terms_in("most men just want the highlight reel"))
        self.assertIn('ache_body', vg._terms_in("that ache building slow"))
