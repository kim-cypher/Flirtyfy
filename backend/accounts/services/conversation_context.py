"""
ConversationContext: Lightweight state object that stores all context needed for LLM call.
Replaces the need to pass dozens of parameters through the system.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ConversationContext:
    """
    Minimal context for generating a single reply.
    Stores preprocessed state to pass to LLM (avoids redundant computation).
    """
    
    # === PARSING STATE ===
    message_count: int  # Total messages in conversation
    last_user_message: str  # Raw text of last user message
    conversation_summary: str  # 1-2 sentence abstract of conversation
    
    # === CLASSIFICATION STATE ===
    tone: str  # e.g., "flirty", "supportive", "romantic", "casual", "playful"
    intent: str  # e.g., "question", "complaint", "joke", "disclosure"
    emotion_level: str  # e.g., "high", "neutral", "frustrated"
    
    # === EXTRACTION STATE ===
    specific_reference: Optional[str] = None  # One concrete detail to mention
    referenced_topic: Optional[str] = None  # What they mentioned (work, hobby, feeling, etc.)
    
    # === LENGTH DETERMINATION ===
    min_chars: int = 80
    max_chars: int = 200
    user_message_length: int = 0  # For energy mirroring
    
    # === FORMAT FLAGS ===
    should_end_with_question: bool = True  # False = statement ending
    
    # === SAFETY STATE ===
    safety_flag: Optional[str] = None  # If set, indicates a safety issue (handles in Python, skip LLM)
    safety_response: Optional[str] = None  # Pre-generated safe response if flagged
    
    # === METADATA ===
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    attempt_number: int = 1  # Retry count
    metadata: dict = field(default_factory=dict)  # Custom metadata for tracking
    
    def is_flagged_for_safety(self) -> bool:
        """Check if this context was flagged by safety filters."""
        return self.safety_flag is not None
    
    def to_prompt_dict(self) -> dict:
        """
        Convert context to minimal dict for LLM prompt injection.
        Only includes dynamic fields—rules stay in Python.
        """
        return {
            "tone": self.tone,
            "intent": self.intent,
            "min_chars": self.min_chars,
            "max_chars": self.max_chars,
            "specific_reference": self.specific_reference or "what she said",
            "last_user_message": self.last_user_message,
            "conversation_summary": self.conversation_summary,
            "should_end_with_question": self.should_end_with_question,
            "message_count": self.message_count,
        }
    
    def __repr__(self) -> str:
        """Human-readable representation for logging."""
        return (
            f"ConversationContext("
            f"msg#{self.message_count}, "
            f"tone={self.tone}, "
            f"intent={self.intent}, "
            f"len={self.min_chars}-{self.max_chars}ch, "
            f"ref={self.specific_reference[:20] if self.specific_reference else 'None'}..., "
            f"flagged={self.is_flagged_for_safety()}"
            f")"
        )
