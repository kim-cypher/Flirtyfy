"""
Reply Patches - Python-based Response Fixes

Replaces expensive LLM rephrase calls with intelligent Python patches.
All functions are zero-cost (no API calls), deterministic, and preservable.

Patch Functions:
1. patch_length() - Fix character count (expand/truncate)
2. patch_banned_phrases() - Remove/replace banned words
3. patch_question_ending() - Ensure ends with ?
4. patch_tone_mismatch() - Adjust tone via word substitution
5. patch_robotic_patterns() - Replace formulaic phrases
6. patch_generic_question() - Make question more specific
7. patch_flow() - Improve readability
"""

import re
from accounts.services.depth_principles import (
    BANNED_TELL_ME_PATTERNS, BANNED_WHAT_DO_YOU_THINK_PATTERNS,
    BANNED_VERIFICATION_PATTERNS, BANNED_HOLLOW_INTEREST_PATTERNS,
    BANNED_OPEN_ENDED_PATTERNS, BANNED_FAKE_DEEP_PATTERNS,
    BANNED_COMFORT_CHECK_PATTERNS
)


class ReplyPatches:
    """Collection of Python-based response patches (zero API cost)"""
    
    @staticmethod
    def patch_length(text, target_min=140, target_max=180):
        """
        Fix character count without LLM.
        
        Strategy:
        - If too short: Add filler connectors and expand key ideas
        - If too long: Truncate at word boundary, preserve ending
        """
        current_length = len(text)
        
        # Too short: expand with context-aware additions
        if current_length < target_min:
            gap = target_min - current_length
            
            # Strategy 1: Add conversational filler
            if not text.lower().startswith(('i', 'you', 'so')):
                additions = {
                    'romantic': " honestly, ",
                    'playful': " lol ",
                    'curious': " like ",
                    'supportive': " and like ",
                }
                # Insert after first sentence (heuristic)
                period_idx = text.find('.')
                if period_idx > 0 and period_idx < len(text) - 1:
                    for filler in additions.values():
                        if current_length + len(filler) < target_max:
                            text = text[:period_idx+1] + filler + text[period_idx+1:]
                            current_length = len(text)
                            break
            
            # Strategy 2: Duplicate parts of the question
            if current_length < target_min and text.endswith('?'):
                question_part = text.split('?')[0]
                if len(question_part) > 20:
                    # Add emphasis: "like what do you mean by X?"
                    prefix = "like "
                    text = text.replace('?', f', like what do you mean?')
                    current_length = len(text)
            
            # Strategy 3: Add transition phrase
            if current_length < target_min:
                transitions = [
                    ("What's", "Okay so like, what's"),  # Add "okay so like"
                    ("How", "And like, how"),
                    ("Do you", "But do you"),
                    ("Are you", "Like, are you"),
                ]
                for old, new in transitions:
                    if text.startswith(old):
                        text = text.replace(old, new, 1)
                        break
            
            # Strategy 4: Double-check and add punctuation
            if current_length < target_min:
                # Add ellipsis or comma before ending
                if not text.endswith('?!'):
                    text = text[:-1] + '...?'
        
        # Too long: truncate at word boundary
        elif current_length > target_max:
            # Find safe truncation point (word boundary)
            truncate_at = target_max - 10  # Leave room for ending
            
            # Find last space before truncation point
            last_space = text.rfind(' ', 0, truncate_at)
            if last_space > target_max - 30:  # If word boundary is reasonable
                text = text[:last_space].rstrip('.,!;:')
            else:
                # Fallback: hard truncate
                text = text[:target_max - 2]
            
            # Ensure ends with ?
            text = text.rstrip('.,!; ') + '?'
        
        # Final safety check
        final_length = len(text)
        if final_length < target_min or final_length > target_max:
            # If still out of range, force exact length
            if final_length > target_max:
                text = text[:target_max - 1].rstrip('.,! ') + '?'
            elif final_length < target_min:
                # Padding is last resort (shouldn't happen)
                text = text.rstrip('?') + ' really?' 
        
        return text
    
    @staticmethod
    def patch_banned_phrases(text):
        """Remove/replace banned phrases detected by pattern matching"""
        lower_text = text.lower()
        
        # All banned categories
        banned_categories = {
            'tell_me': BANNED_TELL_ME_PATTERNS,
            'what_do_you_think': BANNED_WHAT_DO_YOU_THINK_PATTERNS,
            'verification': BANNED_VERIFICATION_PATTERNS,
            'hollow_interest': BANNED_HOLLOW_INTEREST_PATTERNS,
            'open_ended': BANNED_OPEN_ENDED_PATTERNS,
            'fake_deep': BANNED_FAKE_DEEP_PATTERNS,
            'comfort_check': BANNED_COMFORT_CHECK_PATTERNS,
        }
        
        replacements = {
            'tell_me': {
                'tell me more': 'elaborate on that',
                'tell me about yourself': 'what\'s your story',
                'tell me everything': 'everything about you',
                'tell me what you think': 'what\'s your take',
                'tell me how you feel': 'how you feeling about',
            },
            'what_do_you_think': {
                'what do you think?': 'what\'s your take?',
                'what are your thoughts?': 'thoughts?',
                'what\'s your opinion?': 'what do you reckon?',
            },
            'verification': {
                'is that true?': 'for real?',
                'are you serious?': 'no way?',
                'really?': 'actually?',
            },
            'comfort_check': {
                'how does that make you feel?': 'how you feeling about that?',
                'are you comfortable with that?': 'cool with that?',
            }
        }
        
        # Try replacements first (preserves meaning better)
        for category, pattern_list in banned_categories.items():
            if category in replacements:
                for bad, good in replacements[category].items():
                    if bad.lower() in lower_text:
                        text = re.sub(
                            re.escape(bad),
                            good,
                            text,
                            flags=re.IGNORECASE
                        )
                        lower_text = text.lower()
                        break
        
        # If no replacement found, try removing (last resort)
        for category, pattern_list in banned_categories.items():
            for pattern in pattern_list:
                if pattern.lower() in lower_text:
                    # Remove the pattern entirely
                    text = re.sub(
                        re.escape(pattern),
                        '',
                        text,
                        flags=re.IGNORECASE
                    )
                    text = re.sub(r'\s+', ' ', text)  # Clean up extra spaces
                    lower_text = text.lower()
        
        return text.strip()
    
    @staticmethod
    def patch_question_ending(text):
        """Ensure response ends with question mark"""
        text = text.rstrip()
        
        # If already ends with ?, no change needed
        if text.endswith('?'):
            return text
        
        # If ends with other punctuation, replace
        if text.endswith('.!,;:'):
            return text[:-1] + '?'
        
        # Otherwise append
        return text + '?'
    
    @staticmethod
    def patch_tone_mismatch(text, target_tone='playful'):
        """
        Adjust tone via word substitution (no rephrase).
        
        Tone patterns:
        - playful: Add "lol", "haha", "ugh", increase exclamation
        - romantic: Replace "cool" → "beautiful", "nice" → "sweet"
        - casual: Keep simple, add contractions
        - supportive: Add empathetic words
        """
        lower_text = text.lower()
        
        if target_tone == 'playful':
            # Add playful markers if missing
            if 'lol' not in lower_text and 'haha' not in lower_text:
                if text.endswith('?'):
                    text = text[:-1] + ' lol?'
        
        elif target_tone == 'romantic':
            # Word replacements for romantic tone
            replacements = {
                r'\bcool\b': 'beautiful',
                r'\bnice\b': 'sweet',
                r'\bwant\b': 'crave',
                r'\blike\b': 'adore',
            }
            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        elif target_tone == 'supportive':
            # Add supportive markers
            supportive_additions = [
                ('i get it', 'i totally get that'),
                ('understand', 'totally understand'),
                ('hard', 'really hard'),
            ]
            for old, new in supportive_additions:
                if old in lower_text:
                    text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def patch_robotic_patterns(text):
        """Replace robotic/formulaic phrases with natural alternatives"""
        replacements = {
            r'there\'?s\s+something\s+(about|real|different)': 'something\'s',
            r'what\'s\s+actually': 'what',
            r'\bi\s+actually\b': 'i',
            r'\bcertainly\b': 'for sure',
            r'\bof\s+course\b': 'totally',
            r'\byou\s+seem\b': 'you\'re',
            r'\bseems\s+like\b': 'it\'s',
            r'\bi\s+mean\b': '',  # Remove filler entirely
            r'\byou\s+know\b': 'right',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def patch_generic_question(text):
        """Make generic question endings more specific"""
        if not text.endswith('?'):
            return text
        
        generic_patterns = {
            r'really\?$': 'for real?',
            r'though\?$': 'you think?',
            r'lol\?$': 'honest?',
            r'haha\?$': 'serious?',
            r'what\?$': 'what\'s that about?',
        }
        
        for pattern, replacement in generic_patterns.items():
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                break
        
        return text
    
    @staticmethod
    def patch_flow(text):
        """Improve readability and conversational flow"""
        # Add contractions where possible (make it more conversational)
        contractions_map = {
            r'\bis\s+not\b': 'isn\'t',
            r'\bdo\s+not\b': 'don\'t',
            r'\bdoes\s+not\b': 'doesn\'t',
            r'\bcan\s+not\b': 'can\'t',
            r'\bwill\s+not\b': 'won\'t',
            r'\bwould\s+not\b': 'wouldn\'t',
            r'\bshould\s+not\b': 'shouldn\'t',
            r'\bcould\s+not\b': 'couldn\'t',
            r'\bi\s+am\b': 'i\'m',
            r'\byou\s+are\b': 'you\'re',
            r'\bthey\s+are\b': 'they\'re',
        }
        
        for pattern, contraction in contractions_map.items():
            text = re.sub(pattern, contraction, text, flags=re.IGNORECASE)
        
        # Break up long sentences with commas where appropriate
        # (heuristic: if sentence > 60 chars without punctuation, add comma)
        sentences = text.split('.')
        if len(sentences) > 1 and len(sentences[0]) > 60:
            # Find good place to add comma (after 25-30 chars)
            first_sent = sentences[0]
            if len(first_sent) > 30:
                comma_pos = first_sent.find(' ', 25)
                if comma_pos > 0:
                    sentences[0] = first_sent[:comma_pos] + ',' + first_sent[comma_pos:]
        
        text = '.'.join(sentences)
        
        return text
    
    @staticmethod
    def apply_all_patches(text, apply_order=None):
        """
        Apply all patches in optimal order.
        
        Order: length → banned phrases → tone → robotic → generic question → flow → ending
        """
        if apply_order is None:
            apply_order = [
                'patch_length',
                'patch_banned_phrases',
                'patch_tone_mismatch',
                'patch_robotic_patterns',
                'patch_generic_question',
                'patch_flow',
                'patch_question_ending',
            ]
        
        patches_obj = ReplyPatches()
        
        for patch_name in apply_order:
            if hasattr(patches_obj, patch_name):
                patch_func = getattr(patches_obj, patch_name)
                if patch_name == 'patch_tone_mismatch':
                    text = patch_func(text, target_tone='playful')
                else:
                    text = patch_func(text)
        
        return text
