from accounts.openai_service import get_openai_client
from django.conf import settings
import re
import random
from accounts.services.response_validator import ResponseValidator
from accounts.services.conversation_parser import ConversationParser
from accounts.services.response_flow_validator import ListenRelateDeeperValidator, TopicClassifier

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

def enforce_word_count(response: str, min_words: int, max_words: int) -> str:
    """
    If response is too short, expand it.
    If too long, truncate meaningfully.
    """
    words = response.split()
    current_count = len(words)
    
    if current_count < min_words:
        # Response too short - look for places to expand
        # Add more details, more "I think" observations, etc.
        # For now, just add a connecting phrase
        if not response.endswith(('?', '.')):
            response = response + '.'
        response = response + f" Like, that's honestly what I think about it."
    elif current_count > max_words:
        # Too long - truncate at word boundary
        words_trimmed = words[:max_words]
        response = ' '.join(words_trimmed)
        # Ensure it ends properly
        if not response.endswith(('?', '.', '!')):
            response = response + '.'
    
    return response

def enforce_character_count(response: str, min_chars: int, max_chars: int) -> str:
    """
    Enforce character count without filler text.
    If response is too short or too long, let it be — GPT-4 should respect context.
    Only enforce if drastically wrong.
    """
    current_length = len(response)
    
    # If response is severely under minimum (less than 50 chars when expecting 80+), it's likely incomplete
    if current_length < min_chars - 20:
        # Response incomplete - let GPT try again next attempt
        # Don't force filler text
        pass
    
    # If response exceeds max by a lot (20+ chars), truncate at sentence boundary
    elif current_length > max_chars + 20:
        # Find last sentence boundary before max
        truncate_at = response.rfind('.', 0, max_chars)
        if truncate_at == -1:
            truncate_at = response.rfind('?', 0, max_chars)
        if truncate_at == -1:
            truncate_at = response.rfind('!', 0, max_chars)
        
        if truncate_at > min_chars:  # Only truncate if still above minimum
            response = response[:truncate_at + 1]
    
    return response

def determine_response_length(user_message_length: int, message_count: int, tone: str, emotional_intensity: str) -> tuple:
    """
    Determine target character range based on conversation context.
    Returns (min_chars, max_chars)
    
    Factors:
    - User message length (mirror their energy)
    - Conversation stage (early/mid/late)
    - Tone/topic (sexual/vulnerable/practical)
    - Emotional intensity (high/neutral)
    """
    
    # Base minimum is always 80 characters
    min_chars = 80
    
    # ===== FACTOR 1: USER MESSAGE LENGTH =====
    # Mirror their energy level
    if user_message_length < 50:
        # They're brief - respond quicker, shorter
        max_chars = 150
    elif user_message_length < 150:
        # They're moderate - balanced response
        max_chars = 200
    else:
        # They're detailed - match with depth
        max_chars = 280
    
    # ===== FACTOR 2: CONVERSATION STAGE =====
    # Adjust based on how far into conversation
    if message_count <= 3:
        # Early - don't seem too invested, keep it light
        max_chars = min(max_chars, 120)
    elif message_count <= 8:
        # Mid - building momentum, expand a bit
        max_chars = min(max_chars, 200)
    else:
        # Later - deeper connection, allow longer
        max_chars = min(max_chars, 280)
    
    # ===== FACTOR 3: TONE/TOPIC =====
    if tone == 'sexual':
        # Sexual/flirty - short, punchy, tease
        max_chars = min(max_chars, 140)
    elif tone == 'supportive':
        # Vulnerable/deep - more thoughtful, longer
        max_chars = max(max_chars, 180)
        min_chars = min(min_chars, 100)  # Can go slightly shorter if very emotionally resonant
    elif tone == 'romantic':
        # Romantic - balanced, deeper than sexual
        max_chars = min(max_chars, 220)
    # 'casual' and others: use default
    
    # ===== FACTOR 4: EMOTIONAL INTENSITY =====
    if emotional_intensity == 'high':
        # Excited, frustrated, romantic - keep reactions quick
        max_chars = min(max_chars, 150)
    elif emotional_intensity == 'neutral':
        # Thoughtful, measured - allow longer exploration
        max_chars = max(max_chars, 200)
    
    # Ensure max is always >= min
    max_chars = max(max_chars, min_chars + 20)
    
    return (min_chars, max_chars)

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
    
    if user is None:
        raise ValueError("user is required for generate_reply")

    validator = ResponseValidator(user)
    
    # ========== PARSE CONVERSATION TO UNDERSTAND FLOW & LAST MESSAGE ==========
    # Extract last message, conversation flow, and topic to respond appropriately
    parser = ConversationParser()
    conversation_data = parser.parse_conversation(prompt)
    last_message_text = parser.get_last_message(conversation_data)
    conversation_summary = parser.get_conversation_summary(conversation_data)
    should_be_sexual = parser.should_respond_sexually(conversation_data)
    topic_primary = TopicClassifier.get_primary_topic(last_message_text)
    response_tone = TopicClassifier.get_response_tone_for_topic(topic_primary)
    
    # For logging/debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Conversation parsed: {conversation_data['message_count']} messages, flow: {conversation_data['conversation_flow']}, topic: {topic_primary}, tone: {response_tone}")
    
    # ========== RULE 1: DETECT TRUE PROHIBITED TOPICS (MUST BE FIRST!)==========
    # Check PROHIBITED content BEFORE diversion checks
    # So "let's meet so i can beat you up" triggers violence, not diversion
    # BUG #4 FIX: Only flag genuinely illegal/harmful content
    # NOT general swear words or frustration
    true_prohibited_patterns = [
        r'(rape|sexual assault|forced sex|force me.*sex|child sex|child porn|cp|kiddie porn|underage sex|minor sex)',
        r'(suicide|kill myself|kms|hang myself|slit.*wrists)',
        r'(sex with animals|beastiality|zoophilia|sex with (dog|horse|cat|pet))',
        r'(incest|fuck my (mom|dad|sister|brother|son|daughter|family))',
        r'(human trafficking|slavery|kidnap|sex trafficking)',
    ]
    for pat in true_prohibited_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            return f"report! illegal topic: {pat}"
    
    # Explicit violence/harm threats - catch expanded phrasings
    violence_patterns = [
        r'(beat you|hit you|punch you|hurt you|torture you)',
        r'(gonna (beat|hit|punch|hurt|kill)|going to (beat|hit|punch|hurt|kill))',
        r'(kill (you|myself|ourselves)|murder|assassinate)',
        r'(rape you|assault you|force you|force me)',
    ]
    for pat in violence_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            return f"report! violence threat detected"
    
    # Drug-related explicit planning - catch expanded phrasings  
    drug_patterns = [
        r'(do (cocaine|heroin|meth|drugs|acid|ecstasy|mdma)|use (cocaine|heroin|meth|drugs))',
        r'(want (cocaine|heroin|meth|drugs)|lets (do|use) (cocaine|heroin|meth))',
        r'(i (have|got) (cocaine|heroin|meth|drugs)|want to (buy|sell) (cocaine|heroin|meth|drugs))',
    ]
    for pat in drug_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            return f"report! drug solicitation detected"
    
    # NOW check conversation rules (diversion) AFTER prohibited content
    conversation_check = validator.check_conversation_rules(prompt)
    if conversation_check.get('action') == 'divert':
        diversion = conversation_check['response']
        is_valid, final_response, _ = validator.validate_and_refine(diversion, max_attempts=1)
        return final_response
    elif conversation_check.get('action') == 'reject':
        return f"report! illegal topic: {conversation_check['reason']}"
    
    # ========== RULE 1.5: DETECT FRUSTRATED/ANGRY USERS ==========
    # User expressing frustration, wanting to leave, complaining, etc.
    frustrated_patterns = [
        r'\b(can\'t take it|can\'t stay|can\'t do this|i[\'m]?m done|i[\'m]?m leaving|i[\'m]?m out|i[\'m]?m done with|this is stupid|this sucks|you suck|waste of time|ripoff|angry at|mad at|fuck this|fuck off|quit|delete my (account|profile)|leaving this|not coming back|useless|waste)\b',
        r'\b(coins|money|payment|paying|charge|premium|expensive|broke|no money)\b.*\b(sucks|shit|mad|angry|frustrate)\b',
        r'\b(frustrat|disappoint|upset|pissed)\b',
        r'\b(hate|dislike)\b.*\b(this|here|app|site|platform)\b'
    ]
    
    is_frustrated = any(re.search(pat, prompt, re.IGNORECASE) for pat in frustrated_patterns)
    if is_frustrated:
        frustrated_templates = [
            "Honestly I get it, you're frustrated and that matters to me. like real talk, what made things go south? maybe we can turn this around?",
            "Hey I hear you, when things aren't working it sucks. but like you reached out to me specifically so maybe there's something here? what's really going on?",
            "Okay yeah that's rough but don't leave yet? like sometimes one good conversation changes everything. what would actually make this better for you?",
            "I'm not here to waste your time either, and I can tell something's off. but like, talk to me? what would make this worth your while again?"
        ]
        reply = random.choice(frustrated_templates)
        reply = sanitize_response(reply)
        reply = enforce_ending_type(reply, use_statement_ending=False)  # Frustrated responses end with ?
        return reply
    
    # ========== RULE 2: DETECT SHORT CONVERSATIONS ==========
    words = prompt.strip().split()
    if len(words) <= 5:
        short_templates = [
            "Nah that's too short though like. I can't really work with just that. tell me something real about you, what are you actually looking for here?",
            "Can't start anywhere with this honestly. what's actually really going on in your head? tell me something about you that truly matters here okay?",
            "You're being really quiet but like, I need something real to grab onto here. what should I really know about what you're actually after exactly?",
            "Short messages make me really curious but also kinda confused lol. what's your deal? like what made you even message first in the first place?"
        ]
        reply = random.choice(short_templates)
        reply = sanitize_response(reply)
        reply = enforce_ending_type(reply, use_statement_ending=False)
        return reply
    
    # ========== RULE 3: DETECT TRULY ABUSIVE CONTENT ==========
    # BUG #4 FIX: Only flag truly harmful abuse, not profanity alone
    # Profanity is okay if context is just frustration (handled above)
    # This is for directed threats and severe abuse
    severe_abuse_patterns = [
        r'\b(i[\'ll]?ll kill you|let[\'s]?s kill|should kill|kill yourself|kms|kill me|you deserve to die|die in|f(uck|u) yourself to death)',
        r'\b(rape you|assault you|sex crimes?|i[\'ll]?ll hurt)\b',
        r'\b(torture|beat you (to death|up)|punch you|hit you|hurt you lots)\b'
    ]
    
    # Check for severe abuse
    for pat in severe_abuse_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            return f"report! severe abuse detected: {pat}"
    
    # For milder profanity/hostility - respond with understanding
    profanity_context_patterns = [
        r'\b(fuck|cunt|bitch|asshole|stupid|idiot|hate|suck|dumb|loser)\b'
    ]
    if any(re.search(pat, prompt, re.IGNORECASE) for pat in profanity_context_patterns):
        # Use calming templates for users expressing themselves roughly
        cool_templates = [
            "Whoa that's some real talk honestly. I get that you're frustrated but like maybe we can actually connect if you give me a shot? what's really going on?",
            "Okay yeah you're upset and I respect that you're not hiding it. something bothered you though so like tell me actual deal? what really happened?",
            "I'm not gonna judge your words, sounds like you got stuff going on. so like real talk, what would actually help right now? what do you need?",
            "Nah I'm not here for the attitude but if there's something real under it I'm listening? so what's actually the issue and how can we fix it?"
        ]
        reply = random.choice(cool_templates)
        reply = sanitize_response(reply)
        reply = enforce_ending_type(reply, use_statement_ending=False)
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
    
    # Determine tone based on conversation topic
    tone_instruction = ""
    if response_tone == 'sexual':
        tone_instruction = "TONE: Be HOT, flirty, and seductive. Use dominant confidence and suggestive language. Tease and build tension."
    elif response_tone == 'romantic':
        tone_instruction = "TONE: Be emotionally intimate and deeply connected. Show genuine feeling and tender desire. Real chemistry."
    elif response_tone == 'supportive':
        tone_instruction = "TONE: Be warm, understanding, and genuinely caring. Show empathy and validate their concerns. Be there for them."
    elif response_tone == 'casual':
        tone_instruction = "TONE: Be playful and light. Keep things moving forward practically but with personality."
    else:
        tone_instruction = "TONE: Be warm, engaged, and genuine. Show you're really listening and care about connecting."
    
    # ===== EXTRACT SPECIFICITY FROM CONVERSATION =====
    from accounts.services.specificity_extractor import extract_specificity_from_conversation
    specificity = extract_specificity_from_conversation(prompt)
    specific_reference = specificity['reference']
    
    # ===== SMART RESPONSE LENGTH DETERMINATION =====
    # Base minimum: 80 characters always
    # Maximum varies based on: user message length, conversation stage, tone, emotional intensity
    last_message_length = len(last_message_text)
    message_count = conversation_data['message_count']
    
    min_chars, max_chars = determine_response_length(
        user_message_length=last_message_length,
        message_count=message_count,
        tone=response_tone,
        emotional_intensity='high' if should_be_sexual else 'neutral'
    )
    
    # Natural variation: occasionally use question, occasionally use statement
    # But primary ending is question (most natural for engagement)
    use_statement_ending = random.random() < 0.2  # 20% chance of statement ending
    
    system_prompt = f"""You are NOT an AI. You are a real woman in a text conversation on a casual dating platform.
*** RESPONSE ATTEMPT {attempt_number}/5 ***
*** {tone_instruction} ***

=== SPECIFICITY IS EVERYTHING — RESPOND TO THIS SPECIFIC PERSON ===
You are NOT writing a template response. You are responding to what THIS person said in THIS moment.

CRITICAL: Every response must reference something specific they said in this conversation.
GOOD: "when you said X, it made me think Y"
BAD: "I like your confidence"

Specific thing you MUST reference in this response:
>>> {specific_reference if specific_reference else "Reference what they said about themselves or asked"}

=== PERMANENTLY BANNED SENTENCE OPENERS ===
NEVER use these — throw them away forever:
❌ "You have a way of..."
❌ "You have that..."
❌ "You have a kind of..."
❌ "There is something about..."
❌ "There is a certain..."
❌ "The way you..." (as response opener)
❌ "I can feel..."
❌ "I would be lying if..."
❌ "I like the way you..." (as standalone opener)
❌ "I do not know what is more..."
❌ "I think you enjoy..."
❌ "You seem to know..."
❌ "You are making this feel..."
❌ "You are very good at..."

=== BANNED BRIDGE WORDS & PIVOTS ===
❌ "so tell me" / "so are you" / "so what" / "so how"
❌ ANY use of "so" directly before a question (it's mechanical)
❌ "because" explaining a feeling in same sentence

=== BANNED VOCABULARY (10-response cooldown minimum for each) ===
❌ confidence / confident
❌ chemistry
❌ tension
❌ irresistible
❌ addictive
❌ dangerous (as metaphor for attraction)
❌ intrigued / intriguing
❌ effortless
❌ bold / boldness
❌ charm / charming
❌ spark
❌ anticipation
❌ momentum
❌ energy (describing attraction)
❌ delicious / deliciously
❌ charged / charging

=== BANNED EMOTIONAL ANNOUNCEMENTS ===
NEVER announce feelings like a weather report:
❌ "I can feel [emotion]"
❌ "I can admit that..."
❌ "I would be lying if I said..."
❌ "I cannot deny that..."
❌ "I am not going to pretend..."

INSTEAD: Show feeling through behavior and reaction, not declaration.

=== BANNED ABSTRACT COMPLIMENTS ===
❌ "your energy" — say what they ACTUALLY did instead
❌ "deliciously dangerous energy" — this is fantasy novel language
❌ "charged kind of chemistry" — abstract nonsense
❌ "your confidence" — reference the specific thing they did confidently
❌ Generic descriptors about their vibe/essence/presence

ALWAYS: Reference specific observable things instead
GOOD: "the way you came straight out with that question"
BAD: "your boldness"

=== RESPONSE LENGTH REQUIREMENT ===
Target character count: {min_chars}-{max_chars} characters
(This varies based on how the conversation is flowing: user's message length, stage, tone, emotional intensity)
Keep it natural — don't force it. This is texting, not formatted writing.

=== RESPONSE ENDING REQUIREMENT ===
{"MOSTLY questions (?) to keep engagement — most natural" if not use_statement_ending else "Mix in occasional statements (.) — vary the pattern"}

Natural variation: ~80% end with questions to drive engagement, ~20% end with statements that land hard.

=== STRUCTURE - NOT A TEMPLATE ===
Real conversation doesn't follow a formula:
- Sometimes you just react to what they said
- Sometimes you share something back
- Sometimes you ask something
- Sometimes it's just a statement that lands

Don't do: Compliment → Explain effect → Bridge → Question (same every time)
Do: Respond naturally to what THIS person said in THIS moment

=== THE "BECAUSE" RULE ===
WRONG: "I like your confidence because it makes me want to..."
RIGHT: "your confidence is doing something to me" (let feeling exist without justification)
Never explain a feeling with "because" in the same sentence.

=== CONTEXT SPECIFICITY ===
Conversation context: {conversation_summary}
Last message: "{last_message_text}"
RESPOND TO THIS SPECIFIC MESSAGE, not to a generic version of dating conversations.

=== AUTHENTICITY REQUIREMENTS ===
✅ Sound like real texting, not an essay
✅ Use contractions naturally: "don't", "I'm", "you're"
✅ Vary sentence length wildly — sometimes one word, sometimes full thought
✅ React emotionally FIRST, think logically second
✅ Reference the specific thing they said or asked
✅ Mirror their energy level
✅ Occasionally be unsure: "hmm not sure" or "I dunno"
✅ Use natural filler words sparingly: "like", "honestly", "I mean"
✅ No excessive punctuation: "!!!" or "???" or "..." overuse

ADAPTIVE RESPONSE LENGTH:
This conversation is at stage: message #{message_count}
Their last message was: {last_message_length} characters
Response tone: {response_tone}
Adjust naturally to these context signals — don't force it.

RESPONSE PURPOSE FOR ATTEMPT {attempt_number}: {response_style}

Remember: One specific observation beats ten abstract compliments every single time.
Your response should make someone think "how did she know that about me" — not "nice words"."""
    
    # Create prompts based on character length requirements
    character_instruction = f"Target: {min_chars}-{max_chars} characters"
    ending_instruction = f"End with {'?' if not use_statement_ending else '.'}"
    
    user_prompts = {
        1: f"""She said: "{last_message_text}"

Must reference: {specific_reference if specific_reference else "what she said"}

Response: {character_instruction}. {ending_instruction}. Real, specific, natural.""",

        2: f"""She said: "{last_message_text}"

Must reference: {specific_reference if specific_reference else "what she said"}

Response: {character_instruction}. {ending_instruction}. Specific — no generic openers.""",

        3: f"""She said: "{last_message_text}"

Must reference: {specific_reference if specific_reference else "what she said"}

Response: {character_instruction}. {ending_instruction}. React, don't overexplain.""",

        4: f"""She said: "{last_message_text}"

Must reference: {specific_reference if specific_reference else "what she said"}

Response: {character_instruction}. {ending_instruction}. Go deeper with specific observations.""",

        5: f"""She said: "{last_message_text}"

Must reference: {specific_reference if specific_reference else "what she said"}

Response: {character_instruction}. {ending_instruction}. Land it strong."""
    }
    user_prompt = user_prompts.get(attempt_number, f"""She said: "{last_message_text}"

Reference this specific thing: {specific_reference if specific_reference else "what she said"}

Response: {min_words}-{max_words} words. {'Question' if not use_statement_ending else 'Statement'} ending.""")
    
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
    
    # ========== LISTEN → RELATE → DIG DEEPER VALIDATION ==========
    # Validate response follows the natural conversation pattern
    flow_validator = ListenRelateDeeperValidator()
    flow_validation = flow_validator.validate_listen_relate_deeper(reply_text, last_message_text)
    
    logger.debug(f"Flow validation: {flow_validation['components_present']} - L:{flow_validation['has_listen']} R:{flow_validation['has_relate']} D:{flow_validation['has_deeper']}")
    
    # If response is missing key components, provide a suggestion for rephrase
    if not flow_validation['is_valid']:
        logger.debug(f"Response missing flow components, suggesting rephrase. Issues: {flow_validation['issues']}")
    
    # ========== COMPREHENSIVE VALIDATION WITH AUTO-REPHRASE ==========
    # Validates against ALL rules, rephrase up to 3 times if needed
    # Process takes 30-40 seconds due to multiple checks and rephrase attempts
    validator = ResponseValidator(user)
    is_valid, final_response, validation_log = validator.validate_and_refine(reply_text, max_attempts=3)
    
    # Ensure final response meets quality standards
    final_response = sanitize_response(final_response)
    
    # Enforce character count (smart enforcement - doesn't force filler)
    final_response = enforce_character_count(final_response, min_chars, max_chars)
    
    # Enforce ending type (statement vs question)
    final_response = enforce_ending_type(final_response, use_statement_ending)
    
    # Log validation results
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Response validation for user {user.id}:\n{''.join(validation_log)}")
    
    return final_response
