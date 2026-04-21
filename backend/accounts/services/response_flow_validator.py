"""
Conversation Flow Validator

Implements the LISTEN → RELATE → DIG DEEPER pattern for authentic responses.
This ensures every response:
1. LISTENS - Acknowledges what was said
2. RELATES - Adds perspective or emotion
3. DIG DEEPER - Asks a question that goes emotionally deeper
"""

import re
from typing import Dict, Tuple


class ListenRelateDeeperValidator:
    """Validates responses follow the LISTEN → RELATE → DIG DEEPER pattern"""
    
    def __init__(self):
        # Keywords that indicate each component
        self.listen_patterns = [
            r'\b(yeah|yep|right|okay|ok|sounds|makes sense|get it|i hear|i see|totally|absolutely|definitely|for sure|no doubt)\b',
            r'\b(that.*makes sense|that.*cool|that.*awesome|that.*interesting)\b',
            r'\b(so.*you|so.*that|so.*like)\b',  # Rephrasing what they said
        ]
        
        self.relate_patterns = [
            r'\b(i|me|my|we|us|our|feel|think|understand|know|experience|relate|similar|too|also)\b',
            r'\b(same here|me too|same thing|similar.*situation|know.*feeling|understand.*that)\b',
        ]
        
        self.deeper_patterns = [
            r'\?$',  # Ends with question
            r'\b(what.*|when.*|where.*|how.*|why.*|tell me|ask|curious|wonder|interested)\b.*\?',
        ]
        
    def validate_listen_relate_deeper(self, response_text: str, last_message: str = None) -> Dict:
        """
        Validate that response follows LISTEN → RELATE → DIG DEEPER pattern.
        
        Returns:
        {
            'has_listen': bool,
            'has_relate': bool,
            'has_deeper': bool,
            'is_valid': bool,
            'issues': [str],
            'suggestions': [str],
            'score': float (0-1)
        }
        """
        issues = []
        suggestions = []
        
        # Check for LISTEN component
        has_listen = self._check_listen(response_text, last_message)
        if not has_listen:
            issues.append("missing_listen")
            suggestions.append("Start by acknowledging what they said (yeah, that makes sense, I hear you, etc.)")
        
        # Check for RELATE component
        has_relate = self._check_relate(response_text)
        if not has_relate:
            issues.append("missing_relate")
            suggestions.append("Add your own perspective or feeling (I feel, I think, I relate to that, me too, etc.)")
        
        # Check for DEEPER component
        has_deeper = self._check_deeper(response_text)
        if not has_deeper:
            issues.append("missing_deeper")
            suggestions.append("End with a question that digs emotionally deeper than their statement")
        
        # Calculate score
        components_present = sum([has_listen, has_relate, has_deeper])
        score = components_present / 3.0
        
        return {
            'has_listen': has_listen,
            'has_relate': has_relate,
            'has_deeper': has_deeper,
            'is_valid': score >= 0.66,  # At least 2 of 3 components
            'issues': issues,
            'suggestions': suggestions,
            'score': score,
            'components_present': f"{components_present}/3"
        }
    
    def _check_listen(self, response_text: str, last_message: str = None) -> bool:
        """Check if response acknowledges what was said"""
        text = response_text.lower()
        
        # Check for listen patterns
        has_listen_pattern = any(re.search(pat, text) for pat in self.listen_patterns)
        
        if has_listen_pattern:
            return True
        
        # If last message provided, check if response references specific content
        if last_message:
            last_lower = last_message.lower()
            # Extract key nouns from last message
            keywords = re.findall(r'\b([a-z]{4,})\b', last_lower)
            # Check if response includes any of those keywords
            if keywords and any(kw in text for kw in keywords):
                return True
        
        return False
    
    def _check_relate(self, response_text: str) -> bool:
        """Check if response adds personal perspective"""
        text = response_text.lower()
        
        # Must reference self (I, me, my, we, us)
        self_patterns = [r'\b(i\'m|i am|i|me|my|we|us|our)\b']
        has_self = any(re.search(pat, text) for pat in self_patterns)
        
        # And must have something personal - feeling, opinion, experience
        personal_patterns = [
            r'\b(feel|think|believe|know|understand|experience|relate|similar|too|also)\b',
            r'\b(i|me).*\b(feel|think|love|hate|want|need|experience|understand)\b',
        ]
        has_personal = any(re.search(pat, text) for pat in personal_patterns)
        
        return has_self and has_personal
    
    def _check_deeper(self, response_text: str) -> bool:
        """Check if response ends with a question"""
        text = response_text.strip()
        
        # Must end with question mark
        if not text.endswith('?'):
            return False
        
        # Question should be open-ended, not yes/no (though yes/no is okay sometimes)
        # Just check it ends with ? which indicates engagement
        return True
    
    def suggest_pattern_for_response(self, last_message_text: str, conversation_flow: str, 
                                     is_sexual: bool) -> str:
        """
        Generate a template/suggestion for LISTEN → RELATE → DIG DEEPER response.
        """
        templates = {
            'sexual': {
                'listen': [
                    "yeah that's so hot,",
                    "okay that turns me on,",
                    "god that's sexy,",
                    "ugh that's so fucking hot,",
                    "that's exactly what i want,",
                ],
                'relate': [
                    "i feel the same way about you",
                    "i'm so into that too",
                    "i get that kind of energy",
                    "i love that side of you",
                    "that matches what i'm looking for",
                ],
                'deeper': [
                    "what's your biggest fantasy with me?",
                    "where would you actually go for real?",
                    "what gets you crazy about me specifically?",
                    "would you want to actually try it?",
                    "what else have you been wanting to do?",
                ]
            },
            'emotional': {
                'listen': [
                    "i hear what you're saying,",
                    "that makes total sense,",
                    "i get why you feel that,",
                    "yeah that resonates with me,",
                    "okay i see what you mean,",
                ],
                'relate': [
                    "i feel similarly about this",
                    "i've been thinking the same thing",
                    "i relate to that completely",
                    "i want that too honestly",
                    "that's exactly how i feel",
                ],
                'deeper': [
                    "is that something you want to explore with me?",
                    "what would actually make that happen?",
                    "how deep do you want to go with this?",
                    "are you scared about it or excited?",
                    "what's holding you back from doing it?",
                ]
            },
            'logistics': {
                'listen': [
                    "yeah that makes sense,",
                    "i get that situation,",
                    "totally understand that,",
                    "okay so that's what's happening,",
                    "that's important info,",
                ],
                'relate': [
                    "i've dealt with that too",
                    "i respect how you're handling it",
                    "that's something i think about",
                    "i'm in a similar spot honestly",
                    "that matters to me as well",
                ],
                'deeper': [
                    "how does that affect what we're doing?",
                    "what does that mean for us going forward?",
                    "would that change how we connect?",
                    "how important is that to your life?",
                    "does that mean we can still make this work?",
                ]
            }
        }
        
        # Determine which template set to use
        if is_sexual:
            template_set = templates['sexual']
        elif 'emotional_connection' in conversation_flow or 'emotionally' in conversation_flow:
            template_set = templates['emotional']
        else:
            template_set = templates['logistics'] if 'logistics' in conversation_flow else templates['emotional']
        
        # Build suggestion
        listen = template_set['listen'][0] if template_set['listen'] else ""
        relate = template_set['relate'][0] if template_set['relate'] else ""
        deeper = template_set['deeper'][0] if template_set['deeper'] else ""
        
        return f"{listen} {relate} {deeper}"


class TopicClassifier:
    """Classifies messages by topic to determine appropriate response tone"""
    
    TOPIC_PATTERNS = {
        'sexual_intimacy': [
            r'\b(sex|fucking|fuck|cum|orgasm|horny|aroused|erection|dick|pussy|cock|breast|ass|body|naked|strip|penetrate|thrust|foreplay)\b',
            r'\b(intimate|passionate|sensual|touch|kiss|caress|handsy)\b',
            r'\b(desire|want you|need you|crave|desperate)\b.*\b(sexual|sex|physical|touch|body|intimacy)\b',
        ],
        'romantic_connection': [
            r'\b(love|adore|cherish|care about|mean to me|special|perfect match|chemistry|connection)\b',
            r'\b(together|us|we|relationship|future|commitment|forever|commitment)\b',
            r'\b(emotional|feelings|vulnerable|open up|trust|believe)\b',
        ],
        'meeting_logistics': [
            r'\b(meet|visit|coffee|dinner|drink|lunch|breakfast|phone number|address|location|travel|flight)\b',
            r'\b(when|where|time|schedule|availability|weekend|soon|planning)\b.*\b(meet|visit|see)\b',
            r'\b(come (over|to|visit|see)|go (out|to|visit)|get (together|to))\b',
        ],
        'family_matters': [
            r'\b(son|daughter|kids|children|family|mother|father|parent|brother|sister|niece|nephew)\b',
            r'\b(have children|raising|custody|responsibility|parents)\b',
            r'\b(grandchildren|step-\w+|ex-\w+)\b',
        ],
        'health_wellness': [
            r'\b(headache|migraine|sick|ill|pain|hurt|disease|cancer|depression|anxiety|mental health|therapy)\b',
            r'\b(exercise|fitness|gym|diet|health|wellness|medicine|medication|doctor|hospital)\b',
            r'\b(medication|aspirin|blood thinner|thinners)\b',
        ],
        'personal_challenges': [
            r'\b(stressed|stress|worried|concern|problem|issue|difficult|challenge|hard time|struggling)\b',
            r'\b(money|financial|broke|expensive|cost|afford|payment|coins)\b',
            r'\b(work|job|career|boss|coworker|employment|quit|fired)\b',
        ],
        'lifestyle_interests': [
            r'\b(beach|vacation|travel|trip|adventure|explore|hike|sports|hobby|interest|passion)\b',
            r'\b(wine|beer|drinks|party|club|dancing|music|movie|art|book)\b',
            r'\b(restaurant|food|cooking|chef|cuisine|eat|taste)\b',
        ],
    }
    
    @staticmethod
    def classify_topic(message_text: str) -> Dict[str, bool]:
        """
        Classify message into topics.
        
        Returns dict of {topic: is_present}
        """
        text = message_text.lower()
        topics = {}
        
        for topic, patterns in TopicClassifier.TOPIC_PATTERNS.items():
            found = any(re.search(pat, text, re.IGNORECASE) for pat in patterns)
            topics[topic] = found
        
        return topics
    
    @staticmethod
    def get_primary_topic(message_text: str) -> str:
        """Get the primary/most relevant topic for a message"""
        topics = TopicClassifier.classify_topic(message_text)
        
        # Return first topic that matches (in priority order)
        priority_order = [
            'sexual_intimacy',
            'romantic_connection',
            'meeting_logistics',
            'family_matters',
            'health_wellness',
            'personal_challenges',
            'lifestyle_interests',
        ]
        
        for topic in priority_order:
            if topics[topic]:
                return topic
        
        return 'general_conversation'
    
    @staticmethod
    def get_response_tone_for_topic(topic: str) -> str:
        """
        Get recommended response tone for a topic.
        
        Returns: 'sexual', 'romantic', 'warm', 'supportive', 'friendly', 'casual'
        """
        tone_map = {
            'sexual_intimacy': 'sexual',
            'romantic_connection': 'romantic',
            'meeting_logistics': 'casual',
            'family_matters': 'warm',
            'health_wellness': 'supportive',
            'personal_challenges': 'supportive',
            'lifestyle_interests': 'friendly',
        }
        
        return tone_map.get(topic, 'friendly')
