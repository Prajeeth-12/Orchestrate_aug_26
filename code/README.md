# Message Notification Router - Implementation

**Competition:** HackerRank Orchestrate August 2026  
**Target:** TOP 10 (92.8% accuracy)  
**Status:** 🔨 Building

---

## 🚀 Quick Start

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (if using APIs)
cp ../.env.example .env
# Edit .env to add ANTHROPIC_API_KEY if using Claude Vision
```

### Run
```bash
# 1. Explore data
python explore_data.py

# 2. Test rule-based classifier (40% coverage)
python rule_based_classifier.py

# 3. Train full pipeline (once implemented)
python train_pipeline.py

# 4. Generate predictions
python generate_predictions.py
```

---

## 📁 Code Structure

```
code/
├── README.md                      # This file
├── requirements.txt               # Dependencies
├── IMPLEMENTATION_LOG.md          # Detailed build log
│
├── explore_data.py               # Data exploration (Phase 1)
├── rule_based_classifier.py      # 40% deterministic rules (Phase 1)
│
├── utils/
│   ├── __init__.py
│   └── data_loader.py            # Dataset loading utilities
│
├── features/                      # (Phase 2 - To be created)
│   ├── text_features.py          # Text feature extraction
│   ├── user_features.py          # User history features
│   └── multimodal_features.py    # Image & voice processing
│
├── models/                        # (Phase 3 - To be created)
│   ├── xgboost_classifier.py     # XGBoost model
│   └── roberta_classifier.py     # RoBERTa fine-tuning
│
├── train_pipeline.py             # (Phase 3 - To be created)
├── generate_predictions.py        # (Phase 4 - To be created)
└── evaluate.py                    # (Phase 4 - To be created)
```

---

## 🎯 Implementation Phases

### Phase 1: Foundation ✅ (Current)
- [x] Data loading utilities
- [x] Data exploration
- [x] Rule-based classifier (40% coverage)
- [ ] Validate on samples

### Phase 2: Feature Engineering 📝
- [ ] Text features (RoBERTa embeddings, NLP)
- [ ] User history features (trust scores, engagement)
- [ ] Multimodal processing (images, voice)

### Phase 3: ML Models 📝
- [ ] XGBoost training
- [ ] RoBERTa fine-tuning
- [ ] Ensemble & confidence calibration

### Phase 4: Integration 📝
- [ ] Full pipeline
- [ ] Testing on 70 samples
- [ ] Production run on 264 messages
- [ ] Generate output.csv

---

## 🧪 Testing

### Validate Rule-Based Classifier
```bash
python rule_based_classifier.py
# Expected: 12/30 correct on samples (40% coverage)
```

### Validate Full Pipeline
```bash
python evaluate.py --input ../dataset/sample_messages.csv
# Target: >88% accuracy (62/70 correct)
```

---

## 📊 Expected Performance

| Component | Coverage | Accuracy | Contribution |
|-----------|----------|----------|--------------|
| **Rule-based** | 40% | 100% | 40.0% |
| **ML (XGBoost + RoBERTa)** | 60% | 88% | 52.8% |
| **Total** | 100% | **92.8%** | **TOP 10** 🎯 |

---

## 🔑 Key Implementation Details

### Rule-Based Classifier (40% coverage)
```python
# 100% accuracy rules
if forwarded_count > 0: 
    action = 'mute'

if scam_keywords >= 2:
    action = 'mute'

if '@' in text and '?' in text:
    action = 'notify'
```

### Confidence Ranges (CRITICAL!)
- **NOTIFY:** 0.85-0.91
- **MUTE:** 0.81-0.87 (HIGHER than digest!)
- **DIGEST:** 0.78-0.84

### User History Features (93% coverage)
- Sender trust score (reply rate vs dismiss rate)
- Topic relevance (embedding similarity)
- Opt-in/opt-out status
- Historical engagement patterns

---

## 🐛 Debugging

### If imports fail:
```bash
pip install -r requirements.txt
```

### If data not found:
```bash
ls ../dataset/messages.csv
# Should exist with 265 rows (264 + header)
```

### Check logs:
```bash
cat IMPLEMENTATION_LOG.md
```

---

## 📝 Notes

- **Rule-based first:** Get 40% accuracy to validate approach
- **User history is gold:** 93% of messages have evidence_message_ids
- **Context > Keywords:** Detect negation, specific times
- **Conservative:** When uncertain → DIGEST (safest)
- **Confidence calibration:** MUTE requires HIGHER confidence than DIGEST

---

## 🔄 Resume in New Session

1. Read `IMPLEMENTATION_LOG.md` for what's been built
2. Check `../PROGRESS.md` for overall status
3. Run existing scripts to validate
4. Continue from next phase

---

**Status:** Phase 1 in progress  
**Next:** Validate rule-based, then build feature extraction  
**Updated:** August 1, 2026, 21:35
