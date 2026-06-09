"""
Intent Detector and Context-Aware Response Generator
Analyzes pasted conversations to extract context and generate authentic responses.
Used for LEFT side of the button system (flowing conversations).
"""

import json
import logging
from typing import Dict, Optional
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from django.conf import settings
from .button_generator import (
    ensure_ends_with_question,
    validate_character_voice,
    get_openai_client,
)

logger = logging.getLogger(__name__)

# Define conversation stages and tones
CONVERSATION_STAGES = {
    'new': 'Just started matching/talking',
    'growing': 'Getting to know each other, building connection',
    'established': 'Comfortable, ongoing conversations',
    'intimate': 'Close connection, deeper topics',
}

CONVERSATION_TONES = {
    'flirty': 'Light, playful, sexually charged',
    'serious': 'Deep, thoughtful, sincere',
    'playful': 'Fun, joking, lighthearted',
    'vulnerable': 'Open, honest, emotional',
    'testing': 'Curious, asking questions, feeling out',
    'casual': 'Relaxed, natural, everyday',
}

CONVERSATION_TOPICS = {
    'general': 'Everyday conversation, getting to know',
    'food': 'Food, restaurants, cooking, meals',
    'work': 'Career, work, professional life',
    'interests': 'Hobbies, activities, interests',
    'relationship': 'Relationship, connection, feelings',
    'intimacy': 'Physical attraction, sexual topics',
    'future': 'Plans, meeting up, next steps',
    'personal': 'Family, background, personal stories',
}

ENERGY_LEVELS = {
    'low': 'Slow, cautious, taking time',
    'medium': 'Normal pace, balanced engagement',
    'high': 'Fast-paced, excited, enthusiastic',
}


def detect_intent(conversation: str) -> Dict[str, str]:
    """
    Analyze a pasted conversation to extract context.
    
    Detects:
    - Main topic (what the conversation is about)
    - Conversation tone (how it's being communicated)
    - Relationship stage (how well they know each other)
    - Energy level (pace and enthusiasm)
    
    Args:
        conversation: Full conversation text (can be multi-message)
    
    Returns:
        dict with keys: topic, tone, stage, energy
        
    Raises:
        ValueError: If conversation is too short
        APIError: If OpenAI API fails
    """
    
    if not conversation or len(conversation.strip()) < 20:
        raise ValueError("Conversation must be at least 20 characters")
    
    # Truncate if too long (save API calls)
    if len(conversation) > 3000:
        conversation = conversation[-3000:]  # Use last 3000 chars
    
    analysis_prompt = f"""Analyze this dating conversation and provide brief analysis.

CONVERSATION:
{conversation}

Based on this conversation, identify:
1. TOPIC: What's the main subject? (general, food, work, interests, relationship, intimacy, future, personal)
2. TONE: How is it being communicated? (flirty, serious, playful, vulnerable, testing, casual)
3. STAGE: What's the relationship stage? (new, growing, established, intimate)
4. ENERGY: What's the pace/enthusiasm? (low, medium, high)

Respond ONLY with valid JSON (no other text):
{{"topic": "...", "tone": "...", "stage": "...", "energy": "..."}}

Use ONLY the options provided above. Be concise."""
    
    try:
        response = get_openai_client().chat.completions.create(
            model='gpt-4-mini',
            messages=[
                {
                    "role": "system",
                    "content": "You are analyzing dating conversations. Respond ONLY in valid JSON format."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            temperature=0.3,  # Low temperature for consistency
            max_tokens=100,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            intent_data = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, return defaults
            logger.warning(f"Failed to parse intent JSON: {response_text}")
            intent_data = {
                "topic": "general",
                "tone": "flirty",
                "stage": "growing",
                "energy": "medium"
            }
        
        # Validate keys are present
        required_keys = ['topic', 'tone', 'stage', 'energy']
        for key in required_keys:
            if key not in intent_data:
                intent_data[key] = {
                    'topic': 'general',
                    'tone': 'flirty',
                    'stage': 'growing',
                    'energy': 'medium'
                }.get(key, 'unknown')
        
        logger.info(
            f"Intent detected - topic: {intent_data['topic']}, "
            f"tone: {intent_data['tone']}, stage: {intent_data['stage']}, "
            f"energy: {intent_data['energy']}"
        )
        
        return intent_data
    
    except RateLimitError:
        logger.error("OpenAI rate limit exceeded during intent detection")
        raise APIError("API rate limit exceeded. Please try again in a moment.")
    
    except APIConnectionError:
        logger.error("OpenAI API connection error during intent detection")
        raise APIError("Connection error with AI service. Please try again.")
    
    except APIError as e:
        logger.error(f"OpenAI API error during intent detection: {str(e)}")
        raise APIError(f"AI service error: {str(e)}")


def generate_context_aware_response(
    conversation: str,
    intent_data: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate an authentic response that matches the conversation's context.
    Used for LEFT side (pasted conversation) generation.
    
    If intent_data not provided, will analyze conversation first.
    
    Args:
        conversation: Full conversation text to respond to
        intent_data: Optional dict with topic, tone, stage, energy (from detect_intent)
    
    Returns:
        Generated response text (ends with question)
        
    Raises:
        ValueError: If conversation is too short
        APIError: If OpenAI API fails
    """
    
    if not conversation or len(conversation.strip()) < 20:
        raise ValueError("Conversation must be at least 20 characters")
    
    # Analyze intent if not provided
    if intent_data is None:
        intent_data = detect_intent(conversation)
    
    # Build context-aware system prompt
    system_prompt = f"""You are generating an authentic response in a dating conversation.

CONVERSATION CONTEXT:
- Topic: {intent_data.get('topic', 'general')} ({CONVERSATION_TOPICS.get(intent_data.get('topic', 'general'), '')})
- Tone: {intent_data.get('tone', 'flirty')} ({CONVERSATION_TONES.get(intent_data.get('tone', 'flirty'), '')})
- Relationship Stage: {intent_data.get('stage', 'growing')} ({CONVERSATION_STAGES.get(intent_data.get('stage', 'growing'), '')})
- Energy Level: {intent_data.get('energy', 'medium')} ({ENERGY_LEVELS.get(intent_data.get('energy', 'medium'), '')})

YOUR RESPONSE SHOULD:
1. Match the conversation's existing tone and energy
2. Continue the topic naturally
3. End with a genuine question to keep conversation flowing
4. Be authentic and human (not AI-like)
5. Be 1-3 sentences max (50-150 characters)
6. Sound like a real person texting, not a chatbot
7. Match the established relationship stage
8. Avoid clichés and generic phrases"""

    generation_prompt = f"""Here's the conversation so far:

{conversation}

Generate the next message as if continuing this conversation naturally. 
Response should feel like the next logical message from someone interested in this person."""
    
    try:
        response = get_openai_client().chat.completions.create(
            model='gpt-4-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": generation_prompt}
            ],
            temperature=0.8,  # Some randomness but coherent
            max_tokens=150,
        )
        
        result = response.choices[0].message.content.strip()
        
        # Quality validation
        result = ensure_ends_with_question(result)
        result = validate_character_voice(result)
        
        logger.info(
            f"Generated context-aware response - "
            f"topic: {intent_data.get('topic')}, "
            f"tone: {intent_data.get('tone')}, "
            f"stage: {intent_data.get('stage')}"
        )
        
        return result
    
    except RateLimitError:
        logger.error("OpenAI rate limit exceeded during response generation")
        raise APIError("API rate limit exceeded. Please try again in a moment.")
    
    except APIConnectionError:
        logger.error("OpenAI API connection error during response generation")
        raise APIError("Connection error with AI service. Please try again.")
    
    except APIError as e:
        logger.error(f"OpenAI API error during response generation: {str(e)}")
        raise APIError(f"AI service error: {str(e)}")


def extract_conversation_summary(conversation: str) -> Dict[str, any]:
    """
    Extract basic statistics and summary from conversation.
    Useful for analytics and debugging.
    
    Args:
        conversation: Conversation text
    
    Returns:
        dict with: message_count, char_count, avg_message_length, has_question, last_message
    """
    
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    
    return {
        'message_count': len(lines),
        'char_count': len(conversation),
        'avg_message_length': len(conversation) // max(len(lines), 1),
        'has_question': '?' in conversation,
        'last_message': lines[-1] if lines else '',
        'first_message': lines[0] if lines else '',
    }


def validate_conversation_input(conversation: str) -> tuple[bool, str]:
    """
    Validate that pasted conversation is valid for analysis.
    
    Args:
        conversation: Raw conversation text
    
    Returns:
        tuple of (is_valid: bool, message: str)
    """
    
    if not conversation or not conversation.strip():
        return False, "Conversation cannot be empty"
    
    if len(conversation.strip()) < 20:
        return False, "Conversation must be at least 20 characters"
    
    if len(conversation) > 10000:
        return False, "Conversation is too long (max 10000 characters). Please paste a shorter section."
    
    # Check for minimum message count (at least 2 messages for context)
    messages = [l.strip() for l in conversation.split('\n') if l.strip()]
    if len(messages) < 2:
        return False, "Please paste at least 2 messages from the conversation"
    
    return True, "Valid conversation"


def get_intent_descriptions() -> Dict[str, Dict[str, str]]:
    """
    Get human-readable descriptions of all intent categories.
    Useful for documentation and frontend display.
    
    Returns:
        dict with topic, tone, stage, energy descriptions
    """
    return {
        'topics': CONVERSATION_TOPICS,
        'tones': CONVERSATION_TONES,
        'stages': CONVERSATION_STAGES,
        'energies': ENERGY_LEVELS,
    }


def compare_intents(intent1: Dict[str, str], intent2: Dict[str, str]) -> Dict[str, bool]:
    """
    Compare two intent dictionaries to find differences.
    Useful for testing or analyzing conversation changes.
    
    Args:
        intent1: First intent dict
        intent2: Second intent dict
    
    Returns:
        dict showing which keys match/differ
    """
    
    return {
        'topic_match': intent1.get('topic') == intent2.get('topic'),
        'tone_match': intent1.get('tone') == intent2.get('tone'),
        'stage_match': intent1.get('stage') == intent2.get('stage'),
        'energy_match': intent1.get('energy') == intent2.get('energy'),
        'all_match': (
            intent1.get('topic') == intent2.get('topic') and
            intent1.get('tone') == intent2.get('tone') and
            intent1.get('stage') == intent2.get('stage') and
            intent1.get('energy') == intent2.get('energy')
        ),
    }
