"""
ReplyPipeline: Main orchestrator for the refactored reply generation system.
Coordinates: parsing → classification → extraction → safety → LLM call → validation.
All hard logic runs in Python; LLM is only for final phrasing.
"""
import time
import logging
from typing import Optional, Tuple

from accounts.services.conversation_context import ConversationContext
from accounts.services.tone_intent_classifier import ToneIntentClassifier
from accounts.services.specific_detail_extractor import SpecificDetailExtractor
from accounts.services.safety_filter import SafetyFilter
from accounts.services.metrics_tracker import MetricsTracker, ResponseOutcome
from accounts.services.conversation_parser import ConversationParser
from accounts.services.response_validator import ResponseValidator


logger = logging.getLogger(__name__)


class ReplyPipeline:
    """
    Refactored reply generation pipeline.
    
    Flow:
    1. Parse conversation → extract summary, message count
    2. Classify tone/intent/emotion (Python, no LLM)
    3. Extract specific detail to reference
    4. Check safety (hard guardrails, no LLM)
    5. If flagged: return safe response, skip LLM
    6. If safe: call LLM with minimal prompt
    7. Post-process and validate
    8. Return final reply
    """
    
    def __init__(self, user, conversation_id: Optional[int] = None):
        self.user = user
        self.conversation_id = conversation_id
        self.classifier = ToneIntentClassifier()
        self.extractor = SpecificDetailExtractor()
        self.safety = SafetyFilter()
        self.metrics = MetricsTracker(user.id, conversation_id or 0)
        self.parser = ConversationParser()
    
    def generate_reply(self, user_message: str) -> str:
        """
        Main entry point: Generate a single, high-quality reply to user message.
        
        Returns: Final reply text (or safe fallback if flagged)
        """
        start_time = time.time()
        
        try:
            # === STEP 1: PARSE CONVERSATION ===
            t0 = time.time()
            context = self._parse_conversation(user_message)
            t1 = time.time()
            self.metrics.log_parse_step(context.message_count, context.conversation_summary, (t1-t0)*1000)
            
            # === STEP 2: CLASSIFY TONE/INTENT/EMOTION ===
            t0 = time.time()
            tone, intent, emotion = self.classifier.classify(user_message)
            context.tone = tone.value
            context.intent = intent.value
            context.emotion_level = emotion.value
            t1 = time.time()
            self.metrics.log_classification(context.tone, context.intent, context.emotion_level, (t1-t0)*1000)
            
            # === STEP 3: EXTRACT SPECIFIC DETAIL ===
            t0 = time.time()
            detail = self.extractor.extract_detail(user_message, context.conversation_summary)
            context.specific_reference = detail
            t1 = time.time()
            self.metrics.log_detail_extraction(detail, (t1-t0)*1000)
            
            # === STEP 4: SAFETY CHECK (INPUT GUARDRAILS) ===
            t0 = time.time()
            is_safe, violation, safe_response = self.safety.check_safety(user_message)
            t1 = time.time()
            self.metrics.log_safety_check(is_safe, violation, (t1-t0)*1000)
            
            if not is_safe:
                # Safety-flagged: respond with safe message, skip LLM
                context.safety_flag = violation
                context.safety_response = safe_response
                logger.warning(f"Safety flag for user {self.user.id}: {violation}")
                return safe_response
            
            # === STEP 5: CALL LLM WITH MINIMAL PROMPT ===
            t0 = time.time()
            reply = self._call_llm_minimal_prompt(context)
            t1 = time.time()
            
            # Estimate tokens (rough: 1 token ≈ 4 chars for input, 1 token ≈ 3 chars for output)
            prompt_tokens = (len(context.conversation_summary) + len(user_message)) // 4 + 50
            completion_tokens = len(reply) // 3 + 20
            self.metrics.log_llm_call(prompt_tokens, completion_tokens, (t1-t0)*1000)
            
            # === STEP 6: POST-PROCESS & VALIDATE ===
            t0 = time.time()
            final_reply = self._post_process_and_validate(reply, context)
            t1 = time.time()
            
            validation_checks = {
                "has_text": len(final_reply) > 0,
                "proper_length": context.min_chars <= len(final_reply) <= context.max_chars,
                "proper_ending": final_reply.endswith(('?', '.', '!')) if context.should_end_with_question else True,
                "no_profanity": not any(bad in final_reply.lower() for bad in ["fuck", "shit"]),  # Adjust as needed
            }
            is_valid = all(validation_checks.values())
            self.metrics.log_validation(is_valid, validation_checks, (t1-t0)*1000)
            
            # Log total duration
            total_duration = time.time() - start_time
            logger.info(f"Reply generation complete for user {self.user.id} in {total_duration:.2f}s")
            
            return final_reply
        
        except Exception as e:
            logger.error(f"Error in reply pipeline: {e}", exc_info=True)
            # Fallback response
            return "I'm having trouble responding right now, but I'm here. What's on your mind?"
    
    def _parse_conversation(self, user_message: str) -> ConversationContext:
        """Parse conversation and build context."""
        # TODO: Integrate with existing ConversationParser to get actual conversation
        # For now, create a minimal context
        
        context = ConversationContext(
            user_id=self.user.id,
            conversation_id=self.conversation_id,
            message_count=1,  # TODO: Get real count from parser
            last_user_message=user_message,
            conversation_summary=f"User said: {user_message[:50]}...",  # TODO: Get real summary
            user_message_length=len(user_message),
        )
        
        # Determine response length based on message length
        context.min_chars, context.max_chars = self._determine_response_length(user_message, context)
        
        return context
    
    def _determine_response_length(self, user_message: str, context: ConversationContext) -> Tuple[int, int]:
        """Determine target character range for response."""
        msg_len = len(user_message)
        
        # Mirror their energy
        if msg_len < 50:
            return 80, 150  # They're brief, keep response quick
        elif msg_len < 150:
            return 100, 200  # Normal length
        else:
            return 150, 250  # They're long, allow more depth
    
    def _call_llm_minimal_prompt(self, context: ConversationContext) -> str:
        """
        Call LLM with ultra-minimal, high-signal prompt.
        No ban lists, no lengthy rules — only essential context.
        """
        from accounts.openai_service import get_openai_client
        
        client = get_openai_client()
        
        # === MINIMAL SYSTEM PROMPT ===
        system_prompt = (
            f"You are a genuine, caring woman responding in a dating app chat. "
            f"Sound like real texting, not an essay. Use contractions and vary sentence length. "
            f"Reference something specific from what they just said, not generic observations."
        )
        
        # === MINIMAL USER PROMPT ===
        # Inject only the dynamic fields (tone, length, detail, last message)
        user_prompt = (
            f"Tone: {context.tone}\n"
            f"Length: {context.min_chars}-{context.max_chars} characters\n"
            f"Reference: {context.specific_reference or 'what they said'}\n"
            f"End with: {'question (?)' if context.should_end_with_question else 'statement'}\n"
            f"\n"
            f"Context: {context.conversation_summary}\n"
            f"They said: \"{context.last_user_message}\"\n"
            f"\n"
            f"Write one natural, authentic reply."
        )
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.85,
            max_tokens=300,
        )
        
        return response.choices[0].message.content.strip()
    
    def _post_process_and_validate(self, reply: str, context: ConversationContext) -> str:
        """
        Post-process reply to ensure quality standards.
        Capitalize, ensure punctuation, check length, validate format.
        """
        from accounts.services.ai_generation import sanitize_response, enforce_ending_type
        
        # Apply existing post-processing functions
        reply = sanitize_response(reply)
        reply = enforce_ending_type(reply, use_statement=not context.should_end_with_question)
        
        # Ensure length constraints
        if len(reply) < context.min_chars - 20:
            # Too short - let it be for now (avoid forcing filler)
            logger.debug(f"Reply shorter than target: {len(reply)} vs {context.min_chars} min")
        
        if len(reply) > context.max_chars + 20:
            # Too long - truncate at sentence boundary
            for punct in ['. ', '? ', '! ']:
                idx = reply.rfind(punct, 0, context.max_chars)
                if idx > context.min_chars:
                    reply = reply[:idx+1]
                    break
        
        return reply
