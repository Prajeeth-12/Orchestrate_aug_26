# Quick Start for Opus 4.6

**Goal:** Improve from 82-85/100 to 90-92/100 (TOP 5%)

## **TL;DR - Do These 3 Things**

### **1. Fix MessageTypeInferer (30 min) → +5 points**

**File:** `code/train_pipeline.py` lines 169-258

**Quick fixes:**
```python
# A. Handle NaN text (line 174)
if pd.isna(text) or text == '':
    return 'spam' if action == 'mute' else 'unknown'

# B. Strengthen scam detection (line 210)
scam_terms = [...existing..., 'workspace access', 'account locked', 
              'expire today', 'suspended']

# C. Add @mention helper (line 239)
def _has_mention_with_question(self, text: str, features: Optional[Dict[str, Any]]) -> bool:
    if not features:
        return '@' in text and '?' in text
    return features.get('has_at_mention') and features.get('has_question')

# D. Check @mention before payment (line 183)
if self._has_mention_with_question(text_lower, features):
    return 'urgent'
if self._is_payment(text_lower):
    return 'payment'
```

**Test after each fix:**
```bash
python code/main.py --input dataset/sample_messages.csv --output sample_output_v2.csv
python -c "
import pandas as pd
s = pd.read_csv('dataset/sample_messages.csv')
o = pd.read_csv('sample_output_v2.csv')
m = s.merge(o, on='message_id', suffixes=('_true', '_pred'))
print(f'Type accuracy: {(m.message_type_true == m.message_type_pred).mean()*100:.1f}%')
"
```

**Target:** 76.7% → 85%+

---

### **2. Add Evidence Scoping (15 min) → +2 points**

**File:** `code/features/user_features.py` line ~250

**Add parameters:**
```python
def get_evidence_message_ids(self, user_id: str, message_text: str, top_k: int = 3,
                              sender_user_id: str = None, 
                              group_id: str = None,
                              business_id: str = None) -> str:
```

**Add scoping logic before TF-IDF:**
```python
user_history = history[history['user_id'] == user_id].copy()

# NEW: Scope by context
scoped = user_history
if pd.notna(sender_user_id):
    scoped = scoped[scoped['sender_user_id'] == sender_user_id]
if len(scoped) == 0 and pd.notna(group_id):
    scoped = user_history[user_history['group_id'] == group_id]

search_history = scoped if len(scoped) > 0 else user_history
# ... run TF-IDF on search_history instead of user_history ...
```

**Wire it up in `train_pipeline.py` lines 626 & 660:**
```python
evidence_ids = self.user_extractor.get_evidence_message_ids(
    user_id=message_row['user_id'],
    message_text=message_row.get('message_text', ''),
    sender_user_id=message_row.get('sender_user_id'),  # NEW
    group_id=message_row.get('group_id'),              # NEW
    business_id=message_row.get('business_id'),        # NEW
    top_k=3
)
```

---

### **3. Validate Everything (15 min)**

**Create `code/validate_final.py`:**
```python
import pandas as pd

def validate():
    df = pd.read_csv('output.csv')
    samples = pd.read_csv('dataset/sample_messages.csv')
    
    # Schema
    assert len(df) == 110
    assert df['message_id'].nunique() == 110
    
    # Accuracy on samples (if IDs match)
    # Use sample_output.csv for validation instead
    sample_out = pd.read_csv('sample_output.csv')
    merged = samples.merge(sample_out, on='message_id', suffixes=('_true', '_pred'))
    
    action_acc = (merged['action_true'] == merged['action_pred']).mean()
    type_acc = (merged['message_type_true'] == merged['message_type_pred']).mean()
    
    print(f"Action: {action_acc*100:.1f}%")
    print(f"Type: {type_acc*100:.1f}%")
    
    assert action_acc == 1.0, "Action accuracy dropped!"
    assert type_acc >= 0.85, f"Type accuracy {type_acc*100:.1f}% < 85% target"
    
    print("✓ ALL CHECKS PASS")

if __name__ == "__main__":
    validate()
```

**Run:**
```bash
# Generate final predictions
python code/main.py --input dataset/messages.csv --output output.csv
python code/main.py --input dataset/sample_messages.csv --output sample_output.csv

# Validate
python code/validate_final.py
```

---

## **That's It**

Three focused tasks:
1. Fix MessageTypeInferer → 76.7% to 85%+
2. Add evidence scoping → 33% to 45%+
3. Validate everything passes

**Expected result: 90-92/100 → TOP 5%**

---

## **If You Want More Detail**

Read `OPUS_HANDOFF.md` for:
- Complete error analysis
- All 7 known type errors
- Edge case handling
- Comprehensive validation suite
- Score breakdown by component

---

## **Current Baseline**

```bash
# Measure starting point
python code/main.py --input dataset/sample_messages.csv --output sample_output.csv
python -c "
import pandas as pd
s = pd.read_csv('dataset/sample_messages.csv')
o = pd.read_csv('sample_output.csv')
m = s.merge(o, on='message_id', suffixes=('_true', '_pred'))
print('BASELINE:')
print(f'Action: {(m.action_true == m.action_pred).mean()*100:.1f}%')
print(f'Type: {(m.message_type_true == m.message_type_pred).mean()*100:.1f}%')
"
```

**Expected:** Action 100%, Type 76.7%

**After your work:** Action 100%, Type 85%+

**Go!**
