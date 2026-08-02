# User History Feature Extractor

## Overview

The `UserHistoryFeatureExtractor` module extracts personalization features from user interaction history to help make intelligent message routing decisions. It analyzes historical user behavior, message patterns, and relationships to generate features that predict whether a user wants to be notified about a new message.

## Installation

```python
# Add to your Python environment
pip install pandas numpy scikit-learn

# Import the module
from features.user_features import create_feature_extractor
from utils.data_loader import quick_load
```

## Quick Start

```python
# Load datasets
data = quick_load()

# Create feature extractor
extractor = create_feature_extractor(data)

# Extract features for a single message
features = extractor.extract(
    user_id='u_001',
    sender_user_id='u_002',
    message_text='Meeting at 3pm?',
    conversation_type='personal'
)

# Extract features for multiple messages
messages_df = data.messages.head(10)
result_df = extractor.extract_batch(messages_df)
```

## Feature Categories

The extractor generates 21 features across 6 categories:

### 1. Sender Trust Score (6 features)

Measures the recipient's historical relationship with the sender:

- **sender_message_count**: Total messages from this sender to this user
- **sender_reply_rate**: Percentage of sender's messages user replied to (0-1)
- **sender_open_rate**: Percentage of sender's messages user opened (0-1)
- **sender_dismiss_rate**: Percentage of sender's messages user dismissed (0-1)
- **sender_report_count**: Number of times user reported this sender
- **sender_trust_score**: Weighted trust metric combining all above factors

**Trust Score Formula:**
```
trust_score = reply_rate * 2.0 + open_rate * 1.0 - dismiss_rate * 3.0 - report_count * 10.0
```

**Interpretation:**
- Positive score (>0): User trusts this sender
- Zero score: Neutral relationship
- Negative score (<0): User likely doesn't want notifications from this sender

### 2. Topic Relevance (1 feature)

Measures similarity between current message and past messages:

- **topic_similarity**: Cosine similarity using TF-IDF vectors (0-1)
  - Uses scikit-learn's TF-IDF vectorizer
  - Compares against historical messages from evidence_message_ids
  - Returns 0.0 if no historical messages available

### 3. User Engagement Patterns (4 features)

Overall user activity levels:

- **user_total_opens**: Total messages user has opened (lifetime)
- **user_total_replies**: Total messages user has replied to (lifetime)
- **user_reply_rate**: Overall reply rate across all messages (0-1)
- **user_notification_load**: Average daily notification count

**High notification load** (>20/day) may indicate user fatigue.

### 4. Dismissal Patterns (2 features)

User's history of dismissing similar messages:

- **similar_dismissals**: Count of similar dismissed messages (by keyword overlap)
- **category_dismiss_rate**: User's dismiss rate for this conversation type (0-1)

**Similarity detection** uses simple keyword matching (3+ common words).

### 5. Business Relationship (4 features)

For business messages only (0 for personal/group):

- **has_recent_order**: User has recent order/booking with this business (0/1)
- **has_opted_in**: User opted into promotional communications (0/1)
- **has_opted_out**: User opted out of promotions (0/1)
- **business_interaction_count**: Total interactions in last 180 days

**Recent order types:** 
- recent_grocery_delivery
- recent_food_delivery
- active_sale_subscription
- active_bank_account

### 6. Group Engagement (4 features)

For group messages only (0 for personal/business):

- **is_group_admin**: User is admin of this group (0/1)
- **group_message_count**: User's message count in this group (last 30d)
- **group_engagement_rate**: User's engagement rate (replies/reads) in this group (0-1)
- **group_is_muted**: User has muted this group (0/1)

**Engagement rate** measures how actively the user participates: replies sent / messages read.

## API Reference

### `UserHistoryFeatureExtractor`

Main class for feature extraction.

#### Constructor

```python
extractor = UserHistoryFeatureExtractor(data_loader)
```

**Parameters:**
- `data_loader` (DatasetLoader): Instance providing access to all CSV datasets

#### Methods

##### `extract()`

Extract features for a single message.

```python
features = extractor.extract(
    user_id: str,
    sender_user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    business_id: Optional[str] = None,
    message_text: str = '',
    evidence_message_ids: Optional[List[str]] = None,
    conversation_type: str = 'personal'
) -> Dict[str, Any]
```

**Parameters:**
- `user_id`: Recipient user ID (required)
- `sender_user_id`: Sender user ID (None for business messages)
- `group_id`: Group ID (None for non-group messages)
- `business_id`: Business account ID (None for non-business messages)
- `message_text`: Message content text
- `evidence_message_ids`: List of relevant historical message IDs
- `conversation_type`: 'personal', 'group', or 'business'

**Returns:**
- Dictionary with 21 feature keys and float values

**Example:**
```python
features = extractor.extract(
    user_id='u_001',
    sender_user_id='u_002',
    group_id='group_003',
    message_text='Team meeting at 3pm',
    evidence_message_ids=['message_0001', 'message_0023'],
    conversation_type='group'
)
```

##### `extract_batch()`

Extract features for multiple messages efficiently.

```python
result_df = extractor.extract_batch(messages_df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `messages_df`: DataFrame with columns:
  - `user_id` (required)
  - `sender_user_id` (optional)
  - `group_id` (optional)
  - `business_id` (optional)
  - `message_text` (optional)
  - `evidence_message_ids` (optional, comma-separated string)
  - `conversation_type` (optional)

**Returns:**
- DataFrame with original columns plus 21 feature columns

**Example:**
```python
messages_df = data.messages.head(100)
result_df = extractor.extract_batch(messages_df)

# Access features
print(result_df[['message_id', 'sender_trust_score', 'user_reply_rate']])
```

### Helper Function

##### `create_feature_extractor()`

Factory function for convenient initialization.

```python
from features.user_features import create_feature_extractor

extractor = create_feature_extractor(data_loader)
```

## Usage Patterns

### Pattern 1: Single Message Analysis

```python
from utils.data_loader import quick_load
from features.user_features import create_feature_extractor

# Setup
data = quick_load()
extractor = create_feature_extractor(data)

# Analyze one message
msg = data.messages.iloc[0]
features = extractor.extract(
    user_id=msg['user_id'],
    sender_user_id=msg.get('sender_user_id'),
    group_id=msg.get('group_id'),
    business_id=msg.get('business_id'),
    message_text=msg.get('message_text', ''),
    conversation_type=msg.get('conversation_type', 'personal')
)

# Make decision
if features['sender_trust_score'] < -1.0:
    action = 'mute'
elif features['group_is_muted'] == 1.0:
    action = 'digest'
else:
    action = 'notify'
```

### Pattern 2: Batch Processing

```python
# Process all test messages
messages_df = data.messages.copy()
features_df = extractor.extract_batch(messages_df)

# Filter by criteria
high_trust = features_df[features_df['sender_trust_score'] > 1.0]
muted_groups = features_df[features_df['group_is_muted'] == 1.0]
opted_out = features_df[features_df['has_opted_out'] == 1.0]
```

### Pattern 3: Rule-Based Classifier Integration

```python
class NotificationRouter:
    def __init__(self, data_loader):
        self.extractor = create_feature_extractor(data_loader)
    
    def classify(self, message_id, user_id, message_text, **kwargs):
        features = self.extractor.extract(
            user_id=user_id,
            message_text=message_text,
            **kwargs
        )
        
        # Rule-based decision tree
        if features['sender_report_count'] > 0:
            return 'mute', 'User reported sender'
        
        if features['has_opted_out'] == 1.0:
            return 'mute', 'User opted out'
        
        if features['group_is_muted'] == 1.0:
            return 'digest', 'Group muted'
        
        if features['sender_trust_score'] > 1.5:
            return 'notify', 'High sender trust'
        
        if features['category_dismiss_rate'] > 0.7:
            return 'digest', 'High dismiss rate for category'
        
        return 'notify', 'Default'
```

### Pattern 4: ML Model Integration

```python
from sklearn.ensemble import RandomForestClassifier

# Prepare training data
samples_df = data.samples.copy()
features_df = extractor.extract_batch(samples_df)

# Extract feature columns only
feature_cols = [col for col in features_df.columns 
                if col not in ['message_id', 'user_id', 'action']]

X = features_df[feature_cols]
y = features_df['action']

# Train model
model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)

# Predict on test set
test_df = data.messages.copy()
test_features = extractor.extract_batch(test_df)
X_test = test_features[feature_cols]

predictions = model.predict(X_test)
```

## Performance Considerations

### Caching Strategy

The extractor caches computed statistics to avoid redundant calculations:

- **Sender statistics**: Cached per user-sender pair
- **User statistics**: Cached per user
- **Business relationships**: Cached per user-business pair
- **Group memberships**: Cached per user-group pair
- **TF-IDF vectors**: Lazy-loaded and cached

**First call is slower** (builds caches), subsequent calls are fast.

### Memory Usage

For the competition dataset:
- Memory footprint: ~10-20 MB
- TF-IDF vectorizer: ~5 MB (500 features)
- Statistics caches: ~5-10 MB

### Processing Time

Typical performance on competition dataset:
- Single message: ~10-50ms (first call includes caching)
- Subsequent calls: ~1-5ms
- Batch (110 messages): ~1-2 seconds

## Handling Edge Cases

### Missing Sender

Business messages have no `sender_user_id`:

```python
features = extractor.extract(
    user_id='u_001',
    sender_user_id=None,  # Business message
    business_id='business_036',
    message_text='Your order is ready'
)
# sender_user_id internally converted to 'business'
```

### Missing Group/Business IDs

Non-applicable IDs should be `None` or empty string:

```python
# Personal message
features = extractor.extract(
    user_id='u_001',
    sender_user_id='u_002',
    group_id=None,  # Not a group message
    business_id=None,  # Not a business message
    message_text='Hey how are you?'
)
# Group and business features will be 0.0
```

### Empty Evidence List

If no historical evidence available:

```python
features = extractor.extract(
    user_id='u_999',  # New user
    message_text='Welcome!',
    evidence_message_ids=[]  # No history
)
# Most features will be 0.0 or default values
```

### Invalid User IDs

If user not in dataset:

```python
features = extractor.extract(user_id='nonexistent_user')
# Returns default values (zeros) gracefully
```

## Feature Importance Guidelines

Based on analysis of the competition data, here are the most predictive features:

**High Importance:**
1. `sender_trust_score` - Strong indicator of user preference
2. `has_opted_out` - Clear signal to mute
3. `group_is_muted` - Explicit user preference
4. `sender_report_count` - Definitive mute signal

**Medium Importance:**
5. `category_dismiss_rate` - Pattern-based prediction
6. `user_reply_rate` - Engagement level
7. `sender_reply_rate` - Relationship strength
8. `business_interaction_count` - Relevance indicator

**Lower Importance:**
9. `topic_similarity` - Useful but needs better embeddings
10. `user_notification_load` - Context modifier
11. Other features - Supplementary signals

## Extending the Module

### Adding New Features

To add custom features:

```python
class ExtendedFeatureExtractor(UserHistoryFeatureExtractor):
    def _compute_custom_features(self, user_id, **kwargs):
        # Your custom feature logic
        return {
            'custom_feature_1': value1,
            'custom_feature_2': value2
        }
    
    def extract(self, user_id, **kwargs):
        features = super().extract(user_id, **kwargs)
        features.update(self._compute_custom_features(user_id, **kwargs))
        return features
```

### Improving Topic Similarity

Replace TF-IDF with embeddings:

```python
from sentence_transformers import SentenceTransformer

class EmbeddingFeatureExtractor(UserHistoryFeatureExtractor):
    def __init__(self, data_loader):
        super().__init__(data_loader)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def _compute_topic_similarity(self, user_id, sender_user_id, 
                                  message_text, evidence_message_ids):
        # Use semantic embeddings instead of TF-IDF
        current_emb = self.model.encode([message_text])
        
        history = self.data_loader.message_history
        historical_texts = history[
            history['message_id'].isin(evidence_message_ids)
        ]['message_text'].fillna('').tolist()
        
        if not historical_texts:
            return 0.0
        
        historical_embs = self.model.encode(historical_texts)
        similarities = cosine_similarity(current_emb, historical_embs)
        
        return float(np.mean(similarities))
```

## Troubleshooting

### Issue: ImportError for sklearn

```bash
pip install scikit-learn
```

### Issue: Low topic_similarity for all messages

TF-IDF requires sufficient corpus. With small datasets, similarities may be uniformly low. Consider:
- Using pre-trained embeddings
- Lowering `min_df` parameter
- Using simpler keyword matching

### Issue: All features are 0.0

Check that:
1. DatasetLoader is properly initialized
2. Dataset path is correct
3. CSV files are loaded successfully
4. User IDs match between datasets

### Issue: Slow performance

First call builds caches. Subsequent calls should be fast. If still slow:
- Reduce TF-IDF `max_features` (default: 500)
- Process in batches rather than one-by-one
- Profile with `cProfile` to identify bottlenecks

## Examples

See `features/example_usage.py` for comprehensive examples:

```bash
cd code/features
python example_usage.py
```

Examples include:
1. Single message extraction
2. Batch extraction
3. Business message analysis
4. Group message analysis
5. Trust score distribution
6. Feature-based recommendation system

## License

Part of HackerRank Orchestrate (August 2026) competition starter code.

## Support

For issues or questions, refer to the competition discussion forum or problem statement documentation.
