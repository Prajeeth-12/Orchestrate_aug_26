# Text Feature Extractor - Integration Guide

Quick guide for integrating the TextFeatureExtractor into your Message Notification Router pipeline.

## 1. Basic Integration (5 minutes)

```python
from features.text_features import TextFeatureExtractor
import pandas as pd

# Load your messages
messages_df = pd.read_csv('dataset/messages.csv')

# Initialize extractor
extractor = TextFeatureExtractor()

# Extract features
text_features = extractor.extract_batch(messages_df['content'])

# Add message_id back
text_features.insert(0, 'message_id', messages_df['message_id'].values)

# Now you have 28 additional features for each message!
print(f"Extracted {len(text_features.columns) - 1} features")
```

## 2. Combine with Other Features

```python
# Load existing features
user_features = pd.read_csv('user_features.csv')
group_features = pd.read_csv('group_features.csv')

# Extract text features
text_features = extractor.extract_batch(messages_df['content'])
text_features.insert(0, 'message_id', messages_df['message_id'].values)

# Merge all features
all_features = messages_df[['message_id', 'user_id', 'conversation_type']]
all_features = all_features.merge(text_features, on='message_id', how='left')
all_features = all_features.merge(user_features, on='user_id', how='left')
# ... merge other features

# Now ready for model training
```

## 3. Rule-Based Router Example

```python
from features.text_features import TextFeatureExtractor

def classify_message(text):
    """Simple rule-based classifier using text features."""
    extractor = TextFeatureExtractor()
    features = extractor.extract(text)
    
    # MUTE: High spam score
    spam_score = (
        features['scam_keyword_count'] * 2 +
        features['has_instruction_injection'] * 5 +
        features['spam_pattern_score'] * 3 +
        features['has_suspicious_link'] * 3 +
        features['caps_word_ratio'] * 2
    )
    if spam_score > 10:
        return 'mute', 'High spam score', spam_score
    
    # NOTIFY: High urgency
    urgency_score = (
        features['has_specific_time'] * 2 +
        features['has_today'] * 2 +
        features['has_now'] * 1.5 +
        features['has_deadline'] * 1.5 +
        features['urgency_keyword_count'] * 1 +
        features['at_mention_with_question'] * 1 -
        features['has_negation_of_urgency'] * 3
    )
    if urgency_score > 5:
        return 'notify', 'High urgency', urgency_score
    
    # DIGEST: Low urgency or courtesy messages
    if features['has_gratitude'] or features['flexible_timing']:
        return 'digest', 'Low priority/courtesy', 0
    
    # Default: NOTIFY
    return 'notify', 'Default', 0

# Example usage
action, reason, score = classify_message("@john urgent: review by 3pm today?")
print(f"Action: {action}, Reason: {reason}, Score: {score}")
```

## 4. ML Model Integration

```python
from features.text_features import TextFeatureExtractor
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

# Training
train_df = pd.read_csv('train_messages.csv')
extractor = TextFeatureExtractor()

# Extract text features
text_features = extractor.extract_batch(train_df['content'])

# Select important features for model
feature_cols = [
    'has_at_mention', 'has_question', 'at_mention_with_question',
    'word_count', 'sentence_count',
    'has_specific_time', 'has_today', 'has_now', 'has_deadline',
    'urgency_keyword_count', 'has_negation_of_urgency',
    'scam_keyword_count', 'has_instruction_injection',
    'spam_pattern_score', 'has_suspicious_link',
    'time_specificity', 'same_day_indicator', 'flexible_timing',
    'has_frustration', 'has_gratitude', 'forward_indicator_count'
]

X = text_features[feature_cols]
y = train_df['action']

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# Feature importance
importances = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("Top 10 most important features:")
print(importances.head(10))
```

## 5. Production Pipeline

```python
from features.text_features import TextFeatureExtractor
import pandas as pd
import pickle

class MessageRouter:
    """Production message router with text feature extraction."""
    
    def __init__(self, model_path='model.pkl'):
        self.text_extractor = TextFeatureExtractor()
        self.model = pickle.load(open(model_path, 'rb'))
        
    def route_message(self, message_text, user_features=None):
        """
        Route a single message.
        
        Args:
            message_text: Text content of message
            user_features: Optional dict of user-specific features
            
        Returns:
            action: 'notify', 'digest', or 'mute'
            confidence: Confidence score (0-1)
            reason: Human-readable explanation
        """
        # Extract text features
        text_features = self.text_extractor.extract(message_text)
        
        # Combine with user features if provided
        if user_features:
            all_features = {**text_features, **user_features}
        else:
            all_features = text_features
        
        # Convert to DataFrame for model
        features_df = pd.DataFrame([all_features])
        
        # Get prediction
        action = self.model.predict(features_df)[0]
        proba = self.model.predict_proba(features_df)[0]
        confidence = max(proba)
        
        # Generate reason
        reason = self._generate_reason(text_features, action)
        
        return action, confidence, reason
    
    def _generate_reason(self, features, action):
        """Generate human-readable reason for routing decision."""
        reasons = []
        
        if action == 'notify':
            if features['has_specific_time']:
                reasons.append("specific time mentioned")
            if features['urgency_keyword_count'] > 0:
                reasons.append("urgency keywords detected")
            if features['at_mention_with_question']:
                reasons.append("direct question with mention")
                
        elif action == 'mute':
            if features['scam_keyword_count'] > 3:
                reasons.append("scam keywords detected")
            if features['has_suspicious_link']:
                reasons.append("suspicious link")
            if features['spam_pattern_score'] > 0.5:
                reasons.append("spam patterns")
                
        elif action == 'digest':
            if features['has_gratitude']:
                reasons.append("courtesy message")
            if features['flexible_timing']:
                reasons.append("flexible timing")
            if features['has_negation_of_urgency']:
                reasons.append("not urgent")
        
        return '; '.join(reasons) if reasons else 'model prediction'
    
    def route_batch(self, messages_df):
        """Route multiple messages efficiently."""
        # Extract text features for all messages
        text_features = self.text_extractor.extract_batch(
            messages_df['content']
        )
        
        # Predict
        actions = self.model.predict(text_features)
        probas = self.model.predict_proba(text_features)
        confidences = probas.max(axis=1)
        
        # Add to results
        results = messages_df.copy()
        results['action'] = actions
        results['confidence'] = confidences
        
        return results

# Usage
router = MessageRouter('trained_model.pkl')

# Single message
action, confidence, reason = router.route_message(
    "@john urgent question by 3pm?"
)
print(f"Action: {action}, Confidence: {confidence:.2f}, Reason: {reason}")

# Batch processing
messages_df = pd.read_csv('dataset/messages.csv')
results = router.route_batch(messages_df)
results.to_csv('output.csv', index=False)
```

## 6. Feature Selection Tips

Not all 28 features may be useful for your model. Here's how to select the best ones:

```python
from sklearn.feature_selection import SelectKBest, f_classif
from features.text_features import TextFeatureExtractor

# Extract all features
extractor = TextFeatureExtractor()
text_features = extractor.extract_batch(train_df['content'])

# Select top K features
selector = SelectKBest(f_classif, k=15)
X_selected = selector.fit_transform(text_features, y)

# Get selected feature names
feature_names = text_features.columns
selected_mask = selector.get_support()
selected_features = feature_names[selected_mask].tolist()

print(f"Selected {len(selected_features)} features:")
print(selected_features)
```

## 7. Performance Optimization

For large datasets (100K+ messages):

```python
from features.text_features import TextFeatureExtractor
import pandas as pd

def extract_features_chunked(messages, chunk_size=5000):
    """Extract features in chunks to manage memory."""
    extractor = TextFeatureExtractor()
    
    results = []
    for i in range(0, len(messages), chunk_size):
        chunk = messages[i:i+chunk_size]
        chunk_features = extractor.extract_batch(chunk)
        results.append(chunk_features)
    
    return pd.concat(results, ignore_index=True)

# Usage
messages = pd.read_csv('large_dataset.csv')['content']
features = extract_features_chunked(messages, chunk_size=5000)
```

## 8. Custom Feature Engineering

Extend the extractor with domain-specific features:

```python
from features.text_features import TextFeatureExtractor
import re

class CustomTextExtractor(TextFeatureExtractor):
    """Extended extractor with custom features."""
    
    def extract(self, text):
        # Get base features
        features = super().extract(text)
        
        # Add custom features
        features['has_meeting_time'] = bool(
            re.search(r'\b(meeting|call|sync)\b.*\b\d+:\d+', text, re.I)
        )
        features['has_action_request'] = bool(
            re.search(r'\b(please|can you|could you)\b', text, re.I)
        )
        features['has_order_number'] = bool(
            re.search(r'\border\s*#?\s*\d+', text, re.I)
        )
        
        return features

# Usage
custom_extractor = CustomTextExtractor()
features = custom_extractor.extract("Please join meeting at 3pm")
print(features['has_meeting_time'])  # True
print(features['has_action_request'])  # True
```

## 9. Debugging and Validation

```python
from features.text_features import TextFeatureExtractor

def debug_extraction(text):
    """Print detailed feature extraction for debugging."""
    extractor = TextFeatureExtractor()
    features = extractor.extract(text)
    
    print(f"Text: {text}\n")
    print("Extracted Features:")
    print("-" * 60)
    
    # Group by category
    categories = {
        'Structural': [
            'has_at_mention', 'has_question', 'word_count', 
            'sentence_count', 'has_url', 'has_phone', 'has_email'
        ],
        'Urgency': [
            'has_specific_time', 'has_today', 'has_now', 
            'urgency_keyword_count', 'has_negation_of_urgency'
        ],
        'Spam': [
            'scam_keyword_count', 'has_instruction_injection',
            'spam_pattern_score', 'has_suspicious_link'
        ],
        'Sentiment': [
            'has_frustration', 'has_gratitude', 'has_greeting'
        ]
    }
    
    for category, feature_list in categories.items():
        print(f"\n{category}:")
        for feature in feature_list:
            if feature in features:
                value = features[feature]
                if value not in [0, 0.0, False]:  # Show non-zero values
                    print(f"  {feature}: {value}")

# Test on sample messages
debug_extraction("@john urgent: review by 3pm today?")
debug_extraction("URGENT!!! Your account is BLOCKED!!!")
debug_extraction("Thanks for your help yesterday!")
```

## 10. Common Issues and Solutions

### Issue: Some features always zero

**Cause**: Messages don't contain those patterns  
**Solution**: This is normal. Not all messages will trigger all features.

### Issue: High false positive spam detection

**Cause**: Legitimate messages using caps or urgency keywords  
**Solution**: Adjust spam scoring thresholds or combine with sender trust features.

### Issue: Slow batch processing

**Cause**: Processing too many messages at once  
**Solution**: Use chunked processing (see Section 7).

## Quick Reference

```python
# Import
from features.text_features import TextFeatureExtractor

# Initialize
extractor = TextFeatureExtractor()

# Single message
features = extractor.extract(text)

# Batch
features_df = extractor.extract_batch(texts_list)

# Feature info
names = extractor.get_feature_names()  # List of 28 feature names
descriptions = extractor.get_feature_descriptions()  # Dict of descriptions

# Total features: 28
# Processing speed: ~1000 messages/second
```

## Next Steps

1. Run `text_features_example.py` to see demonstrations
2. Run `test_text_features.py` to verify installation
3. Read `TEXT_FEATURES_README.md` for detailed feature documentation
4. Integrate into your pipeline using examples above
5. Experiment with feature combinations for best performance

## Files

- `text_features.py` - Main module (18KB)
- `test_text_features.py` - Unit tests (8KB)
- `text_features_example.py` - Usage examples (10KB)
- `TEXT_FEATURES_README.md` - Full documentation (14KB)
- `INTEGRATION_GUIDE.md` - This file

Happy routing!
