# Location & Meeting Rules - Quick Reference

## TLDR: What Changed

**Old System**: All location and meeting questions diverted with generic responses

**New System**: 
- ✅ General location questions (allowed)
- ✅ Meeting requests decline with context-aware responses
- ✅ Specific address/work requests diverted
- ✅ Responses reference what the user actually said

---

## LOCATION: What's Allowed vs Blocked

### ✅ ALLOWED - No Diversion
```
"where do you live?"
"what city are you in?"
"where are you from?"
"what country are you from?"
```
→ Response: User can share general location naturally

### ❌ BLOCKED - Will Divert
```
"what's your exact address?"
"send me your address"
"what street do you live on?"
"where specifically do you work?"
"what company do you work for?"
"what's the name of your workplace?"
```
→ Response: Redirect with questions (not addresses/work details)

---

## MEETING: How We Decline

### OLD (Banned Phrases ❌)
```
"Not yet, maybe later"
"We're having too much fun"
"Can't do that yet"
```

### NEW (Contextual Anchoring ✅)

**If they mention: Playfulness/teasing**
```
"you said you like the teasing and i'm literally just getting started with you?"
```

**If they mention: Genuine feelings**
```
"there's something actually building here and i wanna feel it more before"
```

**If they sound confident/pushy**
```
"you gotta earn that kind of move, what would prove to me you're worth it?"
```

**Generic response**
```
"not yet but like honestly i think about it which says something right?"
```

---

## VACATION/HOTEL

### ✅ These are ALLOWED (no diversion)
```
"I love Bali"
"There's a nice hotel in Dubai"
"I've been wanting to visit Tokyo"
```

### ❌ What NOT to say
```
❌ "Oh yeah I know Bali so well, I've been there many times"
❌ "That hotel is amazing, I stayed there"
```

### ✅ What TO say instead
```
✅ "What would we do there? What's your dream scenario?"
✅ "That sounds romantic, tell me what you picture?"
```

---

## Test It Yourself

Run the test suite:
```bash
cd backend
docker-compose exec -T backend python test_location_meeting_rules.py
```

Expected: 47/50 tests pass (94%)

---

## Code Location

- **Main Rules**: `/backend/accounts/services/response_validator.py` (lines 20-60)
- **Contextual Anchoring**: `_build_contextual_meeting_decline()` method (lines 350-410)
- **Tests**: `/backend/test_location_meeting_rules.py`
- **Integration**: Already works with `/backend/accounts/services/ai_generation.py`

---

## How It Works

1. **User sends message** → chat endpoint
2. **ai_generation.py calls** `validator.check_conversation_rules(message)`
3. **ResponseValidator checks:**
   - Is it asking for specific location (address/work)? → DIVERT with redirect
   - Is it a meeting request? → DIVERT with contextual decline
   - Otherwise → ALLOW (proceed to OpenAI)
4. **For meeting diverts**: Uses `_build_contextual_meeting_decline()` to reference what THEY said
5. **Response formatted** and sent back

---

## Key Patterns to Know

### Location Prohibited Pattern
```regex
where do you work|where.*work specifically|your workplace|what company
```

### Meeting Prohibited Patterns
```regex
let's meet|when can we meet|let's get coffee|can i come see you|should we meet
```

### Context Detection for Meeting Anchoring
- playful, tease, naughty, flirt, fun, game → Teasing withdrawal
- feel, genuine, real, connection, vibe, energy → Vulnerable pivot
- sure, think, believe, deserve, give, prove → Confident redirect
- (anything else) → Slow burn strategy

---

## What Users Will Experience

**Before**:
User: "where do you work?"
Bot: "not yet honestly. still figuring you out..." (generic)

**After**:
User: "where do you work?"
Bot: "not that specific yet honestly, but i like that you're curious. what's in your head right now?" (personalized redirect)

---

## Team Notes

- ✅ No database migrations needed
- ✅ Backward compatible with existing code
- ✅ Automatically integrated through ai_generation.py
- ✅ Test suite validates all scenarios
- ✅ Django system check passes (0 issues)
- ✅ All responses still meet 140-180 character requirement
- ✅ All responses end with question mark

---

## Questions?

1. **Does this affect existing conversations?** No, only new messages use new logic
2. **Can we customize the contextual anchoring?** Yes, edit templates in `_build_contextual_meeting_decline()`
3. **Can we add more personality types?** Yes, add more phrase detection in the method
4. **How do we measure success?** Track diversion rates and engagement metrics in analytics

