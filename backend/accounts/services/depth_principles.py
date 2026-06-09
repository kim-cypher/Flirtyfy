"""
DEPTH OVER BREADTH: Response Expansion Principles

Core Philosophy:
================
When a response is too short, expand it by going DEEPER into what's already there.
NOT by asking more questions or filling space.

Every word added must create more tension, not fill space.
Length comes from depth, not from additional questions.


PERMANENTLY BANNED PATTERNS (Category-based)
==============================================
"""

# CATEGORY 1: BANNED "TELL ME" FILLERS
# These sound curious but ask for nothing specific
BANNED_TELL_ME_PATTERNS = [
    "Tell me more",
    "Tell me about yourself",
    "Tell me everything",
    "Tell me what you think",
    "Tell me how you feel",
    "Tell me what's on your mind",
    "Tell me something interesting",
    "Tell me what you want",
    "Tell me your thoughts",
    "Tell me about your day",
    "Tell me what you're looking for",
    "Tell me about you",
    "Tell me what makes you happy",
    "Tell me what you're into",
]

# CATEGORY 2: BANNED "WHAT DO YOU THINK" FAMILY
BANNED_WHAT_DO_YOU_THINK_PATTERNS = [
    "What do you think?",
    "What do you think about that?",
    "What are your thoughts?",
    "What are your thoughts on that?",
    "What's your take on that?",
    "What's your opinion?",
    "What do you reckon?",
    "What's your view?",
    "What do you make of that?",
    "What would you say?",
    "What do you think about us?",
    "What do you think will happen?",
]

# CATEGORY 3: BANNED VERIFICATION QUESTIONS
BANNED_VERIFICATION_PATTERNS = [
    "Is that true?",
    "Is that right?",
    "Really?",
    "Are you serious?",
    "Do you mean that?",
    "Did you really?",
    "Is that so?",
    "Honestly?",
    "Are you sure?",
    "Is that how you feel?",
    "Do you really feel that way?",
    "Are you being serious right now?",
    "Do you actually believe that?",
    "Is that really true?",
    "You really think so?",
]

# CATEGORY 4: BANNED HOLLOW INTEREST SIGNALS
BANNED_HOLLOW_INTEREST_PATTERNS = [
    "That's interesting, tell me more",
    "I want to know more about that",
    "I'd love to hear more",
    "I want to know everything about you",
    "I want to understand you better",
    "I'm curious about you",
    "You seem interesting",
    "There's so much I want to know",
    "I want to learn more about you",
    "I'd like to know more",
    "That's fascinating, go on",
    "Keep going",
    "Continue",
    "Say more",
    "Elaborate on that",
]

# CATEGORY 5: BANNED OPEN-ENDED NOTHING QUESTIONS
BANNED_OPEN_ENDED_PATTERNS = [
    "What are you looking for?",
    "What do you want from life?",
    "What makes you happy?",
    "What makes you, you?",
    "What's your story?",
    "Who are you really?",
    "What are you passionate about?",
    "What drives you?",
    "What motivates you?",
    "What are your goals?",
    "What's important to you?",
    "What do you value most?",
    "What gets you out of bed?",
    "What does happiness mean to you?",
    "What are you all about?",
    "How would you describe yourself?",
    "Who are you as a person?",
    "What kind of person are you?",
    "What's your personality like?",
]

# CATEGORY 6: BANNED FAKE DEEP QUESTIONS
BANNED_FAKE_DEEP_PATTERNS = [
    "What do you think love is?",
    "What does life mean to you?",
    "What's the meaning of all this?",
    "Do you believe in fate?",
    "Do you believe in soulmates?",
    "Do you believe in destiny?",
    "What's your philosophy?",
    "What does connection mean to you?",
    "What does intimacy mean to you?",
    "What is attraction to you?",
    "What does a real relationship look like?",
    "What makes two people compatible?",
    "Do you think people can really change?",
    "What makes someone a good partner?",
    "What does loyalty mean to you?",
]

# CATEGORY 7: BANNED COMFORT CHECK FILLERS
BANNED_COMFORT_CHECK_PATTERNS = [
    "How does that make you feel?",
    "How are you feeling about that?",
    "How does that sit with you?",
    "Are you comfortable with that?",
    "Does that resonate with you?",
    "Do you relate to that?",
    "Can you relate?",
    "Does that make sense?",
    "Does that feel right?",
    "Do you understand what I mean?",
    "You know what I mean?",
    "Does that sound right?",
    "What feelings does that bring up?",
    "How are you feeling right now?",
]

# CATEGORY 8: BANNED FUTURE PROJECTION FILLERS
BANNED_FUTURE_PROJECTION_PATTERNS = [
    "What do you think the future holds?",
    "Where do you see yourself?",
    "What does your ideal future look like?",
    "What do you see for us?",
    "Where do you think this is going?",
    "What do you imagine happening next?",
    "What would our life look like together?",
    "Can you picture us together?",
    "What do you think we could become?",
    "Do you see potential here?",
    "Do you think this could be real?",
    "What do you think could happen?",
    "Where do you hope this leads?",
    "What are you hoping comes of this?",
]

# CATEGORY 9: BANNED "HAVE YOU EVER" GENERICS
BANNED_HAVE_YOU_EVER_PATTERNS = [
    "Have you ever been in love?",
    "Have you ever had your heart broken?",
    "Have you ever felt this way?",
    "Have you ever done something crazy?",
    "Have you ever taken a big risk?",
    "Have you ever surprised yourself?",
    "Have you ever regretted something?",
    "Have you ever wanted something?",
    "Have you ever felt understood?",
    "Have you ever fallen for someone?",
    "Have you ever done something spontaneous?",
    "Have you ever felt completely free?",
    "Have you ever met someone who changed you?",
    "Have you ever just let go?",
]

# CATEGORY 10: BANNED PREFERENCE SURVEYS
BANNED_PREFERENCE_SURVEY_PATTERNS = [
    "What's your favorite",
    "What kind of music do you like?",
    "What's your favorite movie?",
    "What do you like to do for fun?",
    "What do you like to do in your free time?",
    "What do you like to do on weekends?",
    "What are your hobbies?",
    "What's your favorite food?",
    "What kind of movies are you into?",
    "What kind of books do you read?",
    "What's your favorite season?",
    "What do you like in your free time?",
    "What are you into these days?",
    "What kind of music gets you going?",
    "What's your idea of a perfect day?",
]

# CATEGORY 11: BANNED MORNING/NIGHT FILLERS
BANNED_TIME_CHECK_PATTERNS = [
    "How was your day?",
    "How are you doing?",
    "How are you?",
    "How are you today?",
    "How's your day going?",
    "What are you up to?",
    "What are you doing right now?",
    "What have you been up to?",
    "How has your week been?",
    "How was your night?",
    "Did you sleep well?",
    "What are you up to today?",
    "Are you busy right now?",
    "How have you been?",
    "What's new with you?",
    "Anything exciting happening?",
]

# CATEGORY 12: BANNED VALIDATION SEEKERS
BANNED_VALIDATION_SEEKER_PATTERNS = [
    "Am I making you smile?",
    "Am I making you blush?",
    "Did that surprise you?",
    "Did I catch you off guard?",
    "Are you enjoying this?",
    "Are you having fun?",
    "Are you liking this?",
    "Do you like talking to me?",
    "Are you glad we started talking?",
    "Do you enjoy our conversations?",
    "Am I what you expected?",
    "Did you expect me to say that?",
    "Are you impressed?",
    "Does this feel good?",
    "Do you like where this is going?",
]

# CATEGORY 13: BANNED DOUBLE-BARRELLED DUMPS
# Any message with 2+ questions in a row = banned pattern

# CATEGORY 14: BANNED ECHO QUESTIONS
# Restating what they said as a question = banned
# E.g., "You love the beach? Tell me more about beaches"

# CATEGORY 15: BANNED PERMISSION ASKERS (Kills tension)
BANNED_PERMISSION_ASKER_PATTERNS = [
    "Can I ask you something?",
    "Is it okay if I ask?",
    "Do you mind if I ask?",
    "Would it be okay to talk about that?",
    "Is that too personal?",
    "I hope that's not too forward?",
    "Was that too much?",
    "Did I say too much?",
    "Is that weird to ask?",
    "Do you mind me asking?",
    "Is it okay that I said that?",
    "Too forward?",
    "Was that okay?",
    "Am I being too much?",
]

# CATEGORY 16: BANNED GENERIC GREETING/SMALL TALK
BANNED_GENERIC_GREETING_PATTERNS = [
    "How are you?",
    "How are you today?",
    "How are you doing today?",
    "How are you feeling?",
    "What's your name?",
    "Who are you?",
    "What do you do?",
    "What do you do for a living?",
    "Where are you from?",
    "What's your story?",
]

# Compile all into one master list
ALL_BANNED_PHATIC_PATTERNS = (
    BANNED_TELL_ME_PATTERNS +
    BANNED_WHAT_DO_YOU_THINK_PATTERNS +
    BANNED_VERIFICATION_PATTERNS +
    BANNED_HOLLOW_INTEREST_PATTERNS +
    BANNED_OPEN_ENDED_PATTERNS +
    BANNED_FAKE_DEEP_PATTERNS +
    BANNED_COMFORT_CHECK_PATTERNS +
    BANNED_FUTURE_PROJECTION_PATTERNS +
    BANNED_HAVE_YOU_EVER_PATTERNS +
    BANNED_PREFERENCE_SURVEY_PATTERNS +
    BANNED_TIME_CHECK_PATTERNS +
    BANNED_VALIDATION_SEEKER_PATTERNS +
    BANNED_PERMISSION_ASKER_PATTERNS +
    BANNED_GENERIC_GREETING_PATTERNS
)


"""
DEPTH EXPANSION STRATEGIES
===========================

Instead of padding with hollow questions, use ONE of these:
"""


def get_depth_expansion_prompt() -> str:
    """
    Returns the system prompt instruction for depth-based expansion.
    Used in response_validator._rephrase_response() when extending short responses.
    """
    return """
EXPAND BY GOING DEEPER - NOT WIDER

When extending a response to meet length requirements:
NEVER add more questions. NEVER add "tell me more" filler.

Instead, choose ONE of these strategies:

1️⃣ GO DEEPER INTO THE MOMENT
   - Extend the physical or emotional observation already in the response
   - Add one more specific sensory detail about what was just said
   - Let the feeling land longer before the question
   - EXAMPLE: "that caught me off guard" → "that caught me off guard, i'm still thinking about it"

2️⃣ ADD A SPECIFIC CALLBACK
   - Reference something said earlier in the conversation
   - Connect it to this moment specifically
   - "that thing you said about X earlier — this is the same energy"
   - NOT: "that's interesting" — YES: "that's the third time you've mentioned that"

3️⃣ SLOW THE BEAT DOWN
   - Add trailing thoughts that create tension
   - Use "..." to let something breathe before the question
   - A pause mid-response is more powerful than filler at the end
   - EXAMPLE: "i keep coming back to what you said... like it matters"

4️⃣ REVEAL SOMETHING
   - Have the character admit something real about how this is landing
   - NOT a label ("I feel excited") but actual behavior
   - "still thinking about that thing you said an hour ago"
   - NOT: "you make me feel things" — YES: "been rereading this conversation"

5️⃣ SHARPEN THE OBSERVATION
   - Instead of adding words, make existing words do more work
   - Rewrite the weakest sentence to be more specific, physical, unexpected
   - "you're interesting" → "the way you said that changed everything"

WHAT NEVER TO DO:
- Never add "tell me more" to hit character limit
- Never add "what do you think?" as padding
- Never add a second question to make it longer
- Never add generic compliment to fill space
- Never repeat a point in different words

TEST EACH EXPANSION:
"Does this word/phrase make the response stronger or just longer?"
If just longer → cut it and find words that do work.

CORE PRINCIPLE:
Length comes from depth, not from additional questions.
A 140-character response should feel complete because it said something REAL,
not because it asked something hollow to pad the ending.
"""


def validate_no_phatic_questions(response: str) -> tuple[bool, str]:
    """
    Check if response contains banned phatic/hollow question patterns.
    Uses word-boundary-aware regex matching to avoid false positives.
    
    Returns: (is_clean, violated_pattern)
    """
    import re
    response_lower = response.lower().strip()
    
    for pattern in ALL_BANNED_PHATIC_PATTERNS:
        pattern_lower = pattern.lower()
        
        # Use regex with word boundaries for more precise matching
        # Replace spaces with \s+ to handle multiple spaces
        regex_pattern = r'\b' + re.escape(pattern_lower).replace(r'\ ', r'\s+') + r'\b'
        
        if re.search(regex_pattern, response_lower):
            return False, pattern
    
    # Check for double-barrelled questions (2+ question marks)
    question_count = response.count('?')
    if question_count > 1:
        # Exception: Allow "...? Like...?" as natural speech
        # But flag "...? What...?" patterns
        if re.search(r'\?\s+(what|do you|are you)', response_lower):
            return False, "double-barrelled question detected"
    
    return True, ""


def get_depth_expansion_examples() -> dict:
    """
    Returns examples of depth-based expansions vs hollow padding.
    """
    return {
        "TOO_SHORT": "god you're driving me crazy",
        
        "HOLLOW_PADDING": "god you're driving me crazy? tell me more about yourself?",
        
        "DEPTH_EXPANSION_1_MOMENT": "god you're driving me crazy... like in the best way, i'm still thinking about what you said",
        
        "DEPTH_EXPANSION_2_CALLBACK": "god you're driving me crazy, especially after that thing you said about taking risks earlier",
        
        "DEPTH_EXPANSION_3_PAUSE": "god you're driving me crazy... like it's not even fair how much i'm replaying this conversation",
        
        "DEPTH_EXPANSION_4_REVEAL": "god you're driving me crazy, been reading this back like three times now because something about it just hit different",
        
        "DEPTH_EXPANSION_5_SHARPEN": "the way you just said that — god you're driving me crazy and you probably know it already",
    }
