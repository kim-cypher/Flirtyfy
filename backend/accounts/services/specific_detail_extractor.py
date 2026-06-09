"""
SpecificDetailExtractor: Identifies one concrete detail from the user's message to reference.
Ensures the reply mentions something specific, not generic observations.
"""
import re
from typing import Optional


class SpecificDetailExtractor:
    """
    Extracts a single specific, concrete detail from the user's message.
    Prioritizes: topics mentioned, emotions, actions, questions asked.
    """
    
    # Work/Career/Professional context
    WORK_KEYWORDS = [
        "work", "job", "boss", "colleague", "meeting", "project", "deadline",
        "office", "remote", "startup", "company", "client", "presentation",
        "promotion", "raise", "fired", "quit", "career", "interview", "hired",
    ]
    
    # Hobbies/Interests/Activities
    HOBBY_KEYWORDS = [
        "art", "music", "sport", "game", "read", "write", "travel", "cook",
        "hike", "dance", "yoga", "gym", "run", "swim", "bike", "draw", "paint",
        "movie", "show", "podcast", "blog", "photo", "guitar", "piano", "sing",
    ]
    
    # Relationships/Social
    RELATIONSHIP_KEYWORDS = [
        "friend", "family", "sister", "brother", "mom", "dad", "parent",
        "crush", "ex", "relationship", "dating", "marriage", "partner",
        "alone", "lonely", "social", "group", "community",
    ]
    
    # Emotions/Feelings
    EMOTION_KEYWORDS = [
        "happy", "sad", "angry", "anxious", "stressed", "tired", "excited",
        "scared", "nervous", "frustrated", "confused", "overwhelmed", "lonely",
        "grateful", "proud", "ashamed", "embarrassed", "jealous", "envious",
    ]
    
    # Places/Locations
    PLACE_KEYWORDS = [
        "home", "house", "apartment", "city", "beach", "mountain", "park",
        "coffee", "bar", "restaurant", "cafe", "gym", "library", "office",
    ]
    
    # Time/Period references
    TIME_KEYWORDS = [
        "morning", "night", "weekend", "vacation", "holiday", "tonight",
        "tomorrow", "yesterday", "last week", "soon", "later", "this week",
    ]
    
    def extract_detail(self, message: str, conversation_summary: Optional[str] = None) -> Optional[str]:
        """
        Extract one specific detail from the message to reference in the reply.
        
        Strategy:
        1. Look for topics (work, hobby, location, emotion, relationship)
        2. Extract specific noun/phrase mentioned
        3. Return a phrase like "your job" or "that hike you mentioned" or "how tired you are"
        """
        msg_lower = message.lower()
        
        # === PRIORITY 1: Check for explicit emotional statement ===
        # "I'm feeling X" or "I'm so [emotion]"
        emotion_match = re.search(r"i[\'m]?m\s+(feeling|so|really|very|super)\s+(\w+)", msg_lower)
        if emotion_match:
            emotion = emotion_match.group(2)
            # Check if it matches known emotions
            if any(emot in emotion for emot in self.EMOTION_KEYWORDS):
                return f"how {emotion} you are"
        
        # === PRIORITY 2: Check for direct actions or events ===
        # "I just [did something]" or "I'm [doing something]"
        action_match = re.search(r"i[\'m]?m\s+(just\s+)?(\w+(?:\s+\w+)?)", msg_lower)
        if action_match:
            action = action_match.group(2).strip()
            return f"that you're {action}"
        
        # === PRIORITY 3: Look for topic keywords ===
        topics_found = {}
        
        # Score work-related mentions
        work_score = sum(1 for kw in self.WORK_KEYWORDS if kw in msg_lower)
        if work_score > 0:
            topics_found["work"] = work_score
        
        # Score hobby mentions
        hobby_score = sum(1 for kw in self.HOBBY_KEYWORDS if kw in msg_lower)
        if hobby_score > 0:
            topics_found["hobby"] = hobby_score
        
        # Score relationship mentions
        rel_score = sum(1 for kw in self.RELATIONSHIP_KEYWORDS if kw in msg_lower)
        if rel_score > 0:
            topics_found["relationship"] = rel_score
        
        # Score emotion mentions
        emo_score = sum(1 for kw in self.EMOTION_KEYWORDS if kw in msg_lower)
        if emo_score > 0:
            topics_found["emotion"] = emo_score
        
        # Score place mentions
        place_score = sum(1 for kw in self.PLACE_KEYWORDS if kw in msg_lower)
        if place_score > 0:
            topics_found["place"] = place_score
        
        # === PRIORITY 4: Return top-scoring topic ===
        if topics_found:
            top_topic = max(topics_found, key=topics_found.get)
            return self._format_detail_for_topic(top_topic, msg_lower)
        
        # === PRIORITY 5: Extract first proper noun (name or capitalized word) ===
        # Look for capitalized words that might be names or places
        nouns = re.findall(r'\b[A-Z]\w+\b', message)
        if nouns:
            return f"that thing about {nouns[0].lower()}"
        
        # === FALLBACK: Use generic reference ===
        return None  # Caller will use "what she said" as fallback
    
    def _format_detail_for_topic(self, topic: str, msg_lower: str) -> str:
        """Format the detail based on what topic was found."""
        
        if topic == "work":
            # Find specific work keyword mentioned
            for kw in self.WORK_KEYWORDS:
                if kw in msg_lower:
                    return f"that thing about your {kw}"
            return "that work thing"
        
        elif topic == "hobby":
            for kw in self.HOBBY_KEYWORDS:
                if kw in msg_lower:
                    return f"that you {kw}"
            return "that hobby thing"
        
        elif topic == "relationship":
            for kw in self.RELATIONSHIP_KEYWORDS:
                if kw in msg_lower:
                    return f"that thing about your {kw}"
            return "that relationship thing"
        
        elif topic == "emotion":
            for kw in self.EMOTION_KEYWORDS:
                if kw in msg_lower:
                    return f"how {kw} you are"
            return "how you're feeling"
        
        elif topic == "place":
            for kw in self.PLACE_KEYWORDS:
                if kw in msg_lower:
                    return f"that place, {kw}"
            return "that location"
        
        return None
