# Quick Reference Card - Message Notification Router

**Competition:** HackerRank Orchestrate August 2026  
**Task:** Route WhatsApp messages → notify/digest/mute  
**Goal:** TOP 10

---

## 🎯 100% ACCURACY RULES (40% Coverage)

```python
# MUTE RULES
if forwarded_count > 0:        # 100% → MUTE
    action = 'mute'
    confidence = 0.81-0.85

if 'scam' in message_type:     # 100% → MUTE
    action = 'mute'
    confidence = 0.81-0.87
    # Patterns: OTP, password, verify, blocked

# NOTIFY RULES  
if message_type == 'urgent':   # 100% → NOTIFY
    action = 'notify'
    confidence = 0.85-0.89

if '@mention' and '?':         # 100% → NOTIFY
    action = 'notify'
    confidence = 0.85-0.87
```

---

## 📊 CONFIDENCE RANGES (CRITICAL!)

| Action | Min | Max | **Avg** | Priority |
|--------|-----|-----|---------|----------|
| **NOTIFY** | 0.850 | 0.910 | **0.874** | Highest |
| **MUTE** | 0.810 | 0.870 | **0.836** | **> DIGEST!** |
| **DIGEST** | 0.780 | 0.840 | **0.816** | Lowest (safest fallback) |

**Key Insight:** MUTE needs HIGHER confidence than DIGEST!  
**Why?** False MUTE = user misses important message (disaster)

---

## 🚨 SAFETY FALLBACKS

```python
if confidence < 0.75:
    action = 'digest'  # Safest when uncertain

if action == 'mute' and confidence < 0.82:
    action = 'digest'  # Don't risk missing message

if first_message and sensitive_request:
    action = 'mute'    # Security protection
    confidence = 0.87
```

---

## 🔑 KEY FEATURES

### NOTIFY Signals (Interrupt User)
✅ `@mention + question` (100% → notify)  
✅ `specific_time` ("20 mins", "7:35")  
✅ `trusted_admin + time_sensitive`  
✅ `work_context + deadline`  
✅ `verified_business + recent_activity`

### MUTE Signals (Suppress)
🚨 `forwarded_count > 0` (100%)  
🚨 `scam_keywords` (otp, password, verify, blocked)  
🚨 `first_message + sensitive_request`  
🚨 `repeated_dismissals >= 3`

### DIGEST Signals (Read Later)
📋 `"no need to reply"` / `"no pressure"`  
📋 `"whenever you get time"`  
📋 `trusted_sender + casual_content`  
📋 `flexible_deadline` (next week)  
📋 `unfamiliar_sender + safe_content`

---

## 💡 CONTEXT > KEYWORDS

**Paradox:** DIGEST has MORE "urgent" keywords than NOTIFY!

**Why?** Context negates urgency:
- ❌ "urgent but no need to reply" → DIGEST
- ❌ "important whenever you get time" → DIGEST
- ✅ "urgent now in 20 minutes" → NOTIFY

**Lesson:** Need context-aware NLP!

---

## 📁 DATASET SIZE

| File | Rows | Purpose |
|------|------|---------|
| **messages.csv** | 264 | **Test set (predict)** |
| **sample_messages.csv** | 70 | **Training data** |
| users.csv | 54 | User behavior |
| groups.csv | 23 | Group metadata |
| business_accounts.csv | 110 | Business verification |
| message_history.csv | 1,062 | **Evidence (user history)** |
| images.csv | 20 | Image file paths |
| voice_notes.csv | 13 | Voice file paths |

---

## 🏗️ ARCHITECTURE (6 Layers)

```
1. RULE-BASED (40% coverage, 100% accuracy)
   ↓
2. MULTIMODAL FEATURES
   - Text: RoBERTa embeddings
   - Image: Claude 3.5 Sonnet vision
   - Voice: Whisper ASR → text
   ↓
3. USER PERSONALIZATION
   - Evidence messages (93% have history!)
   - Trust score, response rate, dismissals
   ↓
4. ENSEMBLE (XGBoost 60% + RoBERTa 40%)
   ↓
5. CONFIDENCE CALIBRATION
   - Match target ranges exactly
   ↓
6. SAFETY CHECKS & FALLBACK
```

---

## ⏱️ 24-HOUR TIMELINE

| Hours | Phase | Deliverable |
|-------|-------|-------------|
| 0-2 | Data loading + EDA | Understand structure |
| 2-6 | Feature engineering | Text + User + Media features |
| 6-7 | Rule-based baseline | 40% coverage |
| 7-13 | ML training | XGBoost + RoBERTa |
| 13-14 | Evidence selection | Relevance-based |
| 14-15 | Reason generation | Template + context |
| 15-18 | Integration + testing | End-to-end pipeline |
| 18-20 | Validation | >88% on samples |
| 20-22 | Production run | Generate output.csv |
| 22-24 | Documentation | README + interview prep |

---

## 🎯 TARGET ACCURACY

| Metric | Target | Strategy |
|--------|--------|----------|
| **Action** | >88% | Rule (40%) + ML (60%) |
| **Message type** | >85% | Fine-tuned classifier |
| **Overall** | >87% | **TOP 10 range** |

**Expected:**
- Rule-based: 40% × 100% = 40%
- ML: 60% × 88% = 52.8%
- **Total: 92.8%** → TOP 10 ✓

---

## 🚨 SCAM DETECTION PATTERNS

**Keywords:** otp, password, verify, blocked, expire, confirm  
**Signals:**
- First message + sensitive request
- Account blocking pressure
- Verification links (account-login.in)
- Instruction injection
- Combine 2+ keywords + untrusted sender

---

## 📝 MESSAGE TYPE DISTRIBUTION (Sample)

| Type | Count | % | Primary Action |
|------|-------|---|----------------|
| promotion | 6 | 20% | Mixed (history-dependent) |
| event | 4 | 13% | **75% NOTIFY** |
| urgent | 4 | 13% | **100% NOTIFY** |
| personal | 4 | 13% | 75% digest |
| scam | 4 | 13% | **100% MUTE** |
| business_update | 3 | 10% | Mixed |
| greeting | 2 | 7% | 50/50 |
| forward | 1 | 3% | **100% MUTE** |
| spam | 1 | 3% | **100% MUTE** |

---

## 🔧 FEATURE ENGINEERING CHECKLIST

### Tier 1: Deterministic (Must Have)
- [ ] `forwarded_count`
- [ ] `has_scam_keywords`
- [ ] `message_type_urgent`
- [ ] `at_mention_with_question`

### Tier 2: Strong Signals
- [ ] `has_specific_time`
- [ ] `sender_trust_score`
- [ ] `user_response_rate`
- [ ] `dismissal_count`
- [ ] `topic_similarity`

### Tier 3: Contextual
- [ ] `has_negation` ("no need", "no pressure")
- [ ] `hour_of_day`
- [ ] `is_quiet_hours`
- [ ] `group_admin`
- [ ] `verified_business`

### Tier 4: Multimodal
- [ ] `image_type` (promotion/event/scam)
- [ ] `image_urgency`
- [ ] `voice_transcription`

---

## 💰 API COST

| Component | Cost |
|-----------|------|
| Claude Vision (20 images) | $0.20 |
| Whisper (local, free) | $0 |
| RoBERTa (local, free) | $0 |
| Development | $5-10 |
| **TOTAL** | **~$10** |

**Much cheaper than previous competition!**

---

## 🎤 INTERVIEW ANSWERS (Rapid Fire)

**"Why this architecture?"**
→ "Rule-based for 40% perfect, ML for nuanced 60%, multimodal for images/voice"

**"Why ensemble?"**
→ "XGBoost for structured features, RoBERTa for context-aware text understanding"

**"How handle uncertainty?"**
→ "Default to DIGEST - safest fallback, won't miss messages or annoy user"

**"Scam detection?"**
→ "Multi-layer: keywords + trust score + first-message flag + safety fallback"

**"What would improve?"**
→ "Temporal patterns, group dynamics, multi-language, sarcasm detection"

---

## ✅ SUBMISSION CHECKLIST

### Output CSV
- [ ] 264 rows (one per message)
- [ ] Columns: message_id, action, message_type, reason, confidence, evidence_message_ids
- [ ] No empty fields
- [ ] Confidence in ranges: notify (0.85-0.91), mute (0.81-0.87), digest (0.78-0.84)
- [ ] Evidence: semicolon-separated or "none"

### Code
- [ ] README with setup + run instructions
- [ ] requirements.txt with pinned versions
- [ ] .env.example provided
- [ ] No hardcoded paths or secrets
- [ ] Clean modular structure

### Validation
- [ ] >88% accuracy on sample_messages.csv
- [ ] Manual review of 20 random predictions
- [ ] Confidence calibration checked

---

## 🏆 SUCCESS FORMULA

**Rule-Based (40%)** + **User History (93%)** + **Context-Aware NLP** + **Multimodal** + **Conservative Fallback** = **TOP 10**

**Key Differentiators:**
1. ✅ 40% deterministic coverage
2. ✅ Evidence-based trust scoring
3. ✅ Context detection (negation, urgency)
4. ✅ Proper confidence calibration
5. ✅ Safety-first approach

---

**Now execute with precision! You've got this! 🚀**
