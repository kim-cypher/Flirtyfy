# Location & Meeting Handling Rules Analysis

## CURRENT LOCATION/MEETING RULES (Response Validator)

### 1. **Personal Info Patterns** (Currently BLOCKED)
These trigger automatic diversion if user asks:
```regex
address|phone|number|call|whatsapp|snapchat|location|where do you live|where are you from|what city|what state|are you real|are you close|are you nearby|are you in town|can I visit|can I come
```

**Problem:** "where do you live" and "where are you from" are BLOCKED but should be ALLOWED for GENERAL location responses

### 2. **Meetup Request Patterns** (Currently BLOCKED) 
These trigger automatic diversion if user asks:
```regex
in person|in-person|meet up|meetup|see you|see u|see ya|see ya in real life|continue this in (person|real life|private)|continue this outside|go offline|coffee catch up|coffee|dinner|drinks|date|let's meet|lets meet|when (can|will|are) we|where can we meet|where should we meet|when are we (meeting|meeting up)|are you nearby|are you in town|can I visit|can I come|come over|come see
```

---

## REFINED LOCATION RULES (Per User Requirements)

### LOCATION: What Should Be ALLOWED ✅
1. **General location sharing:**
   - "I live in Lagos" / "I'm from Lagos" → ACCEPT & respond naturally
   - "I'm in Nairobi" → ACCEPT
   - General city/country mentions → ACCEPT

2. **Coming to pick you up scenarios:**
   - "I'll come pick you up" → FLIRT with it (not divert)
   - "Should I come pick you up?" → FLIRT with it

3. **Transport/logistics without address:**
   - "I don't have a car" → Suggest you can drive without asking specifics
   - "My car is in the shop" → Engage naturally

### LOCATION: What Should Be PROHIBITED 🚫
1. **Specific address requests:**
   - "What's your exact address?"
   - "Send me your address"
   - Any request for specific house/apartment details
   - "What street do you live on?"

2. **Specific work location:**
   - "Where do you work specifically?"
   - "What's the name of your workplace?"
   - "What company do you work for?"
   - "What office do you go to?"

3. **Pretending to know specific places:**
   - "Oh I know that hotel!" → DON'T pretend to know it
   - "I've been to that restaurant" → ASK general romantic questions instead

### VACATION/HOTEL SCENARIOS ✅
- User mentions: "Let's go to Bali" / "There's a nice hotel in..." 
- Response: ASK GENERAL ROMANTIC QUESTIONS about the place
- Example: "Bali sounds dreamy, what do you picture us doing there?" 
- NOT: "Oh yeah I know Bali so well..." (pretending you've been)

---

## REFINED MEETING RULES (Per User Requirements)

### MEETING: What Should Be PROHIBITED 🚫
1. **Specific meeting commitments:**
   - "Let's meet tomorrow"
   - "When can we meet?"
   - "Let's get coffee" / "Let's go to dinner"
   - "Can I come see you?"

2. **Old polite decline (BANNED):**
   - "Not yet, maybe later" ❌
   - "We're having too much fun" (as a reason to decline) ❌
   - Generic "let's not meet" ❌

### MEETING: NEW DECLINE STRATEGY ✅
Use **contextual flirt anchoring** with specific strategies:

1. **Teasing Withdrawal:** Reference something specific they said
   - "Nah not yet... you said you like being teased, and I'm just getting warmed up 😏"

2. **Slow Burn:** Make it desirable to wait
   - Reference their earlier comment + build anticipation
   - "We gotta keep building this first... remember when you said..."

3. **Confident Redirect:** Reframe the meeting as something that needs prep
   - "Not happening yet, I'm still figuring you out... you deserve the full experience"

4. **Vulnerable Pivot:** Honest admission + deepening
   - "Can't do that yet... there's something building here and I want to feel it more first"

---

## CURRENT CODE LOCATIONS

### File: `/backend/accounts/services/response_validator.py`

**Personal Info Check (Line 34-37):**
```python
self.personal_info_patterns = [
    r'\b(address|phone|number|call|whatsapp|snapchat|location|where do you live|where are you from|what city|what state|are you real|are you close|are you nearby|are you in town|can I visit|can I come)\b'
]
```

**Meetup Check (Line 32-33):**
```python
self.meetup_request_patterns = [
    r'\b(in person|in-person|meet up|meetup|see you|see u|see ya|see ya in real life|continue this in (person|real life|private)|continue this outside|go offline|coffee catch up|coffee|dinner|drinks|date|let\'s meet|lets meet|when (can|will|are) we\b|where can we meet|where should we meet|when are we (meeting|meeting up)|are you nearby|are you in town|can I visit|can I come|come over|come see)\b'
]
```

**Conversation Check Method (Line 276-288):**
```python
def check_conversation_rules(self, conversation_text):
    """Check conversation before generating a reply and divert if the user asks for a meetup or personal info."""
    for pat in self.meetup_request_patterns + self.personal_info_patterns:
        if re.search(pat, conversation_text, re.IGNORECASE):
            response = random.choice(self.diversion_templates)
            response = self._format_question_response(response)
            return {
                'action': 'divert',
                'response': response,
                'reason': 'meetup_or_personal_info_request'
            }
    return {'action': 'allow'}
```

**Diversion Templates (Line 42-48):**
Currently generic, need to be updated to use **contextual flirt anchoring**

---

## ACTION PLAN

### Phase 1: Separate Location Rules
- Split `personal_info_patterns` into:
  - `location_shares_allowed` (general location mentions - don't check)
  - `location_prohibited` (specific address, work, etc. - divert)

### Phase 2: Separate Meeting Rules  
- Split `meetup_request_patterns` into:
  - `meeting_prohibited` (specific meeting commits - divert with NEW strategy)
  - `meeting_allowed` (casual mentions like "pick you up" - engage naturally)

### Phase 3: Update Diversion Logic
- `check_conversation_rules()` should:
  1. Detect which category triggered (location_prohibited vs meeting_prohibited)
  2. Use appropriate diversion strategy:
     - Location prohibited → polite redirect (ask general Q's instead)
     - Meeting prohibited → contextual flirt anchoring (ref something specific + keep tension)

### Phase 4: Test Coverage
- Test general location questions don't trigger diversion
- Test specific address requests DO trigger diversion
- Test meeting contexts properly anchor to conversation history
- Test vacation/hotel contexts ask romantic questions vs pretending knowledge

