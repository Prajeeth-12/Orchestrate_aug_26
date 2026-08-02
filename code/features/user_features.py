"""
User History Feature Extraction Module for Message Notification Router

This module extracts personalization features from user interaction history to help
determine whether a message should be notified immediately, digested for later, or muted.

Features extracted include:
- Sender trust scores based on past interactions
- Topic relevance using text similarity
- User engagement patterns and notification load
- Dismissal patterns and preferences
- Business relationship indicators
- Group engagement metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from collections import defaultdict
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings('ignore')


class UserHistoryFeatureExtractor:
    """
    Extract user history features for personalized message routing decisions.

    This class analyzes historical user behavior, message patterns, and relationships
    to generate features that help predict whether a user wants to be notified
    about a new message.

    Attributes:
        data_loader: DatasetLoader instance providing access to all datasets
        _sender_stats: Cached sender statistics per user
        _user_stats: Cached global user statistics
        _tfidf_vectorizer: TF-IDF vectorizer for text similarity (lazy loaded)
        _message_vectors: Cached TF-IDF vectors for historical messages
    """

    def __init__(self, data_loader):
        """
        Initialize the feature extractor.

        Args:
            data_loader: DatasetLoader instance from utils.data_loader
        """
        self.data_loader = data_loader

        # Cache for computed statistics
        self._sender_stats = None
        self._user_stats = None
        self._business_stats = None
        self._group_stats = None

        # Text similarity components (lazy loaded)
        self._tfidf_vectorizer = None
        self._message_vectors = None
        self._message_text_map = None

    def _ensure_sender_stats_cached(self):
        """Compute and cache sender statistics if not already done."""
        if self._sender_stats is not None:
            return

        events = self.data_loader.message_events
        history = self.data_loader.message_history

        # Merge events with history to get sender info
        merged = events.merge(
            history[['message_id', 'user_id', 'sender_user_id']],
            on='message_id',
            how='left',
            suffixes=('', '_recipient')
        )

        # Group by recipient user_id and sender_user_id
        stats = defaultdict(lambda: defaultdict(lambda: {
            'message_count': 0,
            'opened': 0,
            'replied': 0,
            'dismissed': 0,
            'reported': 0,
            'muted': 0
        }))

        for _, row in merged.iterrows():
            user_id = row['user_id']
            sender_id = row.get('sender_user_id')

            if pd.isna(sender_id):
                sender_id = 'business'  # Business messages have no sender_user_id

            stats[user_id][sender_id]['message_count'] += 1

            if row.get('message_opened') == 1:
                stats[user_id][sender_id]['opened'] += 1
            if row.get('message_replied') == 1:
                stats[user_id][sender_id]['replied'] += 1
            if row.get('notification_dismissed') == 1:
                stats[user_id][sender_id]['dismissed'] += 1
            if row.get('message_reported') == 1:
                stats[user_id][sender_id]['reported'] += 1
            if row.get('muted_after_message') == 1:
                stats[user_id][sender_id]['muted'] += 1

        self._sender_stats = stats

    def _ensure_user_stats_cached(self):
        """Compute and cache global user statistics if not already done."""
        if self._user_stats is not None:
            return

        events = self.data_loader.message_events
        daily_summary = self.data_loader.daily_summary

        stats = {}

        # Aggregate event stats per user
        user_events = events.groupby('user_id').agg({
            'message_opened': 'sum',
            'message_replied': 'sum',
            'notification_dismissed': 'sum',
            'message_reported': 'sum'
        }).to_dict('index')

        # Aggregate daily notification load
        user_daily = daily_summary.groupby('user_id').agg({
            'notifications_sent': 'mean',
            'notifications_dismissed': 'mean'
        }).to_dict('index')

        # Combine
        all_users = set(user_events.keys()) | set(user_daily.keys())

        for user_id in all_users:
            event_data = user_events.get(user_id, {})
            daily_data = user_daily.get(user_id, {})

            total_opens = event_data.get('message_opened', 0)
            total_replies = event_data.get('message_replied', 0)
            total_messages = len(events[events['user_id'] == user_id])

            stats[user_id] = {
                'total_opens': total_opens,
                'total_replies': total_replies,
                'total_messages': total_messages,
                'reply_rate': total_replies / max(total_messages, 1),
                'open_rate': total_opens / max(total_messages, 1),
                'avg_daily_notifications': daily_data.get('notifications_sent', 0),
                'avg_daily_dismissals': daily_data.get('notifications_dismissed', 0)
            }

        self._user_stats = stats

    def _ensure_business_stats_cached(self):
        """Compute and cache business relationship statistics if not already done."""
        if self._business_stats is not None:
            return

        ubh = self.data_loader.user_business_history

        stats = defaultdict(lambda: defaultdict(dict))

        for _, row in ubh.iterrows():
            user_id = row['user_id']
            business_id = row['business_id']

            stats[user_id][business_id] = {
                'has_recent_order': row.get('why_user_knows_account', '') in [
                    'recent_grocery_delivery', 'recent_food_delivery',
                    'active_sale_subscription', 'active_bank_account'
                ],
                'has_opted_in': row.get('allows_promotions', 0) == 1,
                'has_opted_out': pd.notna(row.get('promotions_opted_out_at')),
                'interaction_count': row.get('activity_count_180d', 0),
                'opens_30d': row.get('messages_opened_30d', 0),
                'dismissals_30d': row.get('messages_dismissed_30d', 0),
                'replies_30d': row.get('messages_replied_30d', 0)
            }

        self._business_stats = stats

    def _ensure_group_stats_cached(self):
        """Compute and cache group membership statistics if not already done."""
        if self._group_stats is not None:
            return

        gm = self.data_loader.group_members

        stats = defaultdict(lambda: defaultdict(dict))

        for _, row in gm.iterrows():
            user_id = row['user_id']
            group_id = row['group_id']

            total_sent = row.get('messages_sent_30d', 0)
            total_read = row.get('messages_read_30d', 0)
            replies_sent = row.get('replies_sent_30d', 0)

            # Calculate engagement rate: replies / messages read (how actively they participate)
            # Capped at 1.0 since replies should not exceed reads in normal cases
            engagement_rate = min(replies_sent / max(total_read, 1), 1.0) if total_read > 0 else 0.0

            stats[user_id][group_id] = {
                'is_admin': row.get('role', '') == 'admin',
                'message_count': total_sent,
                'read_count': total_read,
                'engagement_rate': engagement_rate,
                'is_muted': row.get('group_muted_by_user', 0) == 1,
                'dismissals_30d': row.get('notifications_dismissed_30d', 0)
            }

        self._group_stats = stats

    def _ensure_text_similarity_ready(self):
        """Initialize TF-IDF vectorizer and fit on historical messages."""
        if self._tfidf_vectorizer is not None:
            return

        history = self.data_loader.message_history

        # Extract message texts
        messages = history['message_text'].fillna('').tolist()
        message_ids = history['message_id'].tolist()

        # Initialize and fit TF-IDF vectorizer
        self._tfidf_vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=1
        )

        try:
            self._message_vectors = self._tfidf_vectorizer.fit_transform(messages)
            self._message_text_map = dict(zip(message_ids, messages))
        except Exception:
            # Fallback if TF-IDF fails (e.g., empty corpus)
            self._tfidf_vectorizer = None
            self._message_vectors = None
            self._message_text_map = {}

    def get_evidence_message_ids(self, user_id: str, message_text: str, top_k: int = 3,
                                  sender_user_id: str = None, group_id: str = None,
                                  business_id: str = None) -> str:
        """
        Find similar messages from user's history using TF-IDF similarity.
        Scopes search: same sender > same group > same business > any user history.

        Args:
            user_id: Receiving user ID
            message_text: Current message text
            top_k: Number of similar messages to return
            sender_user_id: Sender user ID for scoping
            group_id: Group ID for scoping
            business_id: Business ID for scoping

        Returns:
            Semicolon-separated message IDs or 'none'
        """
        # Ensure TF-IDF is ready
        self._ensure_text_similarity_ready()

        # Handle NaN or invalid message_text
        if self._tfidf_vectorizer is None:
            return 'none'

        if pd.isna(message_text):
            return 'none'

        message_text_str = str(message_text)
        if not message_text_str or len(message_text_str) < 10:
            return 'none'

        history = self.data_loader.message_history

        # Filter user's history
        user_history = history[history['user_id'] == user_id].copy()

        if len(user_history) == 0:
            return 'none'

        # Try scoped search: same sender > same group > same business > full user history
        search_history = user_history
        if sender_user_id and pd.notna(sender_user_id) and 'sender_user_id' in user_history.columns:
            scoped = user_history[user_history['sender_user_id'] == sender_user_id]
            if len(scoped) > 0:
                search_history = scoped

        if len(search_history) == len(user_history):
            if group_id and pd.notna(group_id) and 'group_id' in user_history.columns:
                scoped = user_history[user_history['group_id'] == group_id]
                if len(scoped) > 0:
                    search_history = scoped

        if len(search_history) == len(user_history):
            if business_id and pd.notna(business_id) and 'business_id' in user_history.columns:
                scoped = user_history[user_history['business_id'] == business_id]
                if len(scoped) > 0:
                    search_history = scoped

        try:
            # Get indices of scoped messages in the full history
            search_indices = search_history.index.tolist()

            # Transform current message
            current_vector = self._tfidf_vectorizer.transform([message_text])

            # Compute similarity only with scoped messages
            search_vectors = self._message_vectors[search_indices]
            similarities = cosine_similarity(current_vector, search_vectors)[0]

            # Recency weighting: boost recent messages slightly
            if 'created_at' in history.columns:
                try:
                    timestamps = pd.to_datetime(history.iloc[search_indices]['created_at'], errors='coerce')
                    max_ts = timestamps.max()
                    if pd.notna(max_ts):
                        days_ago = (max_ts - timestamps).dt.total_seconds() / 86400
                        days_ago = days_ago.fillna(days_ago.max() if len(days_ago) > 0 else 30)
                        recency_boost = np.exp(-days_ago.values / 60.0) * 0.15
                        similarities = similarities + recency_boost
                except Exception:
                    pass

            # Get top-k matches with combined score > 0.2
            top_indices = similarities.argsort()[-top_k:][::-1]

            matched_ids = []
            for idx in top_indices:
                if similarities[idx] > 0.2:
                    actual_idx = search_indices[idx]
                    msg_id = history.iloc[actual_idx]['message_id']
                    matched_ids.append(msg_id)

            return ';'.join(matched_ids) if matched_ids else 'none'

        except Exception as e:
            # Fallback on error
            return 'none'

    def _compute_sender_trust_features(
        self,
        user_id: str,
        sender_user_id: Optional[str]
    ) -> Dict[str, float]:
        """
        Compute sender trust score features.

        Args:
            user_id: Recipient user ID
            sender_user_id: Sender user ID (None for business messages)

        Returns:
            Dictionary of sender trust features
        """
        self._ensure_sender_stats_cached()

        # Handle business messages
        if pd.isna(sender_user_id) or sender_user_id == '':
            sender_user_id = 'business'

        sender_data = self._sender_stats.get(user_id, {}).get(sender_user_id, {
            'message_count': 0,
            'opened': 0,
            'replied': 0,
            'dismissed': 0,
            'reported': 0,
            'muted': 0
        })

        message_count = sender_data['message_count']

        # Compute rates
        reply_rate = sender_data['replied'] / max(message_count, 1)
        open_rate = sender_data['opened'] / max(message_count, 1)
        dismiss_rate = sender_data['dismissed'] / max(message_count, 1)
        report_count = sender_data['reported']

        # Compute trust score (weighted combination)
        trust_score = (
            reply_rate * 2.0 +
            open_rate * 1.0 -
            dismiss_rate * 3.0 -
            report_count * 10.0
        )

        return {
            'sender_message_count': float(message_count),
            'sender_reply_rate': float(reply_rate),
            'sender_open_rate': float(open_rate),
            'sender_dismiss_rate': float(dismiss_rate),
            'sender_report_count': float(report_count),
            'sender_trust_score': float(trust_score)
        }

    def _compute_topic_similarity(
        self,
        user_id: str,
        sender_user_id: Optional[str],
        message_text: str,
        evidence_message_ids: List[str]
    ) -> float:
        """
        Compute topic similarity between current message and historical messages.

        Args:
            user_id: Recipient user ID
            sender_user_id: Sender user ID
            message_text: Current message text
            evidence_message_ids: Historical message IDs to compare against

        Returns:
            Average cosine similarity score (0-1)
        """
        self._ensure_text_similarity_ready()

        # Return placeholder if TF-IDF not available
        if self._tfidf_vectorizer is None or not evidence_message_ids:
            return 0.0

        try:
            # Transform current message
            current_vector = self._tfidf_vectorizer.transform([str(message_text) if message_text else ''])

            # Get historical message vectors
            history = self.data_loader.message_history
            historical_messages = history[
                history['message_id'].isin(evidence_message_ids)
            ]['message_text'].fillna('').tolist()

            if not historical_messages:
                return 0.0

            historical_vectors = self._tfidf_vectorizer.transform(historical_messages)

            # Compute similarities
            similarities = cosine_similarity(current_vector, historical_vectors)

            return float(np.mean(similarities))

        except Exception:
            return 0.0

    def _compute_engagement_features(self, user_id: str) -> Dict[str, float]:
        """
        Compute user engagement pattern features.

        Args:
            user_id: User ID

        Returns:
            Dictionary of engagement features
        """
        self._ensure_user_stats_cached()

        user_data = self._user_stats.get(user_id, {
            'total_opens': 0,
            'total_replies': 0,
            'total_messages': 0,
            'reply_rate': 0.0,
            'open_rate': 0.0,
            'avg_daily_notifications': 0.0,
            'avg_daily_dismissals': 0.0
        })

        return {
            'user_total_opens': float(user_data['total_opens']),
            'user_total_replies': float(user_data['total_replies']),
            'user_reply_rate': float(user_data['reply_rate']),
            'user_notification_load': float(user_data['avg_daily_notifications'])
        }

    def _compute_dismissal_features(
        self,
        user_id: str,
        message_text: str,
        conversation_type: str
    ) -> Dict[str, float]:
        """
        Compute dismissal pattern features.

        Args:
            user_id: User ID
            message_text: Current message text
            conversation_type: Type of conversation (personal/group/business)

        Returns:
            Dictionary of dismissal features
        """
        events = self.data_loader.message_events
        history = self.data_loader.message_history

        # Get user's dismissed messages
        user_dismissals = events[
            (events['user_id'] == user_id) &
            (events['notification_dismissed'] == 1)
        ]

        # Count similar dismissals (simple keyword matching)
        similar_dismissals = 0

        if len(user_dismissals) > 0:
            dismissed_message_ids = user_dismissals['message_id'].tolist()
            dismissed_texts = history[
                history['message_id'].isin(dismissed_message_ids)
            ]['message_text'].fillna('')

            # Simple keyword overlap
            # Handle case where message_text might be NaN or non-string
            message_text_str = str(message_text) if pd.notna(message_text) else ''
            current_words = set(re.findall(r'\w+', message_text_str.lower()))

            for text in dismissed_texts:
                text_words = set(re.findall(r'\w+', text.lower()))
                overlap = len(current_words & text_words)
                if overlap >= 3:  # At least 3 common words
                    similar_dismissals += 1

        # Category-specific dismiss rate
        category_messages = history[
            (history['user_id'] == user_id) &
            (history['conversation_type'] == conversation_type)
        ]

        category_dismissed = events[
            (events['user_id'] == user_id) &
            (events['message_id'].isin(category_messages['message_id'])) &
            (events['notification_dismissed'] == 1)
        ]

        category_dismiss_rate = len(category_dismissed) / max(len(category_messages), 1)

        return {
            'similar_dismissals': float(similar_dismissals),
            'category_dismiss_rate': float(category_dismiss_rate)
        }

    def _compute_business_features(
        self,
        user_id: str,
        business_id: Optional[str]
    ) -> Dict[str, float]:
        """
        Compute business relationship features.

        Args:
            user_id: User ID
            business_id: Business account ID (None for non-business messages)

        Returns:
            Dictionary of business relationship features
        """
        self._ensure_business_stats_cached()

        if pd.isna(business_id) or business_id == '':
            return {
                'has_recent_order': 0.0,
                'has_opted_in': 0.0,
                'has_opted_out': 0.0,
                'business_interaction_count': 0.0
            }

        business_data = self._business_stats.get(user_id, {}).get(business_id, {
            'has_recent_order': False,
            'has_opted_in': False,
            'has_opted_out': False,
            'interaction_count': 0
        })

        return {
            'has_recent_order': float(business_data['has_recent_order']),
            'has_opted_in': float(business_data['has_opted_in']),
            'has_opted_out': float(business_data['has_opted_out']),
            'business_interaction_count': float(business_data['interaction_count'])
        }

    def _compute_group_features(
        self,
        user_id: str,
        group_id: Optional[str]
    ) -> Dict[str, float]:
        """
        Compute group engagement features.

        Args:
            user_id: User ID
            group_id: Group ID (None for non-group messages)

        Returns:
            Dictionary of group engagement features
        """
        self._ensure_group_stats_cached()

        if pd.isna(group_id) or group_id == '':
            return {
                'is_group_admin': 0.0,
                'group_message_count': 0.0,
                'group_engagement_rate': 0.0,
                'group_is_muted': 0.0
            }

        group_data = self._group_stats.get(user_id, {}).get(group_id, {
            'is_admin': False,
            'message_count': 0,
            'engagement_rate': 0.0,
            'is_muted': False
        })

        return {
            'is_group_admin': float(group_data['is_admin']),
            'group_message_count': float(group_data['message_count']),
            'group_engagement_rate': float(group_data['engagement_rate']),
            'group_is_muted': float(group_data['is_muted'])
        }

    def extract(
        self,
        user_id: str,
        sender_user_id: Optional[str] = None,
        group_id: Optional[str] = None,
        business_id: Optional[str] = None,
        message_text: str = '',
        evidence_message_ids: Optional[List[str]] = None,
        conversation_type: str = 'personal'
    ) -> Dict[str, Any]:
        """
        Extract all user history features for a single message.

        Args:
            user_id: Recipient user ID
            sender_user_id: Sender user ID (None for business messages)
            group_id: Group ID (None for non-group messages)
            business_id: Business ID (None for non-business messages)
            message_text: Message content text
            evidence_message_ids: List of relevant historical message IDs
            conversation_type: Type of conversation (personal/group/business)

        Returns:
            Dictionary containing all extracted features with descriptive keys
        """
        if evidence_message_ids is None:
            evidence_message_ids = []

        features = {}

        # 1. Sender Trust Score
        features.update(self._compute_sender_trust_features(user_id, sender_user_id))

        # 2. Topic Relevance
        features['topic_similarity'] = self._compute_topic_similarity(
            user_id, sender_user_id, message_text, evidence_message_ids
        )

        # 3. Engagement Patterns
        features.update(self._compute_engagement_features(user_id))

        # 4. Dismissal Patterns
        features.update(self._compute_dismissal_features(
            user_id, message_text, conversation_type
        ))

        # 5. Business Relationship
        features.update(self._compute_business_features(user_id, business_id))

        # 6. Group Engagement
        features.update(self._compute_group_features(user_id, group_id))

        return features

    def extract_batch(self, messages_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features for a batch of messages.

        Args:
            messages_df: DataFrame with columns:
                - user_id: Recipient user ID
                - sender_user_id: Sender user ID (optional)
                - group_id: Group ID (optional)
                - business_id: Business ID (optional)
                - message_text: Message content
                - evidence_message_ids: Comma-separated list of evidence IDs (optional)
                - conversation_type: Type of conversation (optional)

        Returns:
            DataFrame with original columns plus all extracted feature columns
        """
        result_df = messages_df.copy()

        # Initialize feature columns
        feature_names = [
            'sender_message_count', 'sender_reply_rate', 'sender_open_rate',
            'sender_dismiss_rate', 'sender_report_count', 'sender_trust_score',
            'topic_similarity', 'user_total_opens', 'user_total_replies',
            'user_reply_rate', 'user_notification_load', 'similar_dismissals',
            'category_dismiss_rate', 'has_recent_order', 'has_opted_in',
            'has_opted_out', 'business_interaction_count', 'is_group_admin',
            'group_message_count', 'group_engagement_rate', 'group_is_muted'
        ]

        for feature in feature_names:
            result_df[feature] = 0.0

        # Extract features for each message
        for idx, row in messages_df.iterrows():
            # Parse evidence message IDs
            evidence_ids = []
            if 'evidence_message_ids' in row and pd.notna(row['evidence_message_ids']):
                evidence_str = str(row['evidence_message_ids'])
                if evidence_str not in ['', 'none', 'None']:
                    evidence_ids = [eid.strip() for eid in evidence_str.split(',')]

            # Extract features
            features = self.extract(
                user_id=row['user_id'],
                sender_user_id=row.get('sender_user_id'),
                group_id=row.get('group_id'),
                business_id=row.get('business_id'),
                message_text=row.get('message_text', ''),
                evidence_message_ids=evidence_ids,
                conversation_type=row.get('conversation_type', 'personal')
            )

            # Assign features to dataframe
            for feature_name, feature_value in features.items():
                result_df.at[idx, feature_name] = feature_value

        return result_df


def create_feature_extractor(data_loader) -> UserHistoryFeatureExtractor:
    """
    Factory function to create a UserHistoryFeatureExtractor instance.

    Args:
        data_loader: DatasetLoader instance

    Returns:
        Configured UserHistoryFeatureExtractor

    Example:
        >>> from utils.data_loader import quick_load
        >>> from features.user_features import create_feature_extractor
        >>>
        >>> data = quick_load()
        >>> extractor = create_feature_extractor(data)
        >>>
        >>> features = extractor.extract(
        ...     user_id='u_001',
        ...     sender_user_id='u_002',
        ...     message_text='Meeting at 3pm?'
        ... )
    """
    return UserHistoryFeatureExtractor(data_loader)


if __name__ == "__main__":
    # Example usage and testing
    import sys
    sys.path.append('..')

    from utils.data_loader import quick_load

    print("Loading datasets...")
    data = quick_load()

    print("\nInitializing feature extractor...")
    extractor = create_feature_extractor(data)

    print("\nExtracting features for sample message...")

    # Get first test message
    test_msg = data.messages.iloc[0]

    features = extractor.extract(
        user_id=test_msg['user_id'],
        sender_user_id=test_msg.get('sender_user_id'),
        group_id=test_msg.get('group_id'),
        business_id=test_msg.get('business_id'),
        message_text=test_msg.get('message_text', ''),
        conversation_type=test_msg.get('conversation_type', 'personal')
    )

    print("\n📊 Extracted Features:")
    print("-" * 60)
    for feature_name, feature_value in sorted(features.items()):
        print(f"  {feature_name:30s}: {feature_value:.4f}")

    print("\n✅ Feature extraction test complete!")
