# Strategy & Implementation Guide

**Competition:** HackerRank Orchestrate August 2026  
**Task:** Message Notification Router  
**Target:** TOP 10 ranking

---

## 📚 STRATEGY DOCUMENTS

All strategy and planning documents are in `strategy_docs/`:

### 1. **SESSION_STATE.md** ⭐⭐⭐ **START HERE**
Complete context for restarting in new sessions. Contains:
- What we've done so far
- Current folder structure
- Key insights and breakthrough findings
- Expected performance (92.8% → TOP 10)
- 24-hour timeline
- How to restart guide
- Critical reminders

**Use this file to:** Resume work in new Claude session

### 2. **00_EXECUTIVE_SUMMARY.md** 📋
High-level overview including:
- Problem understanding
- Key insights from 70 sample analysis
- Winning architecture (6 layers)
- Expected performance breakdown
- Competitive advantages
- Interview preparation

**Use this file to:** Understand overall strategy

### 3. **WINNING_STRATEGY_TOP10.md** 📖
Complete 24-hour implementation roadmap:
- Phase-by-phase breakdown
- Detailed code templates
- Feature engineering specifics
- ML training procedures
- Multimodal processing (images, voice)
- Validation strategy
- Submission checklist

**Use this file to:** Build the solution step-by-step

### 4. **QUICK_REFERENCE_CARD.md** 🚀
Cheat sheet with:
- 100% accuracy rules (40% coverage)
- Confidence ranges (CRITICAL!)
- Safety fallbacks
- Feature checklist
- Interview Q&A
- Debugging tips

**Use this file to:** Quick lookup during implementation

---

## 🎯 QUICK START

### If Starting Fresh:
```bash
# 1. Read restart point
cat strategy_docs/SESSION_STATE.md

# 2. Review key insights
cat strategy_docs/QUICK_REFERENCE_CARD.md

# 3. Start implementation
cat strategy_docs/WINNING_STRATEGY_TOP10.md
```

### Tell Claude (New Session):
> "Read strategy_docs/SESSION_STATE.md and continue the Message Notification Router competition."

---

## 📊 KEY INSIGHTS

### 40% Deterministic Coverage
```python
if forwarded_count > 0: action = 'mute'
if message_type == 'scam': action = 'mute'  
if message_type == 'urgent': action = 'notify'
if '@' in text and '?' in text: action = 'notify'
```

### Confidence Hierarchy
- **NOTIFY:** 0.85-0.91
- **MUTE:** 0.81-0.87 (HIGHER than digest!)
- **DIGEST:** 0.78-0.84 (safest fallback)

### User History is Gold
93% of messages have evidence_message_ids

---

## 🏗️ ARCHITECTURE

```
1. RULE-BASED (40% perfect)
   ↓
2. MULTIMODAL FEATURES (text + image + voice)
   ↓
3. USER PERSONALIZATION (history-based)
   ↓
4. ENSEMBLE (XGBoost + RoBERTa)
   ↓
5. CONFIDENCE CALIBRATION
   ↓
6. SAFETY CHECKS & FALLBACK
   ↓
OUTPUT
```

---

## 📁 FOLDER STRUCTURE

```
current_competition_aug26/
├── README.md                 # Official repo readme
├── README_STRATEGY.md        # This file (strategy overview)
├── problem_statement.md      # Official problem
├── AGENTS.md                 # AI tool instructions
├── CLAUDE.md                 # Claude-specific config
│
├── strategy_docs/            # OUR STRATEGY (read these!)
│   ├── SESSION_STATE.md     ⭐ Restart point
│   ├── 00_EXECUTIVE_SUMMARY.md
│   ├── WINNING_STRATEGY_TOP10.md
│   └── QUICK_REFERENCE_CARD.md
│
├── code/                     # Build solution here
│   └── [your implementation]
│
└── dataset/                  # Competition data
    ├── messages.csv          # 264 test messages
    ├── sample_messages.csv   # 70 training examples
    ├── output.csv            # Submit this
    ├── users.csv
    ├── groups.csv
    ├── business_accounts.csv
    ├── message_history.csv   # User history (1,062 messages)
    ├── message_events.csv
    ├── images.csv
    ├── voice_notes.csv
    ├── user_business_history.csv
    ├── group_members.csv
    ├── daily_notification_summary.csv
    └── media/
        ├── images/           # 20 JPG files
        └── audio/            # 13 voice files
```

---

## ⏱️ NEXT STEPS

1. **Read:** `strategy_docs/SESSION_STATE.md` (5 min)
2. **Review:** `strategy_docs/QUICK_REFERENCE_CARD.md` (3 min)
3. **Implement:** Follow `strategy_docs/WINNING_STRATEGY_TOP10.md`
4. **Build:** In `code/` directory
5. **Test:** On `dataset/sample_messages.csv` (70 examples)
6. **Run:** On `dataset/messages.csv` (264 test messages)
7. **Submit:** `dataset/output.csv`

---

## 🎯 EXPECTED RESULT

**92.8% accuracy** → **TOP 10**

- Rule-based: 40% × 100% = 40.0%
- ML: 60% × 88% = 52.8%
- **Total: 92.8%**

---

## 📞 QUICK ACCESS

**Working Directory:**
```bash
cd /c/Users/praje/Downloads/hr_oc_know/competitions/current_competition_aug26
```

**Restart Point:**
```bash
cat strategy_docs/SESSION_STATE.md
```

**Implementation Guide:**
```bash
cat strategy_docs/WINNING_STRATEGY_TOP10.md
```

---

**Status:** Ready for implementation 🚀  
**All strategy documents:** Complete ✅  
**Dataset:** Verified ✅  
**Next:** Build solution in `code/`
