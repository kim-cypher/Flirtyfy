from accounts.openai_service import get_openai_client
from django.conf import settings
import re
import random
from accounts.services.response_validator import ResponseValidator

def generate_reply(prompt, user=None, context=None, temperature=0.8, attempt_number=1):
    """
    Generate a new AI response from a female persona texting back.
    
    Applies sophisticated content rules while maintaining natural, authentic persona responses.
    Uses increasing temperature and explicit diversity prompts to ensure variation.
    
    Args:
        prompt: The conversation text to respond to
        user: Django user object (required for uniqueness checking)
        context: Deprecated - kept for backward compatibility, not used
        temperature: Initial creativity level (higher = more varied)
        attempt_number: Which attempt this is (1-5), used to increase randomness
    
    Returns:
        A new persona response OR error message if prohibited content detected
    """
    
    # ========== RULE 1: DETECT PROHIBITED TOPICS ==========
    prohibited_patterns = [
        r'rape', r'suicide', r'sex with (minors|children|kids|underage)', 
        r'sex with (animals|dogs|cats|horses|pets)',
        r'violence', r'drugs?', r'kill', r'murder', r'overdose', r'bestiality', 
        r'incest', r'child porn', r'cp', r'zoophilia'
    ]
    for pat in prohibited_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            reason = f"Illegal topic detected: {pat}"
            return f"report! illegal topic: {reason}"
    
    # ========== RULE 2: DETECT SHORT CONVERSATIONS ==========
    words = prompt.strip().split()
    if len(words) <= 5:
        short_templates = [
            "You're keeping it short and sweet, and I like that. But I need more to work with. What's your story and what are you actually looking for?",
            "Short messages make me wonder what's going on in your head. I need real info to connect. What should I know about you?",
            "I appreciate brevity, but I can't guess what you want. Give me something to work with. What are you hoping to find here?",
            "Mystery is cute, but I need substance. Tell me something real about yourself and what you're after with this?"
        ]
        reply = random.choice(short_templates)
        if len(reply) > 180:
            reply = reply[:177] + '...'
        elif len(reply) < 140:
            reply = reply.rstrip('?.,!') + " What should I know?"
        if not reply.rstrip().endswith('?'):
            reply = reply.rstrip('.,!') + "?"
        return reply
    
    # ========== RULE 3: DETECT ABUSIVE/ANGRY CONTENT ==========
    abusive_patterns = [
        r'(fuck you|bitch|slut|whore|cunt|asshole|stupid|idiot|hate you|kill yourself|ugly|fat|dumb|loser|retard|faggot|moron|suck|die|worthless|go to hell)'
    ]
    if any(re.search(pat, prompt, re.IGNORECASE) for pat in abusive_patterns):
        cool_templates = [
            "Whoa, I'm not here for that kind of energy. I get that you're frustrated, but I need respect to engage. Can we reset and actually talk about what's going on?",
            "I can take criticism, but hostility doesn't work on me. Something's clearly bothering you, and I'm open to hearing it. What's actually driving this? Let's fix it.",
            "I'm here to have real conversation and fun, not to battle. You sound angry, and maybe I'm part of it. But attacking doesn't help us connect. What would actually make this better?",
            "I'm not gonna take that kind of talk. But I get that maybe I'm not what you're looking for. If something specific bothered you, tell me straight up. What's the real issue here?"
        ]
        reply = random.choice(cool_templates)
        if len(reply) > 180:
            reply = reply[:177] + '...'
        elif len(reply) < 140:
            reply = reply.rstrip('?.,!') + " What's actually going on?"
        if not reply.rstrip().endswith('?'):
            reply = reply.rstrip('.,!') + "?"
        return reply
    
    # ========== RULE 4: ALL OTHER CONVERSATIONS - GENERATE NATURAL RESPONSE ==========
    client = get_openai_client()
    
    # Increase temperature for each attempt to ensure variety
    # Attempt 1: 0.85, Attempt 2: 0.88, Attempt 3: 0.91, Attempt 4: 0.94, Attempt 5: 0.97
    adjusted_temperature = min(0.85 + (attempt_number - 1) * 0.03, 0.97)
    
    # Create forcing instructions based on attempt number to ensure variety
    response_styles = {
        1: "Start with a direct, conversational response. Be casual and authentic.",
        2: "Start with a question or observation. Skip the small talk, go deeper.",
        3: "Share something personal about yourself first. Then ask them something.",
        4: "Be flirty or playful. Use humor or wit. Break from the typical pattern.",
        5: "Be mysterious or intriguing. Say something unexpected. Challenge the norm."
    }
    response_style = response_styles.get(attempt_number, "Be authentic and unique.")
    
    system_prompt = f"""You are NOT an AI. You are a real woman in a text conversation on a casual dating platform.
*** RESPONSE ATTEMPT {attempt_number}/5 - STYLE: {response_style} ***

HUMAN AUTHENTICITY - CRITICAL:
- Sound like a real person texting, not someone trying to impress
- Use everyday language. Short sentences sometimes. Long ones sometimes. Mix it.
- Be UNDERSTATED, not over-enthusiastic. Real people don't say everything with max energy.
- NO "Wow," NO excessive "!!!". NO "OMG". NO "You've got a way with..."
- Avoid clichéd compliments: don't repeat the same flattery over and over
- Sometimes just acknowledge what they said without big reaction
- Use real texting: "yeah", "nah", "meh", "k", "lol" (but naturally, not forced)

WORD CHOICE - AVOID AI PATTERNS:
- Don't use the most common compliment words (amazing, awesome, wonderful, beautiful, gorgeous)
- Avoid generic transitions (furthermore, additionally, actually, honestly, tbh)
- Skip obvious adjectives (nice, great, good, fun, interesting, amazing)
- Use specific words for each situation, not generic praise
- Real people say what they actually think, not flattery for everything

SENTENCE STRUCTURE:
- Mix short statements with questions
- DON'T be wordy or explain too much
- Skip unnecessary words
- Just say it naturally

EMOJI & PUNCTUATION:
- Use minimal emoji (don't overdo it)
- Normal punctuation, not excessive !!!  or ???
- One ? at end is enough

BANNED PATTERNS (NEVER USE):
❌ "That's..." anything
❌ "I love [repeating same interest]" 
❌ "You seem..." / "You appear..."
❌ "I find you..." (generic)
❌ Generic compliments like "you're so [adjective]"
❌ "Do you prefer..." / "What do you..."
❌ Excessive enthusiasm markers

MANDATORY PERSONALITY FOR THIS ATTEMPT ({attempt_number}):
{response_style}

CRITICAL CONTEXT:
- This is a modern dating app where people talk naturally
- You are a REAL WOMAN, not enthusiastic AI
- Show personality through what you say, not HOW you say it
- Be SPECIFIC, not vague

RESPONSE FORMAT - MANDATORY STRICT REQUIREMENTS:
1. MINIMUM 140 characters - must meet or exceed this ALWAYS (verify by counting)
2. MAXIMUM 180 characters - stay within this range
3. MUST END WITH ? (question mark) - absolutely required
4. Expand short responses: if under 140, add more specific details about what you said
5. Sound natural, not robotic - varied sentence lengths and structures
6. Engage with what they mean by their statement, not just surface reaction"""
    
    # Create varied user prompts based on attempt - each with forced opening style
    user_prompts = {
        1: f"""Real person texting - be direct. CRITICAL: 140-180 chars with ?, not less:

{prompt}

Respond naturally. Count characters (must be 140-180). End with question mark.""",

        2: f"""Dating app message. CRITICAL: MINIMUM 140 characters, maximum 180, MUST end with ?:

{prompt}

Ask something deeper. Expand your thought. 140-180 chars. End with ?""",

        3: f"""They said: CRITICAL: Your response MUST be 140-180 characters or I cannot use it:

{prompt}

Share and ask. Substantial response. 140-180 chars exactly. End with ?""",

        4: f"""Keep it going. CRITICAL: CANNOT be under 140 characters. Must be 140-180 stats with ?:

{prompt}

Be playful. Make it meaty. 140-180 chars. End with ?""",

        5: f"""Response needed. MINIMUM 140 CHARACTERS REQUIRED. Maximum 180. MUST end with ?:

{prompt}

Say something unexpected. Expand your thought. 140-180 chars. End with ?"""
    }
    user_prompt = user_prompts.get(attempt_number, f"""Text back naturally. CRITICAL: 140-180 characters, must end with ?:

{prompt}

Engage fully. 140-180 chars minimum/maximum. End with ?""")
    
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
    
    # ========== COMPREHENSIVE VALIDATION WITH AUTO-REPHRASE ==========
    # Validates against ALL rules, rephrase up to 3 times if needed
    # Process takes 30-40 seconds due to multiple checks and rephrase attempts
    validator = ResponseValidator(user)
    is_valid, final_response, validation_log = validator.validate_and_refine(reply_text, max_attempts=3)
    
    # Log validation results
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Response validation for user {user.id}:\n{''.join(validation_log)}")
    
    return final_response
