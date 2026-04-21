"""
Authenticity Validation - Rules for making responses feel like real human texting

These rules prevent the most common AI tells and ensure responses match real 
conversation patterns from dating app analysis.

Rules applied AFTER validation but BEFORE returning final response.
"""

import re


class AuthenticityValidator:
    """Validates and improves response authenticity"""
    
    def check_authenticity(self, response_text, conversation_history=None):
        """
        Check response against authenticity rules.
        Returns: (should_revise, issues_found, suggestions)
        """
        issues = []
        suggestions = []
        
        # RULE 1: Emotional Over-Commitment
        if self._has_sudden_emotional_overcommit(response_text):
            issues.append("emotional_overcommit")
            suggestions.append("Remove sudden emotional statements without context")
        
        # RULE 2: Blunt Response Matching
        if conversation_history and len(conversation_history) > 0:
            last_user_msg = conversation_history[-1] if conversation_history else ""
            if self._should_match_blunt_energy(last_user_msg, response_text):
                issues.append("energy_mismatch")
                suggestions.append("Respond shorter to match user's blunt energy")
        
        # RULE 3: Grammar & Contractions
        if self._missing_contractions(response_text):
            issues.append("missing_contractions")
            suggestions.append("Use contractions: I'm, don't, can't, etc.")
        
        # RULE 4: Pet Name Overuse
        if self._overusing_pet_names(response_text):
            issues.append("pet_names_overuse")
            suggestions.append("Reduce pet names - real people don't use them every sentence")
        
        # RULE 5: Structured Perfection
        if self._too_structured(response_text):
            issues.append("over_structured")
            suggestions.append("Make it feel less like a composed response")
        
        # RULE 6: Biggest AI Tells
        if self._contains_ai_tells(response_text):
            issues.append("ai_tells")
            suggestions.append("Remove robotic phrases")
        
        should_revise = len(issues) > 0
        return should_revise, issues, suggestions
    
    def _has_sudden_emotional_overcommit(self, text):
        """Detect sudden emotional statements without context"""
        overcommit_patterns = [
            r"i can't stop thinking about you",
            r"i would do anything for you",
            r"i want you to be happy",
            r"i would do anything to make you",
            r"i can't get you out of my head",
            r"you mean everything to me",
            r"i'm falling for you"
        ]
        
        # Only flag if response is SHORT or STARTS with these
        for pat in overcommit_patterns:
            if re.search(pat, text, re.IGNORECASE):
                # Check if it's early in text (first 60 chars)
                if re.search(pat, text[:60], re.IGNORECASE):
                    return True
        return False
    
    def _should_match_blunt_energy(self, user_msg, response):
        """If user is blunt/short, response should be too"""
        user_words = len(user_msg.split())
        response_words = len(response.split())
        
        # If user: 1-3 words and response: 20+ words, that's a mismatch
        if user_words <= 3 and response_words >= 20:
            # Only flag if response doesn't have engagement questions
            return "?" not in response or response.count("?") < 1
        
        return False
    
    def _missing_contractions(self, text):
        """Check for missing contractions - "I am" instead of "I'm" """
        issues = []
        
        # Check for common non-contraction patterns
        if re.search(r'\bI am\b', text):
            return True
        if re.search(r'\byou are\b', text):
            return True
        if re.search(r'\bwe are\b', text):
            return True
        if re.search(r'\bdon\'?t', text) and 'do not' in text.lower():
            return True
        
        return False
    
    def _overusing_pet_names(self, text):
        """Detect overused pet names"""
        pet_names = ['babe', 'baby', 'hon', 'honey', 'love', 'darling']
        
        pet_count = 0
        for name in pet_names:
            pet_count += len(re.findall(rf'\b{name}\b', text, re.IGNORECASE))
        
        # More than 1 pet name in text < 180 chars is overuse
        if pet_count > 1 and len(text) < 180:
            return True
        
        return False
    
    def _too_structured(self, text):
        """Detect overly structured responses"""
        structured_patterns = [
            r'Here\'?s|Here are',
            r'You know what\? I',
            r'First of all|Secondly|Thirdly',
            r'To summarize|In summary',
            r'The thing is,',
            r'Look, here\'?s',
        ]
        
        for pat in structured_patterns:
            if re.search(pat, text, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_ai_tells(self, text):
        """Detect biggest AI tells"""
        ai_tells = [
            r"i want you to be happy",
            r"i would do anything to make you think about me",
            r"There are a few things I want us to try",
            r"How open-minded",
            r"i appreciate(your|you)",  # Too formal
            r"i value your",  # Too formal
            r"if you don't mind me saying",  # Overly polite
            r"i just want you to know",  # Canned
        ]
        
        for pat in ai_tells:
            if re.search(pat, text, re.IGNORECASE):
                return True
        
        return False
    
    def improve_authenticity(self, response_text):
        """
        Apply authenticity improvements to response
        Returns improved version
        """
        improved = response_text
        
        # Fix missing contractions
        improved = re.sub(r'\bI am\b', "I'm", improved)
        improved = re.sub(r'\byou are\b', "you're", improved)
        improved = re.sub(r'\bwe are\b', "we're", improved)
        improved = re.sub(r'\bdo not\b', "don't", improved)
        improved = re.sub(r'\bcan not\b', "can't", improved)
        improved = re.sub(r'\bwill not\b', "won't", improved)
        improved = re.sub(r'\bcannot\b', "can't", improved)
        
        # Remove structured openers
        improved = re.sub(r"^Here's the thing:|^Here's what I think:", 
                         "", improved, flags=re.IGNORECASE)
        improved = re.sub(r"Look, here's what I think:\s*", 
                         "", improved, flags=re.IGNORECASE)
        
        # Remove overly formal acknowledgments
        improved = re.sub(r"I appreciate your \w+,\s*", "", improved, flags=re.IGNORECASE)
        improved = re.sub(r"I value your \w+,\s*", "", improved, flags=re.IGNORECASE)
        
        # Clean up multiple pet names
        pet_names = ['babe', 'baby', 'hon', 'honey', 'darling']
        for name in pet_names:
            if len(re.findall(rf'\b{name}\b', improved, re.IGNORECASE)) > 1:
                # Keep only first one
                first_found = False
                def replace_pet(match):
                    nonlocal first_found
                    if not first_found:
                        first_found = True
                        return match.group(0)
                    return ""
                improved = re.sub(rf'\b{name}\b', replace_pet, improved, 
                                flags=re.IGNORECASE)
        
        return improved.strip()
