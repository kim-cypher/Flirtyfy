"""
Specificity Extractor — Extract actual phrases and observations from user messages
Instead of generic compliments, reference SPECIFIC things they said
"""

import re
from typing import Dict, List

class SpecificityExtractor:
    """Extract specific phrases and patterns from user text that responses should reference"""
    
    @staticmethod
    def extract_specific_phrases(text: str) -> Dict:
        """
        Extract specific, quotable phrases and observations
        NOT abstract descriptors like 'energy' or 'confidence'
        """
        text_lower = text.lower()
        
        extracted = {
            'direct_questions': [],      # Questions they asked
            'declarative_statements': [], # What they said about themselves
            'unusual_phrasings': [],      # How they phrased something different
            'emotional_reveals': [],      # Things that show emotion/vulnerability
            'action_indicators': [],      # Things they do or want to do
            'specificity_anchors': []     # Specific to THIS conversation
        }
        
        # ===== DIRECT QUESTIONS =====
        # Find what they're actually asking
        questions = re.findall(r'([^.?!]*\?)', text)
        extracted['direct_questions'] = [q.strip() for q in questions if q.strip()]
        
        # ===== DECLARATIVE STATEMENTS =====
        # Extract "I am", "I like", "I want", "I've", "I do" statements
        declarations = re.findall(
            r"(i\s+(?:am|like|want|need|enjoy|think|believe|'ve|do|don't|can't|could|would|should|love|hate|prefer|wish|hope|dream)\s+[^.?!]+)",
            text_lower, re.IGNORECASE
        )
        extracted['declarative_statements'] = declarations
        
        # ===== EMOTIONAL REVEALS =====
        # Look for vulnerability markers
        emotional_keywords = [
            'scared', 'nervous', 'anxious', 'worried', 'excited', 'thrilled',
            'heartbroken', 'lonely', 'sad', 'depressed', 'happy', 'joyful',
            'frustrated', 'angry', 'confused', 'uncertain', 'vulnerable',
            'shy', 'insecure', 'confident', 'proud', 'ashamed', 'embarrassed'
        ]
        for keyword in emotional_keywords:
            if keyword in text_lower:
                # Find the sentence containing this word
                sentences = re.split(r'[.!?]', text)
                for sent in sentences:
                    if keyword in sent.lower():
                        extracted['emotional_reveals'].append(sent.strip())
        
        # ===== ACTION INDICATORS =====
        # What are they doing or want to do?
        action_verbs = [
            'go', 'visit', 'travel', 'meet', 'come', 'see', 'watch', 
            'do', 'try', 'learn', 'explore', 'discover', 'take', 'make'
        ]
        for verb in action_verbs:
            pattern = rf"\b{verb}\s+(?:to\s+)?[^.?!{{]*"
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            extracted['action_indicators'].extend(matches)
        
        # ===== UNUSUAL PHRASINGS =====
        # Look for distinctive word choices or structures
        sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
        # Pick sentences that aren't standard questions (keep the interesting ones)
        extracted['unusual_phrasings'] = [
            s for s in sentences 
            if len(s.split()) > 3 and '?' not in s
        ][:3]  # Top 3 interesting statements
        
        # ===== SPECIFICITY ANCHORS =====
        # Find things that make this DIFFERENT from other conversations
        specific_references = []
        
        # Look for proper nouns (places, names)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        specific_references.extend(proper_nouns)
        
        # Look for numbers/dates/times
        numbers_dates = re.findall(r'\b(?:\d{1,2}:\d{2}|tomorrow|today|tonight|next\s+\w+|this\s+\w+)\b', 
                                   text, re.IGNORECASE)
        specific_references.extend(numbers_dates)
        
        # Look for specific activities/interests
        interests = re.findall(
            r'\b(?:love|adore|obsessed|fan of|into|crazy about|into|passionate about)\s+([^.?!,]+)',
            text, re.IGNORECASE
        )
        specific_references.extend(interests)
        
        extracted['specificity_anchors'] = list(set(specific_references))
        
        return extracted
    
    @staticmethod
    def get_response_anchor(extracted: Dict) -> str:
        """
        Get the BEST specific thing to reference in a response
        Priority: direct question > emotional reveal > action indicator > phrasing > statement
        """
        # Best targets for reference (in priority order)
        if extracted['direct_questions']:
            return extracted['direct_questions'][0]  # What they asked
        
        if extracted['emotional_reveals']:
            return extracted['emotional_reveals'][0]  # What they revealed
        
        if extracted['action_indicators']:
            return extracted['action_indicators'][0]  # What they want to do
        
        if extracted['specificity_anchors']:
            return extracted['specificity_anchors'][0]  # Specific place/time/interest
        
        if extracted['unusual_phrasings']:
            return extracted['unusual_phrasings'][0]  # How they said it
        
        if extracted['declarative_statements']:
            return extracted['declarative_statements'][0]  # What they said about self
        
        return None
    
    @staticmethod
    def build_specific_reference(extract_dict: Dict, text: str) -> str:
        """
        Build a phrase-specific response anchor
        E.g., "the way you said X" or "what you asked about Y"
        """
        anchor = SpecificityExtractor.get_response_anchor(extract_dict)
        
        if not anchor:
            return None
        
        # Determine what TYPE of anchor this is and build reference accordingly
        if anchor in extract_dict['direct_questions']:
            # Reference their question
            return f"when you asked me {anchor.lower()}"
        
        elif any(anchor in e for e in extract_dict['emotional_reveals']):
            # Reference their emotional reveal
            return f"the fact that you {anchor.lower().strip('?')}"
        
        elif any(anchor in a for a in extract_dict['action_indicators']):
            # Reference their action/desire
            phrase = anchor.strip()
            return f"that you want to {phrase}"
        
        elif anchor in extract_dict['specificity_anchors']:
            # Reference specific thing (place, time, interest, name)
            return f"the thing about {anchor.lower()}"
        
        else:
            # Generic reference to what they said
            # Find first few words
            words = anchor.split()[:4]
            snippet = ' '.join(words)
            return f"the way you put that — '{snippet}...'"
    
    @staticmethod
    def is_generic_response(response: str) -> bool:
        """Check if response uses generic descriptors instead of specific references"""
        
        # BANNED generic openers (from 50-response analysis)
        generic_openers = [
            "you have a way of",
            "you have that",
            "you have a kind of",
            "there is something about",
            "there is a certain",
            "there is a very",
            "the way you",  # when used as true opener
            "i can feel",
            "i would be lying if",
            "i like the way you",
            "i do not know what is more",
            "i think you enjoy",
            "you seem to know",
            "you are making this feel",
            "you are very good at",
            "you make",
        ]
        
        response_lower = response.lower()
        return any(opener in response_lower for opener in generic_openers)


def extract_specificity_from_conversation(text: str) -> Dict:
    """Main entry point"""
    extractor = SpecificityExtractor()
    extracted = extractor.extract_specific_phrases(text)
    
    return {
        'extracted': extracted,
        'anchor': extractor.get_response_anchor(extracted),
        'reference': extractor.build_specific_reference(extracted, text),
        'is_generic': False  # Will be checked in response validation
    }
