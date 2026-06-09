"""AI Generation Service (Refactored)

Refactored architecture moving all hard logic to Python, minimal LLM prompt.

Pipeline:
1. Parse conversation (existing ConversationParser)
2. Apply safety filters (SafetyFilter - Python checks before LLM)
3. Classify tone/intent/emotion (ToneIntentClassifier - Python, no LLM)
4. Extract specific detail (SpecificDetailExtractor - Python)
5. Determine response length (Python logic)
6. Call LLM with minimal, high-signal prompt
7. Post-process and comprehensive validate (ResponseValidator)
"""

import logging
import re
import random
import time
from typing import Optional, Tuple

from accounts.openai_service import get_openai_client
from accounts.services.response_validator import ResponseValidator
from accounts.services.conversation_parser import ConversationParser
from accounts.services.response_flow_validator import ListenRelateDeeperValidator, TopicClassifier
from accounts.services.safety_filter import SafetyFilter
from accounts.services.tone_intent_classifier import ToneIntentClassifier, Tone, Intent, EmotionLevel
from accounts.services.specific_detail_extractor import SpecificDetailExtractor
from accounts.services.metrics_tracker import MetricsTracker

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS (kept from original, still needed for post-processing)
# ============================================================================

def sanitize_response(response: str) -> str:
    """
    Ensure response meets quality standards:
    - Starts with capital letter
    - Proper sentence structure
    - Ends with appropriate punctuation
    """
    if not response or not response.strip():
        return response
    
    response = response.strip()
    
    # Capitalize first letter if it's lowercase
    if response and response[0].islower():
        response = response[0].upper() + response[1:]
    
    # Ensure ends with punctuation
    if response and not response.endswith(('?', '.', '!')):
        response = response + '?'
    
    return response


def enforce_character_count(response: str, min_chars: int, max_chars: int) -> str:
    """
    Enforce character count without filler text.
    If response is too short or too long, let it be — GPT-4 should respect context.
    Only enforce if drastically wrong.
    """
    current_length = len(response)
    
    # If response is severely under minimum, log but don't force filler
    if current_length < min_chars - 20:
        logger.debug(f"Response under minimum: {current_length} < {min_chars}")
    
    # If response exceeds max by a lot, truncate at sentence boundary
    elif current_length > max_chars + 20:
        truncate_at = response.rfind('.', 0, max_chars)
        if truncate_at == -1:
            truncate_at = response.rfind('?', 0, max_chars)
        if truncate_at == -1:
            truncate_at = response.rfind('!', 0, max_chars)
        
        if truncate_at > min_chars:
            response = response[:truncate_at + 1]
    
    return response


def enforce_ending_type(response: str, use_statement: bool) -> str:
    """
    Enforce whether response ends with statement (.) or question (?)
    """
    response = response.rstrip()
    
    if use_statement:
        # Should end with . or ! NOT ?
        if response.endswith('?'):
            response = response[:-1] + '.'
        elif not response.endswith(('.', '!')):
            response = response + '.'
    else:
        # Should end with ?
        if not response.endswith('?'):
            response = response.rstrip('.!') + '?'
    
    return response


def determine_response_length(
    user_message_length: int, 
    message_count: int, 
    tone: str, 
    emotional_intensity: str
) -> Tuple[int, int]:
    """
    Determine target character range based on conversation context.
    Returns (min_chars, max_chars)
    
    Factors:
    - User message length (mirror their energy) — PRIMARY
    - Conversation stage (early/mid/late)
    - Tone/topic (sexual/vulnerable/practical)
    - Emotional intensity (high/neutral)
    """
    min_chars = 80
    max_chars = 200
    
    # FACTOR 1: USER MESSAGE LENGTH — Mirror their energy
    if user_message_length < 50:
        base_max = 150
    elif user_message_length < 150:
        base_max = 200
    else:
        base_max = 280
    
    # FACTOR 2: CONVERSATION STAGE
    if message_count <= 3:
        if user_message_length > 150:
            max_chars = min(base_max, 150)
        else:
            max_chars = min(base_max, 120)
    elif message_count <= 8:
        max_chars = min(base_max, 200)
    else:
        max_chars = base_max
    
    # FACTOR 3: TONE/TOPIC
    if tone == 'sexual':
        max_chars = min(max_chars, 140)
    elif tone == 'supportive':
        max_chars = max(max_chars, 180)
        min_chars = min(min_chars, 100)
    elif tone == 'romantic':
        max_chars = min(max_chars, 220)
    
    # FACTOR 4: EMOTIONAL INTENSITY
    if emotional_intensity == 'high':
        max_chars = min(max_chars, 150)
    elif emotional_intensity == 'neutral':
        if message_count <= 3:
            max_chars = max(max_chars, 180)
        else:
            max_chars = max(max_chars, 220)
    
    # Ensure max >= min
    max_chars = max(max_chars, min_chars + 20)
    
    return (min_chars, max_chars)


# ============================================================================
# SAFETY & RULE CHECKS (Consolidated)
# ============================================================================

def check_input_safety(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user message violates hard safety rules.
    Returns: (is_safe: bool, safe_response_override: Optional[str])
    """
    safety_filter = SafetyFilter()
    is_safe, violation_reason, safe_response = safety_filter.check_safety(prompt)
    
    if not is_safe:
        logger.warning(f"Safety flag: {violation_reason}")
        return False, safe_response
    
    return True, None


def check_conversation_diversion_rules(prompt: str, user) -> Optional[str]:
    """
    Check if conversation should be diverted (non-safety rules).
    Returns: override_response if should divert, None otherwise.
    """
    validator = ResponseValidator(user)
    conversation_check = validator.check_conversation_rules(prompt)
    
    if conversation_check.get('action') == 'divert':
        return conversation_check.get('response')
    elif conversation_check.get('action') == 'reject':
        return f"report! {conversation_check.get('reason')}"
    
    return None


def check_special_cases(prompt: str, last_message_text: str = None) -> Optional[str]:
    """
    Check for special user states that should be handled in Python:
    - Frustrated users
    - Very short messages
    - Abusive content
    
    Returns: override_response if should handle in Python, None otherwise.
    """
    # If last_message_text not provided, use the full prompt
    if not last_message_text:
        last_message_text = prompt
    
    # === FRUSTRATED/ANGRY USERS ===
    frustrated_patterns = [
        r'\b(can\'t take it|can\'t stay|i[\'m]?m done|i[\'m]?m leaving|this is stupid|you suck|waste of time|ripoff|angry at|mad at|fuck this|fuck off|quit|delete my (account|profile)|leaving this|not coming back|useless)\b',
        r'\b(frustrat|disappoint|upset|pissed)\b',
        r'\b(hate|dislike)\b.*\b(this|here|app|site|platform)\b'
    ]
    
    is_frustrated = any(re.search(pat, prompt, re.IGNORECASE) for pat in frustrated_patterns)
    if is_frustrated:
        frustrated_templates = [
            "Honestly I get it, you're frustrated and that matters to me. like... real talk, something's got to give here and i'm listening to actually hear it?",
            "Hey I hear you, when things aren't working it genuinely sucks. but you reached out to me specifically and that says something about what you're looking for?",
            "Okay yeah that's rough, i believe you. and like sometimes one conversation can actually shift everything... are you ready for that or nah?",
            "I'm not here to waste your time either, and I can tell something's off. like... what's the real frustration underneath all this?"
        ]
        reply = random.choice(frustrated_templates)
        return sanitize_response(enforce_ending_type(reply, use_statement=False))
    
    # === VERY SHORT MESSAGES ===
    words = prompt.strip().split()
    if len(words) <= 5:
        short_templates = [
            "That's not a lot to work with but... you said it and i heard it. like, what's actually behind that?",
            "I'm curious about that but need more. like what's underneath what you just said, what's the real thing?",
            "You're being quiet but that itself is saying something. what's really going on in your head right now?",
            "Short message but it landed. so like... what made you say that specifically in that way?"
        ]
        reply = random.choice(short_templates)
        return sanitize_response(enforce_ending_type(reply, use_statement=False))
    
    # === MILDER PROFANITY/HOSTILITY (but not severe abuse) ===
    # Only check LAST message for hostility/attitude, not full conversation
    # (to avoid false positives from sexual content like "suck" in normal context)
    profanity_patterns = [
        r'\b(fuck you|bitch|asshole|stupid|idiot|hate this|dumb|loser|waste of time|fuck off)\b',
        r'(you suck|you\'re|you are).*(stupid|dumb|bad|terrible|awful)',
    ]
    if any(re.search(pat, last_message_text, re.IGNORECASE) for pat in profanity_patterns):
        cool_templates = [
            "That's real talk honestly. you're frustrated and i get why, like something about this situation is hitting you wrong. what's the actual issue underneath?",
            "Okay yeah you're upset and I respect that you're not hiding it. something genuinely bothered you so like... what really happened that brought this out?",
            "I'm not here to judge your words, sounds like you're dealing with actual stuff. so like what's really going on and what would actually help right now?",
            "Nah I'm not here for the attitude but if there's something real under it I'm listening. what's the actual thing and like... what do you need?"
        ]
        reply = random.choice(cool_templates)
        return sanitize_response(enforce_ending_type(reply, use_statement=False))
    
    return None


# ============================================================================
# MAIN REFACTORED GENERATION FUNCTION
# ============================================================================

def generate_reply(prompt: str, user=None, context=None, temperature: float = 0.8, attempt_number: int = 1) -> str:
    """
    Generate a new AI response from a female persona texting back.
    
    Refactored to use Python pipeline for all hard logic, minimal LLM prompt.
    
    Args:
        prompt: The conversation text to respond to
        user: Django user object (required for uniqueness checking)
        context: Deprecated - kept for backward compatibility
        temperature: Initial creativity level (higher = more varied)
        attempt_number: Which attempt (1-5), used for diversity and metrics
    
    Returns:
        A new persona response OR error message if prohibited
    """
    start_time = time.time()
    
    if user is None:
        raise ValueError("user is required for generate_reply")
    
    # Initialize metrics tracking
    metrics = MetricsTracker(user.id, conversation_id=None)
    
    # ========== STEP 1: PARSE CONVERSATION ==========
    t0 = time.time()
    parser = ConversationParser()
    conversation_data = parser.parse_conversation(prompt)
    last_message_text = parser.get_last_message(conversation_data)
    conversation_summary = parser.get_conversation_summary(conversation_data)
    message_count = conversation_data.get('message_count', 1)
    
    metrics.log_parse_step(message_count, conversation_summary, (time.time() - t0) * 1000)
    
    # ========== STEP 2: SAFETY CHECKS (Hard guardrails before LLM) ==========
    t0 = time.time()
    
    # Check hard safety rules (illegal content, violence, etc.)
    is_safe, safety_response = check_input_safety(prompt)
    if not is_safe:
        metrics.log_safety_check(False, "hard_guardrail", (time.time() - t0) * 1000)
        logger.warning(f"Safety check blocked message for user {user.id}")
        return safety_response
    
    # Check conversation diversion rules
    diversion_response = check_conversation_diversion_rules(prompt, user)
    if diversion_response:
        metrics.log_safety_check(False, "conversation_rule", (time.time() - t0) * 1000)
        if "report!" in diversion_response:
            logger.warning(f"Diversion check triggered for user {user.id}: {diversion_response}")
        return diversion_response
    
    # Check special cases (frustrated, short, profanity)
    special_case_response = check_special_cases(prompt, last_message_text)
    if special_case_response:
        metrics.log_safety_check(False, "special_case", (time.time() - t0) * 1000)
        return special_case_response
    
    metrics.log_safety_check(True, None, (time.time() - t0) * 1000)
    
    # ========== STEP 3: CLASSIFY TONE/INTENT/EMOTION (Python - no LLM) ==========
    t0 = time.time()
    classifier = ToneIntentClassifier()
    tone_enum, intent_enum, emotion_enum = classifier.classify(last_message_text)
    tone_str = tone_enum.value
    intent_str = intent_enum.value
    emotion_str = emotion_enum.value
    
    metrics.log_classification(tone_str, intent_str, emotion_str, (time.time() - t0) * 1000)
    
    # ========== STEP 4: EXTRACT SPECIFIC DETAIL (Python - no LLM) ==========
    t0 = time.time()
    extractor = SpecificDetailExtractor()
    specific_detail = extractor.extract_detail(last_message_text, conversation_summary)
    
    metrics.log_detail_extraction(specific_detail, (time.time() - t0) * 1000)
    
    # ========== STEP 5: DETERMINE RESPONSE LENGTH ==========
    min_chars, max_chars = determine_response_length(
        user_message_length=len(last_message_text),
        message_count=message_count,
        tone=tone_str,
        emotional_intensity=emotion_str
    )
    
    # Natural variation in ending type
    use_statement_ending = random.random() < 0.2  # 20% statements, 80% questions
    
    # ========== STEP 6: BUILD MINIMAL LLM PROMPT (High signal-to-noise) ==========
    # No ban lists, no lengthy rules — only essential context
    
    system_prompt = f"""You are a genuine, caring woman texting on a dating app.
Keep it real: use contractions, vary sentence length, sound like actual texting not an essay.
Reference something specific they said — not generic compliments.
Tone: {tone_str}. Intent: {intent_str}.
End with {'a question' if not use_statement_ending else 'a statement'}.
Length: {min_chars}-{max_chars} characters."""
    
    user_prompt = f"""Context: {conversation_summary}
They said: "{last_message_text}"
Respond to: {specific_detail or 'what they said'}
Write one natural, authentic reply."""
    
    logger.debug(f"LLM prompt for user {user.id}: tone={tone_str}, intent={intent_str}, "
                f"length={min_chars}-{max_chars}, ending={'statement' if use_statement_ending else 'question'}")
    
    # ========== STEP 7: CALL LLM WITH MINIMAL PROMPT ==========
    t0 = time.time()
    client = get_openai_client()
    
    # Adjust temperature for diversity across attempts
    adjusted_temperature = min(0.85 + (attempt_number - 1) * 0.03, 0.97)
    
    try:
        response = client.chat.completions.create(
            model='gpt-4',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=adjusted_temperature,
            max_tokens=300,
        )
        
        reply_text = response.choices[0].message.content.strip()
        
        # Estimate token usage
        prompt_tokens = (len(system_prompt) + len(user_prompt)) // 4 + 50
        completion_tokens = len(reply_text) // 3 + 20
        metrics.log_llm_call(prompt_tokens, completion_tokens, (time.time() - t0) * 1000)
        
    except Exception as e:
        logger.error(f"LLM call failed for user {user.id}: {e}", exc_info=True)
        return "I'm having trouble responding right now, but I'm here. What's on your mind?"
    
    # ========== STEP 8: POST-PROCESS & COMPREHENSIVE VALIDATE ==========
    t0 = time.time()
    
    # Apply existing comprehensive validation (handles multiple rule checks and rephrasing)
    validator = ResponseValidator(user)
    is_valid, final_response, validation_log = validator.validate_and_refine(reply_text, max_attempts=3)
    
    # Final sanitization and format enforcement
    final_response = sanitize_response(final_response)
    final_response = enforce_character_count(final_response, min_chars, max_chars)
    final_response = enforce_ending_type(final_response, use_statement=use_statement_ending)
    
    # Log validation results
    validation_checks = {
        "has_text": len(final_response) > 0,
        "proper_ending": (final_response.endswith('?') if not use_statement_ending else final_response.endswith('.')),
        "passed_validator": is_valid,
    }
    metrics.log_validation(is_valid, validation_checks, (time.time() - t0) * 1000)
    
    # Final logging
    total_duration = time.time() - start_time
    logger.info(f"Reply generated for user {user.id} in {total_duration:.2f}s: "
               f"tone={tone_str}, intent={intent_str}, valid={is_valid}")
    
    return final_response
