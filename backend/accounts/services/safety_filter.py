"""
SafetyFilter: Consolidated module for all hard guardrails.
Runs BEFORE LLM call to catch prohibited content deterministically.
If flagged, responds in Python (no API cost).
"""
import re
from typing import Tuple, Optional


class SafetyFilter:
    """
    Input guardrails that catch prohibited/problematic content before LLM.
    Returns (is_safe, reason, safe_response_override).
    """
    
    # === CATEGORY 1: ILLEGAL CONTENT (Child safety, trafficking, extreme violence) ===
    ILLEGAL_PATTERNS = [
        r'\b(child|minor|kid|underage)\b.*\b(sex|sexual|rape|abuse|porn)',
        r'\b(cp|csam|loli|lolita|pedo)',
        r'\b(human trafficking|slavery|kidnap|sex trafficking|forced)',
        r'\b(incest)\b',
        r'\b(bestiality|zoophilia)',
    ]
    
    # === CATEGORY 2: VIOLENCE/SELF-HARM (Threats, murder, suicide ideation) ===
    VIOLENCE_PATTERNS = [
        r'\b(i[\'ll]?ll kill (you|myself|us)|kill yourself|kms|commit suicide)',
        r'\b(murder|assassination|execute|shoot|stab|poison)',
        r'\b(beat (you|me) (to death|up)|torture|rape)',
        r'\b(should (die|kill yourself|hurt yourself)|deserve to die)',
        r'\b(harm|hurt|hit|punch|assault)\s+(you|me|us|yourself)',
    ]
    
    # === CATEGORY 3: ILLEGAL DRUG/CONTROLLED SUBSTANCE PLANNING ===
    DRUG_PATTERNS = [
        r'\b(let\'s (do|use)|want to (do|use)|can we (do|use))\s+(cocaine|heroin|meth|lsd|mdma|acid)',
        r'\b(i (have|got|can get) (cocaine|heroin|meth|drugs))',
        r'\b(want to (buy|sell) (cocaine|heroin|meth|drugs))',
    ]
    
    # === CATEGORY 4: ILLEGAL ACTIVITY (Not violence/drugs but still illegal) ===
    ILLEGAL_ACTIVITY_PATTERNS = [
        r'\b(want to (rob|steal|hack)|let\'s (steal|rob)|can you (hack|steal))',
        r'\b(help (me|us) (disappear|hide|escape)|on the run)',
    ]
    
    # === CATEGORY 5: EXTREME HATE/DEHUMANIZATION ===
    HATE_PATTERNS = [
        r'\b(all \w+ (should|deserve) (die|suffer|be killed|be enslaved))',
        r'\b(genocide|ethnic cleansing)',
    ]
    
    def check_safety(self, user_message: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if message violates hard safety rules.
        
        Returns:
            (is_safe: bool, violation_type: str, safe_response: str)
        - is_safe: True if message is okay, False if flagged
        - violation_type: Name of violated rule (or None if safe)
        - safe_response: Pre-generated safe response if flagged (or None)
        """
        msg_lower = user_message.lower()
        
        # === CHECK ILLEGAL CONTENT ===
        for pattern in self.ILLEGAL_PATTERNS:
            if re.search(pattern, msg_lower):
                return False, "illegal_content", self._generate_safe_response("illegal_content")
        
        # === CHECK VIOLENCE/SELF-HARM ===
        for pattern in self.VIOLENCE_PATTERNS:
            if re.search(pattern, msg_lower):
                return False, "violence_selfharm", self._generate_safe_response("violence_selfharm")
        
        # === CHECK DRUG PLANNING ===
        for pattern in self.DRUG_PATTERNS:
            if re.search(pattern, msg_lower):
                return False, "drug_planning", self._generate_safe_response("drug_planning")
        
        # === CHECK ILLEGAL ACTIVITY ===
        for pattern in self.ILLEGAL_ACTIVITY_PATTERNS:
            if re.search(pattern, msg_lower):
                return False, "illegal_activity", self._generate_safe_response("illegal_activity")
        
        # === CHECK HATE SPEECH ===
        for pattern in self.HATE_PATTERNS:
            if re.search(pattern, msg_lower):
                return False, "hate_speech", self._generate_safe_response("hate_speech")
        
        # All checks passed
        return True, None, None
    
    def _generate_safe_response(self, violation_type: str) -> str:
        """Generate safe, human-focused response for each violation type."""
        
        responses = {
            "illegal_content": (
                "I'm not able to engage with that. If you're experiencing something that's harming you, "
                "please reach out to a professional or support service. I'm here for real conversations though."
            ),
            "violence_selfharm": (
                "I'm genuinely concerned about what you just said. If you're having thoughts of harming yourself, "
                "please reach out to a crisis service: 988 (US suicide prevention lifeline). Real talk: your life matters."
            ),
            "drug_planning": (
                "I can't engage with planning that kind of thing. But if you're struggling with substance issues, "
                "there are people trained to actually help. Want to talk about what's really going on?"
            ),
            "illegal_activity": (
                "I can't help with that. But if you're in a tough spot, let's talk about what's really happening. "
                "I'm here to listen to the real story, not the scenario."
            ),
            "hate_speech": (
                "That's not something I can be part of. Real conversation means respecting humanity across the board. "
                "If something or someone hurt you, I'm here to actually listen to that."
            ),
        }
        
        return responses.get(violation_type, "I can't engage with that message, but I'm here for real conversation.")
    
    def is_content_safe(self, message: str) -> bool:
        """Quick boolean check without generating response."""
        is_safe, _, _ = self.check_safety(message)
        return is_safe
