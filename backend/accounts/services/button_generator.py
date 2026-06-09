"""
Button Response Generator
Generates random abstract scenario responses for intent buttons.
Uses session tracking to prevent theme repetition within user's session.
"""

import json
import logging
from django.core.cache import cache
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client lazily
_client = None

def get_openai_client():
    global _client
    if _client is None:
        try:
            _client = OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    return _client

# Define all 13 button intents with their prompts
BUTTON_INTENTS = {
    'dead': {
        'name': 'Dead',
        'prompt': (
            "Generate a random way to spark conversation with someone who isn't responding. "
            "Could be about memories together, inside jokes, something you noticed on their profile, "
            "curiosity about their day, a genuine question about their interests, or asking what they've been up to. "
            "Make it feel fresh and different each time. Keep it authentic and not pushy."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'new_match': {
        'name': 'New Match',
        'prompt': (
            "Generate a random first-conversation opener with someone new. "
            "Could be about something in their profile, a shared interest, something playful, "
            "a genuine compliment, asking about their day/weekend, or an interesting question about their hobbies. "
            "Make it feel natural and not like a copy-paste opener."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'morning_flirt': {
        'name': 'Morning Flirt',
        'prompt': (
            "Generate a random morning message. Could be about dreams they might have had, "
            "wishing them a good morning, asking how they slept, coffee/breakfast banter, "
            "missing them, playful teasing, or the day ahead. Make it feel warm, genuine, and a bit flirty."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'deep_talk': {
        'name': 'Deep Talk',
        'prompt': (
            "Generate a random deeper conversation topic. Could be about life goals, "
            "vulnerable moments, dreams and ambitions, what they value most, a meaningful experience, "
            "what they're looking for in connection, or a thoughtful question about their past. "
            "Make it feel sincere and inviting without being too heavy."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'dinner_talk': {
        'name': 'Dinner Talk',
        'prompt': (
            "Generate a random dinner conversation topic. Could be about their favorite foods, "
            "restaurants they want to try, cooking together, what they're eating, food preferences, "
            "restaurant experiences, or dinner plans. Make it feel like natural dinner-time banter."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'sensual': {
        'name': 'Sensual',
        'prompt': (
            "Generate a random sensual/flirty message. Could be about physical attraction, "
            "wanting to see them, admiring something about them, suggesting plans together, "
            "teasing touches, or suggestive conversation. Make it feel confident and sexy without being crude."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'meeting_divert': {
        'name': 'Meeting Divert',
        'prompt': (
            "Generate a message that subtly diverts from meeting up (if the conversation was heading that way). "
            "Could be about taking things slowly, wanting to get to know them better first, "
            "logistics getting complicated, needing to reschedule, or redirecting toward more conversation. "
            "Make it feel genuine and not like you're dodging."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'insist': {
        'name': 'Insist/Push',
        'prompt': (
            "Generate a message that gently insists on meeting up or moving forward. "
            "Could be about being tired of texting, wanting to meet in person to really connect, "
            "suggesting a low-pressure coffee date, expressing genuine interest, or playfully calling them out "
            "for stalling. Make it feel assertive but not aggressive."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'public_talks': {
        'name': 'Public Talks',
        'prompt': (
            "Generate a message about public/social situations or interactions. "
            "Could be about holding hands in public, PDA comfort levels, running into friends, "
            "showing each other off, where to sit together, introducing to friends, or social activities together. "
            "Make it feel natural like casual planning."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'bedroom_questions': {
        'name': 'Bedroom Questions',
        'prompt': (
            "Generate a flirty intimate question or conversation starter about physical intimacy. "
            "Could be about preferences, what turns them on, what they enjoy, desires or fantasies, "
            "asking them to describe their ideal evening, or playful sexual teasing. "
            "Make it suggestive and flirty but not explicit or crude."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'positions': {
        'name': 'Positions/Scenarios',
        'prompt': (
            "Generate a playful message about physical intimacy scenarios or positions. "
            "Could be asking what they like, suggesting something specific, describing a fantasy scenario, "
            "or teasing about trying something new. Make it descriptive, confident, and playfully sexual."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'lyrical_romance': {
        'name': 'Lyrical/Romance',
        'prompt': (
            "Generate a romantic or poetic message. Could reference song lyrics, poetry vibes, "
            "express deeper feelings, romantic fantasies, wanting them to feel special, "
            "describing how you feel about them, or painting a romantic picture. "
            "Make it feel genuine, not clichéd, and appropriately vulnerable."
        ),
        'model': 'gpt-3.5-turbo',
    },
    'vulnerability': {
        'name': 'Vulnerability',
        'prompt': (
            "Generate a vulnerable, authentic message. Could be admitting you like them more than expected, "
            "expressing a fear or insecurity, being honest about feelings, asking for reassurance, "
            "admitting anxiety about connection, or showing genuine emotional openness. "
            "Make it feel safe and real without being needy."
        ),
        'model': 'gpt-3.5-turbo',
    },
}


def generate_button_response(user_id: int, button_intent: str) -> dict:
    """
    Generate a fresh response for a button click.
    Tracks themes to avoid repeats within session.
    
    Args:
        user_id: ID of the user clicking the button
        button_intent: Button intent key (e.g., 'morning_flirt')
    
    Returns:
        dict with 'response' and 'theme' keys
        
    Raises:
        ValueError: If button_intent is invalid
        APIError: If OpenAI API fails
    """
    
    if button_intent not in BUTTON_INTENTS:
        raise ValueError(f"Unknown button intent: {button_intent}")
    
    # Get user's session data (stores used themes)
    session_key = f"user_session_{user_id}"
    session_data = cache.get(session_key, {})
    
    if not session_data:
        session_data = {'user_id': user_id, 'used_themes': {}}
    
    # Get used themes for this button in current session
    used_themes = session_data.get('used_themes', {}).get(button_intent, [])
    
    # Get the intent configuration
    intent_config = BUTTON_INTENTS[button_intent]
    prompt = intent_config['prompt']
    
    # If they've used this button before in session, ask AI to avoid those themes
    if used_themes:
        diversity_instruction = (
            f"\n\nIMPORTANT: In this conversation session, the following themes have already been used for this button: {', '.join(used_themes)}. "
            f"Generate something COMPLETELY DIFFERENT. Avoid these topics entirely."
        )
        prompt += diversity_instruction
    
    try:
        # Generate with OpenAI
        response = get_openai_client().chat.completions.create(
            model=intent_config['model'],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are generating fresh, random conversation scenarios for dating interactions. "
                        "Each response should end with a question to keep conversation flowing. "
                        "Be authentic, avoid clichés, avoid AI-like language. "
                        "Response should be 1-3 sentences max (50-100 characters). "
                        "Sound like a real person texting, not a chatbot."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.95,  # High randomness for variety
            max_tokens=100,
        )
        
        result = response.choices[0].message.content.strip()
        
        # Quality validation
        result = ensure_ends_with_question(result)
        result = validate_character_voice(result)
        
        # Extract the main theme/topic
        theme = extract_theme(result)
        
        # Track this theme in session (prevent repeats)
        if button_intent not in session_data['used_themes']:
            session_data['used_themes'][button_intent] = []
        
        session_data['used_themes'][button_intent].append(theme)
        
        # Save back to cache (expires in 24 hours)
        cache.set(session_key, session_data, 86400)
        
        logger.info(
            f"Generated button response for user {user_id}, intent: {button_intent}, "
            f"theme: {theme}, session themes: {len(session_data['used_themes'].get(button_intent, []))}"
        )
        
        return {
            'response': result,
            'theme': theme,
            'button_intent': button_intent,
            'session_themes': session_data['used_themes'].get(button_intent, [])
        }
    
    except RateLimitError:
        logger.error(f"OpenAI rate limit exceeded for user {user_id}")
        raise APIError("API rate limit exceeded. Please try again in a moment.")
    
    except APIConnectionError:
        logger.error(f"OpenAI API connection error for user {user_id}")
        raise APIError("Connection error with AI service. Please try again.")
    
    except APIError as e:
        logger.error(f"OpenAI API error for user {user_id}: {str(e)}")
        raise APIError(f"AI service error: {str(e)}")


def ensure_ends_with_question(text: str) -> str:
    """
    Ensure response ends with a question mark.
    Critical for keeping conversation flowing.
    
    Args:
        text: Text to validate
    
    Returns:
        Text ending with a question mark
    """
    text = text.strip()
    
    if not text:
        return "What's on your mind?"
    
    # Already ends with question mark
    if text.endswith('?'):
        return text
    
    # Replace period with question if exists
    if text.endswith('.'):
        return text[:-1] + '?'
    
    # No punctuation - add question mark
    if text[-1].isalnum():
        return text + '?'
    
    return text


def validate_character_voice(text: str) -> str:
    """
    Ensure response sounds natural and authentic.
    Remove AI signatures, overly formal language, clichés.
    
    Args:
        text: Text to validate
    
    Returns:
        Cleaned text
    """
    
    # Remove common AI phrases
    ai_phrases = [
        "As an AI",
        "I'm an AI",
        "As an assistant",
        "I can help",
        "Feel free to",
        "Let me know",
        "I'd be happy to",
        "I appreciate",
        "I understand",
        "I'm here to",
        "I'm designed to",
        "Here's what I think",
        "In my opinion",
        "I believe",
        "I would say",
    ]
    
    for phrase in ai_phrases:
        if phrase.lower() in text.lower():
            # Try to remove cleanly
            text = text.replace(phrase, "")
            text = text.replace(phrase.lower(), "")
    
    # Remove repeated words/spaces
    text = ' '.join(text.split())
    
    # Remove leading/trailing spaces and special characters
    text = text.strip()
    
    return text


def extract_theme(text: str) -> str:
    """
    Extract main theme/topic from response for session tracking.
    Used to prevent repeating similar scenarios within same session.
    
    Args:
        text: Generated response text
    
    Returns:
        Theme string (first 3-5 words or key topic)
    """
    
    # Common theme keywords to look for
    theme_keywords = {
        'coffee': ['coffee', 'cafe', 'brew', 'morning drink'],
        'dreams': ['dream', 'dreamed', 'sleep'],
        'work': ['work', 'job', 'busy', 'day'],
        'food': ['food', 'eat', 'dinner', 'lunch', 'breakfast', 'cook'],
        'activity': ['movie', 'hike', 'walk', 'explore', 'adventure'],
        'intimate': ['kiss', 'touch', 'close', 'tonight', 'bed', 'cuddle'],
        'future': ['weekend', 'next', 'plans', 'soon', 'when'],
        'feelings': ['miss', 'like', 'love', 'feel', 'heart', 'special'],
        'physical': ['look', 'think you', 'sexy', 'beautiful', 'attractive'],
        'teasing': ['tease', 'play', 'bet', 'challenge', 'funny'],
    }
    
    text_lower = text.lower()
    
    # Check for theme keywords
    for theme, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return theme
    
    # Fallback: extract first 2-3 words
    words = text.split()[:3]
    theme = ' '.join(words).lower()
    
    # Remove common words
    common_words = ['what', 'when', 'where', 'how', 'do', 'you', 'i', 'the', 'a', 'an']
    theme_words = [w for w in theme.split() if w not in common_words]
    
    if theme_words:
        return theme_words[0]
    
    return 'other'


def get_user_session_info(user_id: int) -> dict:
    """
    Get current session information for a user.
    Useful for debugging and analytics.
    
    Args:
        user_id: ID of the user
    
    Returns:
        Session data dict
    """
    session_key = f"user_session_{user_id}"
    session_data = cache.get(session_key, {})
    return session_data


def reset_user_session(user_id: int) -> None:
    """
    Reset user's session (e.g., start of new day or explicit reset).
    Clears all tracked themes.
    
    Args:
        user_id: ID of the user
    """
    session_key = f"user_session_{user_id}"
    cache.delete(session_key)
    logger.info(f"Reset session for user {user_id}")


def get_all_button_intents() -> dict:
    """
    Get all available button intents with metadata.
    Useful for frontend to display button options.
    
    Returns:
        Dictionary of all button intents with names
    """
    return {
        key: {'name': config['name'], 'key': key}
        for key, config in BUTTON_INTENTS.items()
    }
