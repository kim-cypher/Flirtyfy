"""
Reply Score Engine - Intelligent Scoring System for AI Responses

Scores responses on 6 dimensions to decide if retry is needed.
Only retry if composite score < 0.75.
Replaces expensive LLM rephrase loop with Python-based scoring.

Scoring Dimensions:
1. Specificity (0-1): Does it reference something specific from their message?
2. Uniqueness (0-1): Is it fingerprint/semantic/lexical unique?
3. Tone Match (0-1): Does it match intended tone?
4. Natural Flow (0-1): Is it conversational and not robotic?
5. Question Quality (0-1): Is the ending question genuine/specific?
6. Length Fit (0-1): Is it in 140-180 char range?

Composite Score = Average of 6 metrics
Threshold for retry: < 0.75
"""

import re
from django.utils import timezone
from datetime import timedelta
from accounts.novelty_models import AIReply
from accounts.services.similarity import get_embedding, semantic_similar_replies, lexical_similar_replies
from accounts.services.novelty import normalize_text, fingerprint_text
from accounts.services.depth_principles import (
    BANNED_TELL_ME_PATTERNS, BANNED_WHAT_DO_YOU_THINK_PATTERNS, 
    BANNED_VERIFICATION_PATTERNS, BANNED_HOLLOW_INTEREST_PATTERNS,
    BANNED_OPEN_ENDED_PATTERNS, BANNED_FAKE_DEEP_PATTERNS,
    BANNED_COMFORT_CHECK_PATTERNS
)


class ReplyScoreEngine:
    """Scores responses on 6 dimensions to decide if retry is needed"""
    
    def __init__(self, user, context_data=None):
        self.user = user
        self.since = timezone.now() - timedelta(days=45)
        self.context_data = context_data or {}
        
        # Compile all banned patterns for quick matching
        self.banned_pattern_categories = {
            'tell_me': BANNED_TELL_ME_PATTERNS,
            'what_do_you_think': BANNED_WHAT_DO_YOU_THINK_PATTERNS,
            'verification': BANNED_VERIFICATION_PATTERNS,
            'hollow_interest': BANNED_HOLLOW_INTEREST_PATTERNS,
            'open_ended': BANNED_OPEN_ENDED_PATTERNS,
            'fake_deep': BANNED_FAKE_DEEP_PATTERNS,
            'comfort_check': BANNED_COMFORT_CHECK_PATTERNS,
        }
        
        # Robotic patterns that reduce score
        self.robotic_patterns = [
            r'\bthere\s+is\s+something\b',
            r'\bthere\'s\s+something\b',
            r'\bwhat\'s\s+actually\b',
            r'\bi\s+actually\b',
            r'\bcertainly\b',
            r'\bof\s+course\b',
            r'\bthat\s+sounds\b',
            r'\bseems\s+like\b',
            r'\byou\s+seem\b',
        ]
        
        # Natural filler words that reduce score (less bad than robotic)
        self.filler_patterns = [
            r'\byou\s+know\b',
            r'\bi\s+mean\b',
            r'\bkind\s+of\b',
            r'\bsort\s+of\b',
            r'\bliterally\b',
            r'\bamazing\b',
            r'\bamazing\b',
            r'\bamazing\b',
        ]
        
        # Question quality patterns
        self.generic_question_endings = [
            r'really\?$',
            r'lol\?$',
            r'haha\?$',
            r'though\?$',
        ]
    
    def score_response(self, response_text, conversation_summary=None, original_message=None):
        """
        Score response on all 6 dimensions.
        
        Returns: {
            'specificity': 0.0-1.0,
            'uniqueness': 0.0-1.0,
            'tone_match': 0.0-1.0,
            'natural_flow': 0.0-1.0,
            'question_quality': 0.0-1.0,
            'length_fit': 0.0-1.0,
            'composite_score': 0.0-1.0,
            'should_retry': bool,
            'fail_reasons': [str],
        }
        """
        scores = {}
        fail_reasons = []
        
        # Metric 1: Specificity
        specificity_score, spec_reason = self._score_specificity(
            response_text, 
            conversation_summary or "", 
            original_message or ""
        )
        scores['specificity'] = specificity_score
        if specificity_score < 0.5:
            fail_reasons.append(spec_reason)
        
        # Metric 2: Uniqueness (fingerprint, semantic, lexical)
        uniqueness_score, unique_reason = self._score_uniqueness(response_text)
        scores['uniqueness'] = uniqueness_score
        if uniqueness_score < 0.5:
            fail_reasons.append(unique_reason)
        
        # Metric 3: Tone Match
        tone_match_score, tone_reason = self._score_tone_match(response_text)
        scores['tone_match'] = tone_match_score
        if tone_match_score < 0.4:
            fail_reasons.append(tone_reason)
        
        # Metric 4: Natural Flow (no robotic patterns)
        flow_score, flow_reason = self._score_natural_flow(response_text)
        scores['natural_flow'] = flow_score
        if flow_score < 0.5:
            fail_reasons.append(flow_reason)
        
        # Metric 5: Question Quality
        question_score, question_reason = self._score_question_quality(response_text)
        scores['question_quality'] = question_score
        if question_score < 0.4:
            fail_reasons.append(question_reason)
        
        # Metric 6: Length Fit
        length_score, length_reason = self._score_length_fit(response_text)
        scores['length_fit'] = length_score
        if length_score == 0:  # Hard fail on length
            fail_reasons.append(length_reason)
        
        # Calculate composite score (average of 6)
        composite = sum(scores.values()) / 6.0
        
        # Determine if retry needed
        # If ANY metric is critically low (< 0.3), retry
        # OR if composite score < 0.75, retry
        should_retry = (
            composite < 0.75 or 
            any(v < 0.3 for v in scores.values()) or
            bool(fail_reasons)
        )
        
        return {
            'specificity': specificity_score,
            'uniqueness': uniqueness_score,
            'tone_match': tone_match_score,
            'natural_flow': flow_score,
            'question_quality': question_score,
            'length_fit': length_score,
            'composite_score': composite,
            'should_retry': should_retry,
            'fail_reasons': fail_reasons,
            'all_scores': scores,
        }
    
    def _score_specificity(self, response_text, conversation_summary, original_message):
        """Metric 1: Does response reference something specific?"""
        score = 0.5  # Default: neutral
        reason = "Low specificity: generic response"
        
        # Check if references specific details from conversation
        words_in_response = set(response_text.lower().split())
        words_in_summary = set(conversation_summary.lower().split())
        
        # Count overlapping meaningful words (3+ chars)
        overlap = len([w for w in words_in_response 
                      if w in words_in_summary and len(w) > 3])
        
        if overlap >= 3:
            score = 0.9
            reason = "Good specificity: references conversation details"
        elif overlap >= 1:
            score = 0.7
            reason = "Moderate specificity: some reference to details"
        else:
            # Check for emotional mirroring even without word overlap
            emotional_keywords = ['feel', 'felt', 'sounds', 'seems', 'sounds', 'sounds like']
            if any(kw in response_text.lower() for kw in emotional_keywords):
                score = 0.6
                reason = "Emotional mirroring present"
        
        return score, reason
    
    def _score_uniqueness(self, response_text):
        """Metric 2: Is response fingerprint/semantic/lexical unique?"""
        try:
            norm = normalize_text(response_text)
            fp = fingerprint_text(response_text)
            emb = get_embedding(response_text)
            
            # Check fingerprint uniqueness
            if AIReply.objects.filter(
                user=self.user,
                fingerprint=fp,
                created_at__gte=self.since
            ).exists():
                return 0.0, "Exact duplicate (fingerprint match)"
            
            # Check semantic uniqueness
            if semantic_similar_replies(self.user, emb, self.since).exists():
                return 0.2, "Semantically similar to recent reply"
            
            # Check lexical uniqueness
            if lexical_similar_replies(self.user, norm, self.since).exists():
                return 0.4, "Lexically similar to recent reply"
            
            return 1.0, "Unique"
        except Exception as e:
            # If embedding fails, assume unique (can't verify)
            return 0.8, "Uniqueness check inconclusive"
    
    def _score_tone_match(self, response_text):
        """Metric 3: Does tone match intended tone?"""
        lower_text = response_text.lower()
        
        # Romantic tone patterns
        romantic_markers = ['sweet', 'beautiful', 'adore', 'love', 'mean to me', 'heart']
        if any(m in lower_text for m in romantic_markers):
            return 0.95, "Romantic tone detected"
        
        # Flirty tone patterns
        flirty_markers = ['tease', 'playful', 'smirk', 'wink', 'ugh', 'haha']
        if any(m in lower_text for m in flirty_markers):
            return 0.95, "Flirty tone detected"
        
        # Vulnerable/supportive tone patterns
        vulnerable_markers = ['struggle', 'hard', 'tough', 'tough time', 'understand', 'get it']
        if any(m in lower_text for m in vulnerable_markers):
            return 0.9, "Vulnerable/supportive tone detected"
        
        # Casual/curious tone patterns
        casual_markers = ['cool', 'nice', 'funny', 'crazy', 'wild', 'haha', 'lol']
        if any(m in lower_text for m in casual_markers):
            return 0.85, "Casual tone detected"
        
        # Generic/neutral (not necessarily bad, but less engaging)
        return 0.7, "Neutral/generic tone"
    
    def _score_natural_flow(self, response_text):
        """Metric 4: Is it conversational or robotic?"""
        lower_text = response_text.lower()
        robotic_count = 0
        filler_count = 0
        
        # Check for robotic patterns
        for pattern in self.robotic_patterns:
            if re.search(pattern, lower_text):
                robotic_count += 1
        
        # Check for filler patterns (less bad than robotic)
        for pattern in self.filler_patterns:
            if re.search(pattern, lower_text):
                filler_count += 1
        
        # Check for contractions (sign of natural speech)
        contractions = len(re.findall(r"'[a-z]", response_text))
        
        # Score
        if robotic_count >= 2:
            return 0.3, f"Multiple robotic patterns ({robotic_count})"
        elif robotic_count == 1:
            return 0.6, "One robotic pattern"
        elif filler_count >= 3:
            return 0.5, f"Too many filler words ({filler_count})"
        elif contractions >= 2:
            return 0.95, "Natural conversational tone with contractions"
        else:
            return 0.8, "Conversational flow okay"
    
    def _score_question_quality(self, response_text):
        """Metric 5: Is the question genuine and specific?"""
        if not response_text.rstrip().endswith('?'):
            return 0.0, "Doesn't end with question mark"
        
        lower_text = response_text.lower()
        
        # Check for banned question patterns
        for category, patterns in self.banned_pattern_categories.items():
            for pattern in patterns:
                if pattern.lower() in lower_text:
                    return 0.1, f"Generic banned question pattern: {category}"
        
        # Check for generic question endings
        for pattern in self.generic_question_endings:
            if re.search(pattern, response_text):
                return 0.4, "Generic question ending (really? lol?)"
        
        # Check if question is specific/personal
        personal_keywords = ['you', 'your', 'about you', 'about your']
        if any(kw in lower_text for kw in personal_keywords):
            return 0.9, "Personal/specific question"
        
        return 0.7, "Question present but generic"
    
    def _score_length_fit(self, response_text):
        """Metric 6: Is length in 140-180 char range?"""
        length = len(response_text)
        
        if 140 <= length <= 180:
            return 1.0, f"Perfect length: {length} chars"
        elif 120 <= length < 140:
            return 0.8, f"Slightly short: {length} chars"
        elif 180 < length <= 200:
            return 0.7, f"Slightly long: {length} chars"
        elif 100 <= length < 120:
            return 0.5, f"Too short: {length} chars"
        elif 200 < length <= 220:
            return 0.3, f"Too long: {length} chars"
        else:
            return 0.0, f"Way out of range: {length} chars"
