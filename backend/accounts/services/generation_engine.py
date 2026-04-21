"""
AI Response Generation Engine
Uses all 4 variation layers to ensure truly unique responses
"""

from openai import OpenAI
from accounts.services.ngram_service import check_ngrams, log_ngrams
from accounts.services.structure_service import (
    get_available_structures,
    get_structure_instruction
)
from accounts.services.tone_service import get_available_tones
from accounts.services.vocab_service import get_available_words, log_used_words
from accounts.services.context_detector import detect_context_triggers
from accounts.models import ResponseLog, ConversationLog
import random

# Use OpenAI for now - can switch to Ollama later
client = OpenAI()

MAX_REGENERATION_ATTEMPTS = 5

def build_system_prompt(
    structure: str,
    tone: str,
    available_words: dict,
    forbidden_starters: list,
    context_triggers: list,
    rejection_reasons: list = None
) -> str:

    prompt = """You are a sophisticated AI generating natural, flirty responses for a dating app.

RESPONSE REQUIREMENTS:
- Minimum 140 characters, maximum 180 characters
- MUST end with a question mark (?)
- Use the specified structure and tone
- Never repeat forbidden question starters

AVAILABLE VOCABULARY POOLS (use sparingly):
Attraction words: {attraction_words}
Teasing words: {teasing_words}
Feeling words: {feeling_words}

FORBIDDEN QUESTION STARTERS THIS REPLY:
{forbidden_starters}

RESPONSE STRUCTURE: {structure_desc}
TONE: {tone}
""".format(
        structure_desc=get_structure_instruction(structure),
        tone=tone,
        attraction_words=', '.join(available_words.get('attraction', [])),
        teasing_words=', '.join(available_words.get('teasing', [])),
        feeling_words=', '.join(available_words.get('feeling', [])),
        forbidden_starters=', '.join(forbidden_starters)
    )

    # Add context trigger instructions
    if context_triggers:
        prompt += f"""
CONTEXT TRIGGERS DETECTED: {', '.join(context_triggers)}
Apply contextual flirt anchoring for these triggers.
Use specific sensory details. Never generic responses.
"""

    # Add rejection reasons if regenerating
    if rejection_reasons:
        prompt += f"""
PREVIOUS RESPONSE REJECTED BECAUSE:
{chr(10).join(rejection_reasons)}

Rewrite completely avoiding all of the above.
"""

    return prompt

def generate_response(
    conversation_id: int,
    user_id: str,
    messages: list,
    user_message: str
) -> dict:

    conv = ConversationLog.objects.get(id=conversation_id)
    current_reply = conv.reply_count + 1

    # Get available options from all 4 layers
    available_structures = get_available_structures(conversation_id)
    available_tones = get_available_tones(conversation_id)
    available_words = get_available_words(user_id, current_reply)

    # Detect context triggers in user message
    context_triggers = detect_context_triggers(user_message)

    # Get last used question starter
    last_response = ResponseLog.objects.filter(
        conversation_id=conversation_id
    ).order_by('-reply_number').first()

    forbidden_starters = []
    if last_response:
        forbidden_starters = [last_response.question_starter]

    rejection_reasons = []

    for attempt in range(MAX_REGENERATION_ATTEMPTS):
        # Pick structure and tone
        structure = random.choice(available_structures)
        tone = random.choice(available_tones)

        system_prompt = build_system_prompt(
            structure=structure,
            tone=tone,
            available_words=available_words,
            forbidden_starters=forbidden_starters,
            context_triggers=context_triggers,
            rejection_reasons=rejection_reasons if attempt > 0 else None
        )

        try:
            response = client.chat.completions.create(
                model='gpt-4',
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                    {"role": "user", "content": user_message}
                ],
                temperature=0.8,
                max_tokens=300,
            )

            response_text = response.choices[0].message.content.strip()

            # Run all 4 layer checks
            ngram_check = check_ngrams(user_id, response_text)
            length_ok = len(response_text) >= 140

            rejection_reasons = []

            if not ngram_check["passed"]:
                rejection_reasons.append(
                    f"Trigrams already used: {', '.join(ngram_check['violations'])}"
                )

            if not length_ok:
                rejection_reasons.append(
                    "Response too short — minimum 140 characters"
                )

            if rejection_reasons:
                # Remove used structure/tone from options
                if structure in available_structures:
                    available_structures.remove(structure)
                if tone in available_tones:
                    available_tones.remove(tone)
                continue

            # All checks passed — log everything
            log_ngrams(user_id, response_text)
            log_used_words(user_id, response_text, current_reply)

            ResponseLog.objects.create(
                conversation_id=conversation_id,
                reply_number=current_reply,
                response_text=response_text,
                structure_used=structure,
                tone_used=tone,
                question_starter=_extract_question_starter(response_text)
            )

            conv.reply_count = current_reply
            conv.save()

            return {
                "response": response_text,
                "structure": structure,
                "tone": tone,
                "attempts": attempt + 1
            }

        except Exception as e:
            rejection_reasons.append(f"API Error: {str(e)}")
            continue

    # Fallback after max attempts
    return {
        "response": "Something about this conversation has me intrigued... what made you decide to reach out right now?",
        "structure": "A",
        "tone": "curious",
        "attempts": MAX_REGENERATION_ATTEMPTS,
        "warning": "Max attempts reached — sent fallback response"
    }

def _extract_question_starter(text: str) -> str:
    """Extract the first two words of the final question"""
    import re
    questions = re.findall(r'[.!…]\s*([^?]+\?)', text)
    if questions:
        words = questions[-1].strip().split()[:2]
        return ' '.join(words).lower()
    return ''