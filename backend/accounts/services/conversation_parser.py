"""
Conversation Parser Service

Parses conversation text into structured message exchanges to:
1. Identify the last message (what to respond to)
2. Extract conversation flow (for context understanding)
3. Parse timestamps and participant roles
4. Support the LISTEN → RELATE → DIG DEEPER pattern
"""

import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class ConversationParser:
    """Parses dating app conversations into structured message data"""
    
    # Common timestamp patterns from dating apps
    TIMESTAMP_PATTERNS = [
        r'(\d{1,2}):(\d{2})\s+(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+)?(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|April|March|June|July)\s+(\d{1,2}),?\s+)?(\d{4})?\s*(?:—|--|-|–)\s*(.+?)(?:\s*$|\n)',  # "15:17 Tue, Apr 14, 2026 — 3 hours ago"
        r'(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)?\s*(?:—|--|-|–)\s*(.+?)(?:\s*$|\n)',  # "15:17 — 3 hours ago"
        r'(\d{1,2}):(\d{2})\s+(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}))?\s*$',  # "15:17 Tue Apr 14"
    ]
    
    def parse_conversation(self, conversation_text: str) -> Dict:
        """
        Parse conversation into structured format.
        
        Returns:
        {
            'messages': [
                {
                    'timestamp': '15:17 Tue, Apr 14, 2026',
                    'time_ago': '3 hours ago',
                    'speaker': 'her' or 'him',  # determined heuristically
                    'text': 'message content',
                    'is_question': bool,
                    'raw_position': int  # position in conversation
                },
                ...
            ],
            'last_message': {...},  # The message to respond to
            'last_speaker': 'her' or 'him',
            'conversation_flow': str,  # Summary of conversation pattern
            'message_count': int
        }
        """
        messages = []
        
        # Split by lines
        lines = conversation_text.split('\n')
        pending_text = []  # Text lines before first timestamp
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # Check if this line has a timestamp
            timestamp_match = self._extract_timestamp(line)
            
            if timestamp_match:
                # This line has a timestamp
                timestamp, time_ago, text_after = timestamp_match
                
                # Text before timestamp + text after timestamp
                full_text = (' '.join(pending_text) + ' ' + text_after).strip()
                
                # Create message
                message = {
                    'timestamp': timestamp,
                    'time_ago': time_ago,
                    'text': full_text,
                    'raw_position': len(messages)
                }
                messages.append(message)
                
                # Clear pending text for next message
                pending_text = []
            else:
                # No timestamp - accumulate for next message
                pending_text.append(line.strip())
        
        # Determine speaker for each message and add metadata
        messages = self._assign_speakers(messages)
        
        # Add derived fields
        messages = self._add_metadata(messages)
        
        # Get last message
        last_message = messages[-1] if messages else None
        last_speaker = last_message.get('speaker') if last_message else None
        
        return {
            'messages': messages,
            'last_message': last_message,
            'last_speaker': last_speaker,
            'message_count': len(messages),
            'conversation_flow': self._analyze_flow(messages),
            'raw_text': conversation_text
        }
    
    def _extract_timestamp(self, line: str) -> Optional[Tuple[str, str, str]]:
        """Extract timestamp and message text from a line"""
        for pattern in self.TIMESTAMP_PATTERNS:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Extract time
                hour = groups[0]
                minute = groups[1]
                time_str = f"{hour}:{minute}"
                
                # Extract date info if available
                day_name = groups[2] if len(groups) > 2 else None
                month = groups[3] if len(groups) > 3 else None
                day = groups[4] if len(groups) > 4 else None
                year = groups[5] if len(groups) > 5 else None
                
                # Extract time ago
                time_ago = None
                for i, g in enumerate(groups):
                    if g and ('ago' in str(g).lower() or 'hour' in str(g).lower() or 'day' in str(g).lower() or 'minute' in str(g).lower()):
                        time_ago = str(g).strip()
                        break
                
                # Build timestamp
                if day_name and month and day and year:
                    full_timestamp = f"{time_str} {day_name}, {month} {day}, {year}"
                elif month and day:
                    full_timestamp = f"{time_str} {day_name or ''} {month} {day}".strip()
                else:
                    full_timestamp = time_str
                
                # Extract message text (everything after the timestamp)
                message_text = line[match.end():].strip()
                
                return (full_timestamp, time_ago or '', message_text)
        
        return None
    
    def _assign_speakers(self, messages: List[Dict]) -> List[Dict]:
        """Heuristically assign speaker (her/him) to messages based on patterns"""
        if not messages:
            return messages
        
        # Typical patterns in the conversation:
        # - Alternating speakers
        # - Female speaker might use: "I feel", "my body", "orgasm", "pregnant", "intimate", etc.
        # - Male speaker might use: "baby", "beautiful", "take care", etc.
        
        female_indicators = [
            r'\b(pregnant|period|my body|vagina|clitoris|orgasm|menopause|contraception)\b',
            r'\b(i feel.*emotional|emotional.*connection|my breasts|feminine)\b',
        ]
        
        # Start with assumption of alternating speakers
        # Most dating conversations alternate between her and him
        for i, msg in enumerate(messages):
            text = msg['text'].lower()
            
            # Check for explicit gender indicators
            is_female = any(re.search(pat, text, re.IGNORECASE) for pat in female_indicators)
            
            if is_female:
                msg['speaker'] = 'her'
            else:
                # Alternate assumption: if first message, assume "her"
                # Then alternate
                msg['speaker'] = 'her' if i % 2 == 0 else 'him'
        
        return messages
    
    def _add_metadata(self, messages: List[Dict]) -> List[Dict]:
        """Add metadata to each message"""
        for msg in messages:
            text = msg['text']
            
            # Check if question
            msg['is_question'] = text.rstrip().endswith('?')
            
            # Word count
            msg['word_count'] = len(text.split())
            
            # Character count
            msg['char_count'] = len(text)
            
            # Contains emotional keywords
            emotional_keywords = ['feel', 'love', 'miss', 'want', 'desire', 'afraid', 'scared', 'happy', 'sad', 'sexy', 'horny', 'aroused']
            msg['is_emotional'] = any(kw in text.lower() for kw in emotional_keywords)
            
            # Contains sexual keywords
            sexual_keywords = ['sex', 'orgasm', 'intimate', 'touch', 'kiss', 'body', 'naked', 'horny', 'aroused', 'desire', 'fuck', 'cum', 'dick', 'pussy', 'breast', 'cock']
            msg['is_sexual'] = any(kw in text.lower() for kw in sexual_keywords)
            
            # Contains meeting/logistics keywords
            logistics_keywords = ['meet', 'visit', 'coffee', 'dinner', 'location', 'address', 'phone', 'number', 'time', 'schedule', 'when', 'where']
            msg['is_logistics'] = any(kw in text.lower() for kw in logistics_keywords)
        
        return messages
    
    def _analyze_flow(self, messages: List[Dict]) -> str:
        """Analyze conversation flow to understand context"""
        if not messages:
            return "empty"
        
        # Count message types
        questions = sum(1 for m in messages if m.get('is_question'))
        emotional = sum(1 for m in messages if m.get('is_emotional'))
        sexual = sum(1 for m in messages if m.get('is_sexual'))
        logistics = sum(1 for m in messages if m.get('is_logistics'))
        
        total = len(messages)
        
        # Characterize flow
        flow_type = []
        
        if sexual / total > 0.4:
            flow_type.append("heavily_sexual")
        elif sexual / total > 0.2:
            flow_type.append("moderately_sexual")
        elif sexual > 0:
            flow_type.append("some_sexual_content")
        else:
            flow_type.append("non_sexual")
        
        if emotional / total > 0.3:
            flow_type.append("emotionally_engaged")
        
        if logistics / total > 0.2:
            flow_type.append("logistics_focused")
        
        if questions / total > 0.4:
            flow_type.append("question_heavy")
        else:
            flow_type.append("statement_heavy")
        
        return " + ".join(flow_type)
    
    def get_last_message(self, conversation_data: Dict) -> str:
        """Get the last message text to respond to"""
        if conversation_data['last_message']:
            return conversation_data['last_message']['text']
        return ""
    
    def get_conversation_summary(self, conversation_data: Dict) -> str:
        """
        Get a summary of conversation topics for context.
        Used by AI to understand the broader flow.
        """
        messages = conversation_data['messages']
        topics = []
        
        # Extract keywords from each message
        for msg in messages:
            text = msg['text'].lower()
            
            # Sexual topics
            if msg.get('is_sexual'):
                if 'outdoor' in text:
                    topics.append('outdoor_sex')
                if 'pregnant' in text or 'child' in text or 'baby' in text:
                    topics.append('having_children')
                if 'beach' in text or 'vacation' in text:
                    topics.append('vacation_plans')
                if 'couch' in text or 'bed' in text or 'furniture' in text:
                    topics.append('indoor_intimacy')
                if 'kiss' in text or 'touch' in text or 'intimate' in text:
                    topics.append('physical_affection')
            
            # Emotional topics
            if msg.get('is_emotional'):
                if 'connect' in text or 'connection' in text:
                    topics.append('emotional_connection')
                if 'chemistry' in text:
                    topics.append('chemistry')
                if 'perfect match' in text or 'match' in text:
                    topics.append('compatibility')
                if 'migraine' in text or 'headache' in text or 'sick' in text:
                    topics.append('health_concern')
            
            # Logistics
            if msg.get('is_logistics'):
                if 'family' in text or 'son' in text or 'daughter' in text:
                    topics.append('family_matters')
                if 'work' in text or 'job' in text:
                    topics.append('career')
                if 'meet' in text or 'visit' in text:
                    topics.append('meeting_logistics')
        
        return ", ".join(set(topics)) if topics else "general_conversation"
    
    def should_respond_sexually(self, conversation_data: Dict) -> bool:
        """Determine if response should have sexual/flirty tone based on conversation flow"""
        messages = conversation_data['messages']
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        
        recent_sexual_count = sum(1 for m in recent_messages if m.get('is_sexual'))
        recent_messages_total = len(recent_messages)
        
        # If recent messages are > 30% sexual, respond sexually
        return recent_sexual_count / recent_messages_total > 0.3 if recent_messages_total > 0 else False
    
    def get_conversation_context_for_prompt(self, conversation_data: Dict) -> str:
        """
        Generate context string to include in AI prompt.
        This helps AI understand the flow and what to respond to.
        """
        last_msg = conversation_data['last_message']
        flow = conversation_data['conversation_flow']
        topics = self.get_conversation_summary(conversation_data)
        should_be_sexual = self.should_respond_sexually(conversation_data)
        
        context = f"""
CONVERSATION CONTEXT:
- Last message (what to respond to): "{last_msg['text']}"
- Conversation flow: {flow}
- Topics discussed: {topics}
- Response tone: {'SEXUAL/FLIRTY' if should_be_sexual else 'WARM/GENUINE'}
- Total messages in conversation: {conversation_data['message_count']}
"""
        return context.strip()
