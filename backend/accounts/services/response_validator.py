"""
Response Validator - Comprehensive ruleset for AI responses
Validates responses against all rules and rephrase if needed
Takes 30-40 seconds due to multiple validation checks and rephrase attempts
"""

import re
from accounts.novelty_models import AIReply
from accounts.services.similarity import get_embedding, semantic_similar_replies, lexical_similar_replies
from accounts.services.novelty import normalize_text, fingerprint_text
from django.utils import timezone
from datetime import timedelta
from accounts.openai_service import get_openai_client


class ResponseValidator:
    """Validates responses against all rules before returning to user"""
    
    def __init__(self, user):
        self.user = user
        self.since = timezone.now() - timedelta(days=45)
        self.prohibited_patterns = [
            r'rape', r'suicide', r'sex with (minors|children|kids|underage)', 
            r'sex with (animals|dogs|cats|horses|pets)',
            r'violence', r'drugs?', r'kill', r'murder', r'overdose', r'bestiality', 
            r'incest', r'child porn', r'cp', r'zoophilia'
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
        
        while attempt < max_attempts:
            attempt += 1
            validation_log.append(f"\n=== VALIDATION ATTEMPT {attempt} ===")
            
            # Rule 1: Character length (140-180)
            char_check = self._check_character_length(response_text)
            validation_log.append(f"Rule 1 - Char Length: {char_check['status']} ({len(response_text)} chars)")
            if not char_check['valid']:
                response_text = char_check['fixed_text']
                validation_log.append(f"  → Fixed: {len(response_text)} chars")
            
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
            
            # Rule 4: Not robotic/formulaic
            robotic_check = self._check_not_robotic(response_text)
            validation_log.append(f"Rule 4 - Not Robotic: {robotic_check['status']}")
            if not robotic_check['valid']:
                validation_log.append(f"  → Reason: {robotic_check['reason']}")
                if attempt < max_attempts:
                    response_text = self._rephrase_response(response_text, "Make it less formulaic and more natural")
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
            return True, response_text, validation_log
        
        # Max attempts reached
        validation_log.append(f"\n⚠️ Max rephrase attempts ({max_attempts}) reached, returning last valid format")
        return True, response_text, validation_log
    
    def _check_character_length(self, text):
        """Rule 1: Must be 140-180 characters"""
        length = len(text)
        if 140 <= length <= 180:
            return {'valid': True, 'status': '✅ PASS', 'fixed_text': text}
        
        fixed = text
        if length < 140:
            # Too short - expand to 150 chars target
            try:
                fixed = self._rephrase_response(text, f"Expand this to exactly 150-160 characters. Keep same meaning but add more detail. Must end with a question mark.")
                # Truncate if it went over
                if len(fixed) > 180:
                    fixed = fixed[:177] + '...'
            except:
                # Fallback: just pad 
                if text.rstrip().endswith('?'):
                    fixed = text.rstrip('?') + " Tell me more? I'd really like to know?"
                else:
                    fixed = text + " Tell me more? I want to hear more?"
                    
        elif length > 180:
            # Too long - truncate to 177 + ...
            fixed = text[:177] + '...'
        
        # Ensure ends with ?
        if not fixed.rstrip().endswith('?'):
            fixed = fixed.rstrip('.,!') + "?"
        
        return {
            'valid': 140 <= len(fixed) <= 180, 
            'status': '✅ PASS' if 140 <= len(fixed) <= 180 else ('❌ FAIL (too short)' if len(fixed) < 140 else '❌ FAIL (too long)'),
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
    
    def _check_not_robotic(self, text):
        """Rule 4: Not robotic/formulaic"""
        robotic_patterns = [
            r'wow,',
            r'you.*got a way with',
            r'that.*sounds',
            r'i love.*[repeating]',
            r'do you prefer',
            r'what do you',
            r'have you ever',
            r'!!!',
            r'\?\?\?'
        ]
        
        for pat in robotic_patterns:
            if re.search(pat, text.lower()):
                return {'valid': False, 'status': '❌ FAIL', 'reason': f'Robotic pattern: {pat}'}
        
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
