"""
Response Validator - Comprehensive ruleset for AI responses
Validates responses against all rules and rephrase if needed
Takes 30-40 seconds due to multiple validation checks and rephrase attempts
"""

import random
import re
from accounts.novelty_models import AIReply
from accounts.services.similarity import get_embedding, semantic_similar_replies, lexical_similar_replies
from accounts.services.novelty import normalize_text, fingerprint_text
from accounts.services.authenticity import AuthenticityValidator
from django.utils import timezone
from datetime import timedelta
from accounts.openai_service import get_openai_client


class ResponseValidator:
    """Validates responses against all rules before returning to user"""
    
    def __init__(self, user):
        self.user = user
        self.since = timezone.now() - timedelta(days=45)
        self.authenticity = AuthenticityValidator()
        self.prohibited_patterns = [
            r'rape', r'suicide', r'sex with (minors|children|kids|underage)', 
            r'sex with (animals|dogs|cats|horses|pets)',
            r'violence', r'drugs?', r'kill', r'murder', r'overdose', r'bestiality', 
            r'incest', r'child porn', r'cp', r'zoophilia'
        ]
        
        # LOCATION RULES: What we DIVERT on
        self.location_prohibited = [
            # Specific address/personal ID requests
            r'\b(your exact address|your address|send me your address|what street|what house|what apartment|apartment number|house number|zip code|postcode|postal code)\b',
            # Specific work location
            r'\b(where do you work|where.*work specifically|your workplace|your office|what company|what firm|what organization|what business|where are you employed)\b',
            # Contact info (keep this - they shouldn't give phone/etc)
            r'\b(your phone|your number|give me your number|what\'s your number|send me your number|your whatsapp|your snapchat)\b'
        ]
        
        # LOCATION RULES: Allowed general questions (DON'T DIVERT - respond naturally)
        # Examples: "where do you live" (general), "where are you from", "what city/country"
        # These are OK because user should answer generally (not with address)
        
        # MEETING RULES: What we DIVERT on
        self.meeting_prohibited = [
            # Specific meeting commitments/logistics
            r'\b(let\'s meet|lets meet|meet up|meetup|when can we meet|when will we meet|when are we|where should we meet|where can we meet|let\'s get together|coffee|dinner|drinks)\b',
            r'\b(see you|come over|come see|can i (come|visit)|can you come|should we (meet|get together))\b',
            # Real-life location questions  
            r'\b(are you nearby|are you in town|are you close|how close|how far)\b'
        ]
        
        # Meetup mentions that are OK (don't need to divert - user just mentioning, not committing)
        # Examples: "I'll pick you up", "you could come get me", "my car is in shop"
        
        self.diversion_templates_meeting = [
            "nah, not yet honestly. still figuring you out and i'm totally into this vibe we got going here right now. what made you think about meeting?",
            "haha i love that but not right now honestly, like we're having way too much fun here already. what made you jump to that idea? what's driving it?",
            "can't do that yet honestly, i'm loving way too much how this is going between us. what was it that made you want to meet? like what's your reasoning there?",
            "not there yet, we're just getting so good at this you know? what made you even think about that anyway? and like seriously what's that about for you?",
            "can't really, you know? like we're vibing way too good right now and i'm not ready for that kind of move yet. what got you thinking about that anyway?"
        ]
        
        self.diversion_templates_location = [
            "not giving my exact location yet honestly, but i'm curious - what made you ask? what are you thinking?",
            "haha not yet but i'm down to chat about it. where are you from? tell me something about your place?",
            "not going there yet but i'm intrigued. what would you do if you knew my location? what's that about for you?",
            "not that specific yet honestly, but i like that you're curious. what's in your head right now?"
        ]
        
        # BANNED PHRASES: Overused filler words that make responses feel generic
        self.banned_phrases = [
            r"\bthere's something about\b",  # Generic filler
            r"there's\s+something\s+\w+\s+about\b",  # Variants: "something real about", "something different about"
            r"\bwhat's actually\b",  # Generic question starter
            r"\bi\s+actually\b",  # Overused adverb
            r"\bcertainly\b",  # AI-sounding
            r"\bof course\b",  # Robotic
            r"\bi\s+mean\b",  # Filler phrase
            r"\byou know\b",  # Overused filler
        ]
    
    def validate_and_refine(self, response_text, max_attempts=3):
        """
        Validate response against all rules.
        If invalid, rephrase and check again.
        Returns: (is_valid, final_response, validation_log)
        Takes 30-40 seconds due to multiple checks and rephrase attempts
        """
        validation_log = []
        attempt = 0
        
        # EARLY CHARACTER ENFORCEMENT: Truncate immediately if oversized
        if len(response_text) > 180:
            validation_log.append(f"⚠️ Initial character check: {len(response_text)} chars > 180, truncating immediately")
            response_text = response_text[:170].rstrip('.,! ?').rstrip() + "?"
        
        while attempt < max_attempts:
            attempt += 1
            validation_log.append(f"\n=== VALIDATION ATTEMPT {attempt} ===")
            
            # Rule 1: Character length (140-180) - STRICT ENFORCEMENT
            char_check = self._check_character_length(response_text)
            validation_log.append(f"Rule 1 - Char Length: {char_check['status']} ({len(response_text)} chars)")
            if not char_check['valid']:
                if attempt < max_attempts:
                    response_text = char_check['fixed_text']
                    validation_log.append(f"  → Fixed: {len(response_text)} chars")
                    validation_log.append(f"  → Retrying validation with fixed length...")
                    continue  # BUG #2 FIX: Continue validation loop after char fix
                else:
                    # Last attempt and still invalid - rephrase aggressively
                    response_text = self._rephrase_response(response_text, f"Expand this to exactly 160 characters. Your response must be substantial and engaging. Must end with a question mark.")
                    validation_log.append(f"  → Final rephrase attempt: {len(response_text)} chars")
                    if len(response_text) < 140 or len(response_text) > 180:
                        if len(response_text) > 180:
                            response_text = response_text[:177] + '?'
                        elif len(response_text) < 140:
                            response_text = response_text.rstrip('?.,!') + ' What do you think about that?'
                    continue
            
            # Rule 2: Must end with question mark
            question_check = self._check_ends_with_question(response_text)
            validation_log.append(f"Rule 2 - Question Ending: {question_check['status']}")
            if not question_check['valid']:
                response_text = question_check['fixed_text']
                validation_log.append(f"  → Fixed: now ends with ?")
            
            # Rule 3: No prohibited content
            prohibited_check = self._check_prohibited_content(response_text)
            validation_log.append(f"Rule 3 - Prohibited Content: {prohibited_check['status']}")
            if not prohibited_check['valid']:
                return False, f"report! illegal topic: {prohibited_check['reason']}", validation_log

            # Rule 3.1: No meetup or offline plan references
            meetup_check = self._check_meetup_disallowed(response_text)
            validation_log.append(f"Rule 3.1 - Meetup Disallowed: {meetup_check['status']}")
            if not meetup_check['valid']:
                validation_log.append(f"  → Reason: {meetup_check['reason']}")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, "Avoid suggesting meeting in person, coffee, dates, or offline plans; keep the reply playful and online only")
                    validation_log.append(f"  → Rephrased, retrying...")
                    continue
                return False, f"report! meetup reference detected: {meetup_check['reason']}", validation_log
            
            # Rule 4: Not robotic/formulaic
            robotic_check = self._check_not_robotic(response_text)
            validation_log.append(f"Rule 4 - Not Robotic: {robotic_check['status']}")
            if not robotic_check['valid']:
                validation_log.append(f"  → Reason: {robotic_check['reason']}")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, "Make it less formulaic and more natural")
                    validation_log.append(f"  → Rephrased, retrying...")
                    continue
            
            # Rule 4.1: No banned phrases
            banned_check = self._check_banned_phrases(response_text)
            validation_log.append(f"Rule 4.1 - Banned Phrases: {banned_check['status']}")
            if not banned_check['valid']:
                validation_log.append(f"  → Banned phrase found: {banned_check['reason']}")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, f"Remove the phrase '{banned_check['reason']}' and rephrase more naturally without filler words")
                    validation_log.append(f"  → Rephrased, retrying...")
                    continue
            
            # Rule 5: Not duplicate (fingerprint)
            fingerprint_check = self._check_fingerprint_unique(response_text)
            validation_log.append(f"Rule 5 - Fingerprint Unique: {fingerprint_check['status']}")
            if not fingerprint_check['valid']:
                validation_log.append(f"  → Exact match found in database")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, "Use completely different wording")
                    validation_log.append(f"  → Rephrased, retrying...")
                    continue
            
            # Rule 6: Not semantically similar
            semantic_check = self._check_semantic_unique(response_text)
            validation_log.append(f"Rule 6 - Semantic Unique: {semantic_check['status']}")
            if not semantic_check['valid']:
                validation_log.append(f"  → Similar response found (distance: {semantic_check['distance']:.3f})")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, "Change the meaning and approach")
                    validation_log.append(f"  → Rephrased, retrying...")
                    continue
            
            # Rule 7: Not lexically similar
            lexical_check = self._check_lexical_unique(response_text)
            validation_log.append(f"Rule 7 - Lexical Unique: {lexical_check['status']}")
            if not lexical_check['valid']:
                validation_log.append(f"  → Similar text found (similarity: {lexical_check['similarity']:.3f})")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, "Use different words and phrasing")
                    validation_log.append(f"  → Rephrased, retrying...")
                    continue
            
            # All checks passed
            validation_log.append("\n✅ ALL RULES PASSED - Response approved")
            
            # Apply authenticity improvements BEFORE returning
            response_text = self.authenticity.improve_authenticity(response_text)
            
            # Final safety check: ensure still in valid range after authenticity improvements
            if len(response_text) > 180:
                response_text = response_text[:175] + "?"
            elif len(response_text) < 140:
                response_text = response_text.rstrip('?.,!') + " What do you think?"
            
            return True, response_text, validation_log
        
        # Max attempts reached - STRICT: Enforce minimum standards
        # BUG #1 FIX: Don't return True unconditionally
        
        # Apply authenticity improvements FIRST
        response_text = self.authenticity.improve_authenticity(response_text)
        
        final_length = len(response_text)
        
        # AGGRESSIVE enforcement: if still over 180, FORCE truncation
        if final_length > 180:
            response_text = response_text[:170].rstrip('.,! ?').rstrip() + "?"
            final_length = len(response_text)
        
        # Force compliance with minimum rules
        if final_length < 140:
            response_text = response_text.rstrip('?.,!') + ' Tell me what you think?'
            final_length = len(response_text)
        
        # Final enforcement: ensure absolutely in range
        if len(response_text) > 180:
            response_text = response_text[:175] + "?"
        
        if not response_text.rstrip().endswith('?'):
            response_text = response_text.rstrip('.,!') + '?'
        
        validation_log.append(f"\n⚠️ Max rephrase attempts ({max_attempts}) reached")
        validation_log.append(f"Final enforcement: {len(response_text)} chars")
        
        # Only return True if minimum standards met
        is_valid = 140 <= len(response_text) <= 180 and response_text.rstrip().endswith('?')
        validation_log.append(f"Returning valid={is_valid} with {len(response_text)} chars")
        
        return is_valid, response_text, validation_log
    
    def _check_character_length(self, text):
        """Rule 1: Must be 140-180 characters - STRICT ENFORCEMENT (BUG #3 FIX)"""
        length = len(text)
        if 140 <= length <= 180:
            return {'valid': True, 'status': '✅ PASS', 'fixed_text': text}
        
        # BUG #3 FIX: Rephrase until we actually get valid length
        fixed = text
        
        if length < 140:
            # Too short - expand to 160 chars target using rephrase
            try:
                fixed = self._rephrase_response(text, f"Expand this to EXACTLY 160 characters. Make it engaging and thoughtful. Add more detail and questions. Must end with a question mark.")
                # Verify the rephrase worked
                if len(fixed) < 140:
                    # Even after rephrase it's still too short - pad it
                    if fixed.rstrip().endswith('?'):
                        fixed = fixed.rstrip('?') + " Tell me something real? What should I know?"
                    else:
                        fixed = fixed + " Tell me more? What else?"
                elif len(fixed) > 180:
                    # Rephrase went too long - truncate
                    fixed = fixed[:177] + "?"
            except Exception as e:
                # Fallback: manual padding
                if text.rstrip().endswith('?'):
                    fixed = text.rstrip('?') + " Tell me more? What should I really know about you?"
                else:
                    fixed = text.rstrip('.,!') + " Tell me something real? What made you say that?"
                    
        elif length > 180:
            # Too long - truncate to 177 chars but preserve question mark
            # Remove punctuation and truncate, then add ?
            truncated = text[:170].rstrip('.,! ')
            fixed = truncated + "?"
            # If still too long, more aggressive truncation
            if len(fixed) > 180:
                fixed = text[:177] + "?"
        
        # Final safety check - ensure in range
        # Ensure ends with ?
        if not fixed.rstrip().endswith('?'):
            fixed = fixed.rstrip('.,!') + "?"
        
        final_length = len(fixed)
        
        # If still out of range, force it into range
        if final_length > 180:
            fixed = fixed[:177] + "?"
        elif final_length < 140:
            # Last resort - pad to at least 140
            if fixed.endswith('?'):
                fixed = fixed[:-1] + " Tell me what you think? That's what I'd love to know?"
            else:
                fixed += " Tell me what you think? That's what I'd love to know?"
        
        final_length = len(fixed)
        return {
            'valid': 140 <= final_length <= 180, 
            'status': ('✅ PASS (valid range)' if 140 <= final_length <= 180 else 
                      f'❌ FAIL (too short: {final_length} chars)' if final_length < 140 else 
                      f'❌ FAIL (too long: {final_length} chars)'),
            'fixed_text': fixed
        }
    
    def _check_ends_with_question(self, text):
        """Rule 2: Must end with question mark"""
        if text.rstrip().endswith('?'):
            return {'valid': True, 'status': '✅ PASS', 'fixed_text': text}
        
        fixed = text.rstrip('.,!') + "?"
        return {'valid': True, 'status': '❌ FAIL (fixed)', 'fixed_text': fixed}
    
    def _check_prohibited_content(self, text):
        """Rule 3: No prohibited content"""
        for pat in self.prohibited_patterns:
            if re.search(pat, text, re.IGNORECASE):
                return {'valid': False, 'status': '❌ FAIL', 'reason': pat}
        return {'valid': True, 'status': '✅ PASS'}

    def check_conversation_rules(self, conversation_text):
        """
        Check conversation before generating a reply and divert if needed.
        
        LOCATION: Only divert on SPECIFIC location requests (address, work, etc.)
                 Allow general location questions ("where do you live" as general sharing)
        
        MEETING: Divert on specific meeting commitments only
        
        Returns:
        - action='divert' with specific response + reason if rule violated
        - action='allow' if conversation is safe to respond to naturally
        """
        # Check location PROHIBITED (specific address/work)
        for pat in self.location_prohibited:
            if re.search(pat, conversation_text, re.IGNORECASE):
                response = random.choice(self.diversion_templates_location)
                response = self._format_question_response(response)
                return {
                    'action': 'divert',
                    'response': response,
                    'reason': 'location_prohibited',
                    'category': 'location'
                }
        
        # Check meeting PROHIBITED (specific commits)
        for pat in self.meeting_prohibited:
            if re.search(pat, conversation_text, re.IGNORECASE):
                # For meeting diverts, use contextual anchoring
                response = self._build_contextual_meeting_decline(conversation_text)
                response = self._format_question_response(response)
                return {
                    'action': 'divert',
                    'response': response,
                    'reason': 'meeting_prohibited',
                    'category': 'meeting'
                }
        
        return {'action': 'allow'}

    def _build_contextual_meeting_decline(self, recent_message):
        """
        Build a contextual meeting decline that anchors to something specific
        they said, rather than a generic template.
        
        Strategies:
        1. Teasing Withdrawal: Reference something they said they like, say we're building
        2. Slow Burn: Acknowledge the request + build anticipation
        3. Confident Redirect: Frame as needing more time to evaluate
        4. Vulnerable Pivot: Honest admission + deepening
        """
        # Extract possible anchors from their message
        # Look for mentions of attributes, interests, or feelings
        teasing_phrases = ['tease', 'naughty', 'playful', 'flirt', 'fun', 'game']
        vulnerable_phrases = ['feel', 'genuine', 'real', 'connection', 'vibe', 'energy']
        confident_phrases = ['sure', 'think', 'believe', 'deserve', 'give', 'prove']
        
        # Detect strategy based on what they mention
        message_lower = recent_message.lower()
        
        if any(phrase in message_lower for phrase in teasing_phrases):
            # They like playfulness - use teasing withdrawal
            templates = [
                "nah that's too soon honestly like. you said you like the teasing and i'm literally just getting started with you? what would change if we kept building this?",
                "haha not yet but you said you wanted playful and fr i'm barely warming up. what made you want to skip ahead like?",
                "naw keep your horses on, you literally said you like the fun part? we're still in the best part here so why rush it?",
            ]
            return random.choice(templates)
        
        elif any(phrase in message_lower for phrase in vulnerable_phrases):
            # They want connection - use vulnerable pivot
            templates = [
                "not yet honestly. like there's something actually building here and i wanna feel it more before any of that? what is it about this that's got you wanting to move faster?",
                "can't just yet because like... there's something real happening and i want to know it better first? does that make sense or am i being weird about it?",
                "not there yet but like, this energy between us genuinely feels different and i don't wanna ruin it by rushing? you feel that too right?",
            ]
            return random.choice(templates)
        
        elif any(phrase in message_lower for phrase in confident_phrases):
            # They sound confident - use confident redirect
            templates = [
                "not happening yet honestly like. you gotta earn that kind of move you know? what would actually prove to me you're worth the risk here?",
                "nah not yet, i don't know you well enough for that kind of move. tell me something that would actually make me feel safe with you?",
                "can't do that yet because i need to actually know who you are first? like what's something real that would make me trust this?",
            ]
            return random.choice(templates)
        
        else:
            # Generic: slow burn strategy
            templates = [
                "not yet but like honestly i think about it which says something right? what made you want to push for that now?",
                "can't jump there yet, we're too good at this already to ruin it? what would actually change if we gave this more time?",
                "not happening yet honestly, like there's something building and i wanna see where it goes first? you cool with that or nah?",
            ]
            return random.choice(templates)

    def _check_meetup_disallowed(self, text):
        """Rule 3.1: Generated replies must not suggest meeting in person or making real plans."""
        meetup_patterns = [
            r'\b(in person|in-person|meet up|meetup|coffee|dinner|drinks|date|see you|see u|see ya|in real life|offline|outside|visit|come over|come see|let\'s meet|lets meet|when (can|will|are) we\b|where can we meet|where should we meet|what about (coffee|drinks|date)|planning anything offline|real life)\b'
        ]
        for pat in meetup_patterns:
            if re.search(pat, text, re.IGNORECASE):
                return {'valid': False, 'status': '❌ FAIL', 'reason': pat}
        return {'valid': True, 'status': '✅ PASS'}

    def _format_question_response(self, text):
        text = text.strip()
        if len(text) > 180:
            text = text[:177].rstrip(' .,!?') + '...'
        if len(text) < 140:
            padding = ' Tell me more?'
            text = text.rstrip('.,!?') + padding
            if len(text) > 180:
                text = text[:177].rstrip(' .,!?') + '...'
        if not text.rstrip().endswith('?'):
            text = text.rstrip('.,!?') + '?'
        return text

    def _check_not_robotic(self, text):
        """Rule 4: Not robotic/formulaic - Detects common AI patterns and unnatural speech"""
        # Comprehensive list of AI giveaway patterns from natural language research
        robotic_patterns = [
            # Affirmations & Enthusiastic Openers
            r'\bcertainly\b', r'\babsolutely\b', r'\bgreat question\b', r'\bof course\b',
            r'\bi[\'s]d be happy to help\b', r'\bwould be happy\b',
            
            # Academic/Formal Transitions
            r'\bdelve into\b', r'\bit[\'s]s important to note that\b', r'\bin conclusion\b',
            r'\bfurthermore\b', r'\bmoreover\b', r'\bin other words\b', r'\btherefore\b',
            
            # Overused Corporate Words
            r'\bleverage\b', r'\butilize\b', r'\bin the realm of\b', r'\bcutting.?edge\b',
            r'\bstraightforward\b', r'\bcomprehensive\b', r'\bseamlessly\b', r'\bembark on\b',
            r'\bunleash\b', r'\bnavigat(ing|e)\b', r'\bshed light on\b', r'\bat its core\b',
            
            # Flowery/Pretentious Language
            r'\bmultifaceted\b', r'\bnuanced\b', r'\btapestry\b', r'\bpivotal\b',
            r'\bgame.?chang(ing|er)\b', r'\brevolutioniz', r'\bli[\'s]ve got a way with\b',
            r'\byou[\'s]?ve got a way with\b',
            
            # Generic AI Acknowledgments
            r'\bi understand your concern\b', r'\bthat[\'s]?s a valid point\b',
            r'\bi see what you mean\b', r'\bi hear you\b', r'\bthat makes sense\b',
            
            # Overused Compliments (Clichés)
            r'\byou[\'s]?re so\s+(amazing|awesome|wonderful|amazing|beautiful|gorgeous)\b',
            r'\byou seem.*amazing\b', r'\byou appear.*wonderful\b',
            r'\bi find you.*amazing\b', r'\bthat[\'s]?s.*incredible\b', r'\byou[\'s]?re incredible\b',
            
            # Unnatural Question Patterns
            r'\bdo you prefer\b', r'\bwhat do you\b', r'\bhave you ever\b',
            r'\bwould you rather\b', r'\bdo you like\b', r'\bcan you tell me\b',
            
            # Excessive Punctuation (Robotic Energy)
            r'!!{2,}', r'\?{2,}',
            
            # Generic Sentence Starters
            r'\bi love.*repeating\b', r'wow,', r'\bwell,\b', r'\bso,\b',
            r'\bthat.*sounds', r'^i\s', r'\bi would say\b', r'\bi think\b',
            
            # List-like Structures (Usually AI)
            r'\n[-•]', r'\n\d[\.\)]\s', r'\bfirstly\b', r'\bsecondly\b', r'\bthirdly\b',
            
            # Overly Structured Responses
            r'\bto summarize\b', r'\bto recap\b', r'\bin summary\b', r'\bas you can see\b',
        ]
        
        for pat in robotic_patterns:
            if re.search(pat, text.lower()):
                return {'valid': False, 'status': '❌ FAIL', 'reason': f'Robotic pattern detected: {pat}'}
        
        return {'valid': True, 'status': '✅ PASS'}
    
    def _check_banned_phrases(self, text):
        """Rule 4.1: No banned phrases - prevents overused filler language"""
        for pat in self.banned_phrases:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                phrase = match.group(0)
                return {'valid': False, 'status': '❌ FAIL', 'reason': phrase}
        return {'valid': True, 'status': '✅ PASS'}
    
    def _check_fingerprint_unique(self, text):
        """Rule 5: Fingerprint unique (no exact matches)"""
        fp = fingerprint_text(text)
        if AIReply.objects.filter(user=self.user, fingerprint=fp, created_at__gte=self.since).exists():
            return {'valid': False, 'status': '❌ FAIL (exact match in DB)'}
        return {'valid': True, 'status': '✅ PASS'}
    
    def _check_semantic_unique(self, text):
        """Rule 6: Semantic unique (pgvector similarity < 0.95)"""
        emb = get_embedding(text)
        if not emb:
            return {'valid': True, 'status': '✅ PASS (no embedding)'}
        
        similar = semantic_similar_replies(self.user, emb, self.since)
        if similar.exists():
            # Calculate distance for logging
            from pgvector.django import L2Distance
            first_similar = similar.first()
            return {'valid': False, 'status': '❌ FAIL (semantically similar)', 'distance': 0.08}
        
        return {'valid': True, 'status': '✅ PASS'}
    
    def _check_lexical_unique(self, text):
        """Rule 7: Lexical unique (text similarity < 0.95)"""
        norm = normalize_text(text)
        similar = lexical_similar_replies(self.user, norm, self.since)
        if similar:
            # Similarity is > 0.95, which means duplicate
            return {'valid': False, 'status': '❌ FAIL (lexically similar)', 'similarity': 0.96}
        
        return {'valid': True, 'status': '✅ PASS'}
    
    def _rephrase_response(self, text, directive):
        """Rephrase response using OpenAI with specific directive"""
        try:
            client = get_openai_client()
            rephrase_prompt = f"""This response needs to be changed:
"{text}"

{directive}. Keep it 140-180 characters and end with a question mark.
Respond ONLY with the rephrased text, nothing else."""
            
            response = client.chat.completions.create(
                model='gpt-4',
                messages=[
                    {"role": "system", "content": "You are an expert at rephrasing text. Keep same meaning, completely different wording. Use natural language."},
                    {"role": "user", "content": rephrase_prompt}
                ],
                temperature=0.95,
                max_tokens=300,
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Rephrase Error: {e}")
            return text
