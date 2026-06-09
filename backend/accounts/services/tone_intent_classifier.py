"""
ToneIntentClassifier: Python-based classification of user message tone/intent.
Uses rule-based heuristics (keywords, patterns) to tag messages without LLM.
Fast, deterministic, no API cost.
"""
import re
from typing import Tuple
from enum import Enum


class Tone(str, Enum):
    FLIRTY = "flirty"
    ROMANTIC = "romantic"
    PLAYFUL = "playful"
    SUPPORTIVE = "supportive"
    CASUAL = "casual"
    VULNERABLE = "vulnerable"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"


class Intent(str, Enum):
    QUESTION = "question"
    STATEMENT = "statement"
    JOKE = "joke"
    COMPLAINT = "complaint"
    DISCLOSURE = "disclosure"
    CHALLENGE = "challenge"
    FLIRTATION = "flirtation"


class EmotionLevel(str, Enum):
    HIGH = "high"  # Excited, passionate, energetic
    NEUTRAL = "neutral"  # Balanced, calm
    LOW = "low"  # Sad, tired, withdrawn


class ToneIntentClassifier:
    """Classifies user messages into tone/intent/emotion without LLM."""
    
    # === TONE PATTERNS ===
    FLIRTY_PATTERNS = [
        r'\b(wanna|want to|curious|wondering)\b.*\s(about you|know you|understand you)',
        r'\b(you\'re|youre|you are).*(interesting|intriguing|mysterious|fascinating)',
        r'\b(caught my attention|got my attention|stands out)\b',
        r'\b(how do you|tell me|show me).*(this|that)\b',
        r'\b(drive me|get me).*(crazy|wild|going)',
        r'\b(that\'s|that is).*(hot|sexy|attractive)\b',
        r'\b(i.*like|i.*want).*(you|this side)\b',
        r'(?:^|[^a-z])(lol|haha|😏|wink|😉)',  # Playful markers
    ]
    
    ROMANTIC_PATTERNS = [
        r'\b(feel something|connection|understand me|see me)\b',
        r'\b(real talk|honestly|truth is)\b.*\b(like|love|want|need)\b',
        r'\b(vulnerable|scared|scared to|afraid to share)\b',
        r'\b(never felt|felt this|this different)\b',
        r'\b(heart|soul|deep|meaningful)\b',
    ]
    
    PLAYFUL_PATTERNS = [
        r'\b(haha|lol|lmao|😂|rofl)\b',
        r'\b(just kidding|jk|just messing|being silly)\b',
        r'\b(that\'s funny|made me laugh)\b',
        r'\b(dare you|challenge you|bet)\b',
        r'\b(tease|teasing|playful)\b',
    ]
    
    SUPPORTIVE_PATTERNS = [
        r'\b(i[\'m]?m (here|listening|there))\b',
        r'\b(you\'re (strong|brave|amazing))\b',
        r'\b(i (get it|understand|hear you))\b',
        r'\b(don\'t worry|you (can|will|got this))\b',
        r'\b(that\'s (tough|rough|hard) but)\b',
    ]
    
    VULNERABLE_PATTERNS = [
        r'\b(scared|anxiety|depression|overwhelm|can\'t handle)\b',
        r'\b(what if|i don\'t know|unsure|doubt)\b',
        r'\b(never told|hard to say|admit)\b',
        r'\b(mess|broken|not enough|don\'t deserve)\b',
        r'\b(lonely|alone|isolat)\b',
    ]
    
    FRUSTRATED_PATTERNS = [
        r'\b(can\'t|won\'t|don\'t|frustrated|annoyed|pissed|mad|angry)\b',
        r'\b(waste of time|stupid|pointless|ridiculous|fed up)\b',
        r'\b(fuck|shit|damn|crap)\b.*\b(this|you|it|app)\b',
        r'\b(why does|why can\'t|why won\'t)\b',
        r'\b(leaving|done|quit|delete)\b',
    ]
    
    CURIOUS_PATTERNS = [
        r'\b(what|how|why|when|where)\b.*\?',
        r'\b(tell me|show me|explain|help me understand)\b',
        r'\b(wondering|curious|want to know)\b',
        r'\b(think about|perspective on|opinion)\b',
    ]
    
    # === INTENT PATTERNS ===
    QUESTION_PATTERNS = [
        r'.*\?$',  # Ends with question mark
        r'\b(do you|are you|can you|will you|would you|should you)\b',
    ]
    
    JOKE_PATTERNS = [
        r'\b(lol|haha|😂|rofl|lmao)\b',
        r'\b(just messing|kidding|joking|funny|joke)\b',
        r'(?:^|[^a-z])(😄|😆|😹)',
    ]
    
    COMPLAINT_PATTERNS = [
        r'\b(problem|issue|broken|not work|frustrated|annoyed)\b',
        r'\b(why|how come|shouldn\'t|wrong|bad)\b',
    ]
    
    DISCLOSURE_PATTERNS = [
        r'\b(never told|hard to admit|truth is|honestly)\b',
        r'\b(real talk|actually|secret|confess)\b',
        r'\b(scared to|worried about|nervous)\b',
    ]
    
    CHALLENGE_PATTERNS = [
        r'\b(bet|dare|can you|prove|test)\b',
        r'\b(i don\'t believe|really|no way)\b',
    ]
    
    # === EMOTION PATTERNS ===
    HIGH_EMOTION = [
        r'\b(!!|!!!|\?\?|wow|amazing|incredible|love|hate)\b',
        r'\b(so|really|very|super|extremely)\b.*\b(excited|happy|sad|mad)',
        r'(?:^|[^a-z])(😍|🔥|😡|😭)',
        r'\b(can\'t (wait|believe)|ahhh|omg)\b',
    ]
    
    LOW_EMOTION = [
        r'\b(tired|exhausted|done|whatever|meh|dunno|idk)\b',
        r'\b(i guess|suppose|fine|okay|sure)\b',
        r'(?:^|[^a-z])(😴|😔|😑)',
    ]
    
    def classify(self, message: str) -> Tuple[Tone, Intent, EmotionLevel]:
        """
        Classify a user message into tone, intent, and emotion level.
        Uses pattern matching (no LLM call).
        
        Returns: (tone, intent, emotion_level)
        """
        msg_lower = message.lower()
        msg_len = len(message)
        
        # === CLASSIFY TONE ===
        tone = self._classify_tone(msg_lower)
        
        # === CLASSIFY INTENT ===
        intent = self._classify_intent(msg_lower)
        
        # === CLASSIFY EMOTION LEVEL ===
        emotion = self._classify_emotion(msg_lower)
        
        return tone, intent, emotion
    
    def _classify_tone(self, msg_lower: str) -> Tone:
        """Determine primary tone from patterns."""
        
        # Priority order (frustration > vulnerable > romantic > flirty > playful > supportive > casual)
        score = {tone: 0 for tone in Tone}
        
        for pattern in self.FRUSTRATED_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.FRUSTRATED] += 1
        
        for pattern in self.VULNERABLE_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.VULNERABLE] += 1
        
        for pattern in self.ROMANTIC_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.ROMANTIC] += 1
        
        for pattern in self.FLIRTY_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.FLIRTY] += 1
        
        for pattern in self.PLAYFUL_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.PLAYFUL] += 1
        
        for pattern in self.SUPPORTIVE_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.SUPPORTIVE] += 1
        
        for pattern in self.CURIOUS_PATTERNS:
            if re.search(pattern, msg_lower):
                score[Tone.CURIOUS] += 1
        
        # Return highest-scoring tone (or default to casual)
        best_tone = max(score, key=score.get)
        return best_tone if score[best_tone] > 0 else Tone.CASUAL
    
    def _classify_intent(self, msg_lower: str) -> Intent:
        """Determine primary intent from patterns."""
        
        if any(re.search(pat, msg_lower) for pat in self.QUESTION_PATTERNS):
            return Intent.QUESTION
        
        if any(re.search(pat, msg_lower) for pat in self.JOKE_PATTERNS):
            return Intent.JOKE
        
        if any(re.search(pat, msg_lower) for pat in self.CHALLENGE_PATTERNS):
            return Intent.CHALLENGE
        
        if any(re.search(pat, msg_lower) for pat in self.DISCLOSURE_PATTERNS):
            return Intent.DISCLOSURE
        
        if any(re.search(pat, msg_lower) for pat in self.COMPLAINT_PATTERNS):
            return Intent.COMPLAINT
        
        if any(re.search(pat, msg_lower) for pat in self.FLIRTATION_PATTERNS):
            return Intent.FLIRTATION
        
        return Intent.STATEMENT
    
    def _classify_emotion(self, msg_lower: str) -> EmotionLevel:
        """Determine emotion intensity."""
        
        high_count = sum(1 for pat in self.HIGH_EMOTION if re.search(pat, msg_lower))
        low_count = sum(1 for pat in self.LOW_EMOTION if re.search(pat, msg_lower))
        
        if high_count > low_count:
            return EmotionLevel.HIGH
        elif low_count > high_count:
            return EmotionLevel.LOW
        else:
            return EmotionLevel.NEUTRAL
    
    # Alias for code compatibility
    FLIRTATION_PATTERNS = FLIRTY_PATTERNS
