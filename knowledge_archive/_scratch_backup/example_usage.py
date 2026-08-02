"""
Example Usage of TextFeatureExtractor for Message Notification Router

Demonstrates how to integrate text feature extraction into the main pipeline.
"""

import sys
sys.path.append('..')

from utils.data_loader import quick_load
from features.user_features import create_feature_extractor
import pandas as pd


def example_1_single_message_extraction():
    """Example 1: Extract features for a single message"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Single Message Feature Extraction")
    print("=" * 70)

    # Load data
    data = quick_load()

    # Create feature extractor
    extractor = create_feature_extractor(data)

    # Get a test message
    msg = data.messages.iloc[0]

    print(f"\nMessage: {msg['message_id']}")
    print(f"User: {msg['user_id']}")
    print(f"Type: {msg['conversation_type']}")
    print(f"Text preview: {str(msg['message_text'])[:60]}...")

    # Extract features
    features = extractor.extract(
        user_id=msg['user_id'],
        sender_user_id=msg.get('sender_user_id'),
        group_id=msg.get('group_id'),
        business_id=msg.get('business_id'),
        message_text=msg.get('message_text', ''),
        conversation_type=msg.get('conversation_type', 'personal')
    )

    print(f"\nExtracted {len(features)} features:")
    print("-" * 70)

    # Group features by category
    categories = {
        'Sender Trust': ['sender_message_count', 'sender_reply_rate', 'sender_open_rate',
                        'sender_dismiss_rate', 'sender_report_count', 'sender_trust_score'],
        'Topic Relevance': ['topic_similarity'],
        'User Engagement': ['user_total_opens', 'user_total_replies', 'user_reply_rate',
                           'user_notification_load'],
        'Dismissal Patterns': ['similar_dismissals', 'category_dismiss_rate'],
        'Business Relationship': ['has_recent_order', 'has_opted_in', 'has_opted_out',
                                 'business_interaction_count'],
        'Group Engagement': ['is_group_admin', 'group_message_count', 'group_engagement_rate',
                            'group_is_muted']
    }

    for category, feature_list in categories.items():
        print(f"\n{category}:")
        for feature_name in feature_list:
            if feature_name in features:
                value = features[feature_name]
                print(f"  {feature_name:30s}: {value:.4f}")


def example_2_batch_extraction():
    """Example 2: Extract features for multiple messages at once"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Batch Feature Extraction")
    print("=" * 70)

    # Load data
    data = quick_load()

    # Create feature extractor
    extractor = create_feature_extractor(data)

    # Get first 10 test messages
    messages_df = data.messages.head(10).copy()

    print(f"\nProcessing {len(messages_df)} messages...")

    # Extract features for all messages
    result_df = extractor.extract_batch(messages_df)

    print(f"\nOriginal columns: {len(messages_df.columns)}")
    print(f"Result columns: {len(result_df.columns)}")
    print(f"Features added: {len(result_df.columns) - len(messages_df.columns)}")

    # Show summary statistics for key features
    print("\nFeature Summary Statistics:")
    print("-" * 70)

    key_features = [
        'sender_trust_score',
        'user_reply_rate',
        'category_dismiss_rate',
        'business_interaction_count'
    ]

    for feature in key_features:
        print(f"\n{feature}:")
        print(f"  Mean: {result_df[feature].mean():.4f}")
        print(f"  Std:  {result_df[feature].std():.4f}")
        print(f"  Min:  {result_df[feature].min():.4f}")
        print(f"  Max:  {result_df[feature].max():.4f}")


def example_3_business_message_analysis():
    """Example 3: Analyze business message features"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Business Message Feature Analysis")
    print("=" * 70)

    # Load data
    data = quick_load()

    # Create feature extractor
    extractor = create_feature_extractor(data)

    # Get business messages only
    business_messages = data.messages[
        data.messages['conversation_type'] == 'business'
    ].head(5).copy()

    print(f"\nAnalyzing {len(business_messages)} business messages...")

    # Extract features
    result_df = extractor.extract_batch(business_messages)

    # Show business-specific features
    print("\nBusiness-Specific Features:")
    print("-" * 70)

    business_features = [
        'has_recent_order',
        'has_opted_in',
        'has_opted_out',
        'business_interaction_count'
    ]

    for _, row in result_df.iterrows():
        print(f"\nMessage: {row['message_id']} (User: {row['user_id']})")
        for feature in business_features:
            print(f"  {feature:30s}: {row[feature]:.1f}")


def example_4_group_message_analysis():
    """Example 4: Analyze group message features"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Group Message Feature Analysis")
    print("=" * 70)

    # Load data
    data = quick_load()

    # Create feature extractor
    extractor = create_feature_extractor(data)

    # Get group messages only
    group_messages = data.messages[
        data.messages['conversation_type'] == 'group'
    ].head(5).copy()

    print(f"\nAnalyzing {len(group_messages)} group messages...")

    # Extract features
    result_df = extractor.extract_batch(group_messages)

    # Show group-specific features
    print("\nGroup-Specific Features:")
    print("-" * 70)

    group_features = [
        'is_group_admin',
        'group_message_count',
        'group_engagement_rate',
        'group_is_muted'
    ]

    for _, row in result_df.iterrows():
        print(f"\nMessage: {row['message_id']} (User: {row['user_id']}, Group: {row['group_id']})")
        for feature in group_features:
            print(f"  {feature:30s}: {row[feature]:.4f}")


def example_5_trust_score_distribution():
    """Example 5: Analyze sender trust score distribution"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Sender Trust Score Distribution")
    print("=" * 70)

    # Load data
    data = quick_load()

    # Create feature extractor
    extractor = create_feature_extractor(data)

    # Extract features for all messages
    messages_df = data.messages.copy()
    result_df = extractor.extract_batch(messages_df)

    print(f"\nAnalyzed {len(result_df)} messages")

    # Group by conversation type
    print("\nTrust Score by Conversation Type:")
    print("-" * 70)

    for conv_type in ['personal', 'group', 'business']:
        subset = result_df[result_df['conversation_type'] == conv_type]
        if len(subset) > 0:
            print(f"\n{conv_type.capitalize()}:")
            print(f"  Count:       {len(subset)}")
            print(f"  Mean Trust:  {subset['sender_trust_score'].mean():.4f}")
            print(f"  Median Trust:{subset['sender_trust_score'].median():.4f}")
            print(f"  Max Trust:   {subset['sender_trust_score'].max():.4f}")
            print(f"  Min Trust:   {subset['sender_trust_score'].min():.4f}")


def example_6_feature_based_recommendation():
    """Example 6: Simple feature-based notification recommendation"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Feature-Based Notification Recommendation")
    print("=" * 70)

    # Load data
    data = quick_load()

    # Create feature extractor
    extractor = create_feature_extractor(data)

    # Extract features for a sample message
    msg = data.messages.iloc[5]
    features = extractor.extract(
        user_id=msg['user_id'],
        sender_user_id=msg.get('sender_user_id'),
        group_id=msg.get('group_id'),
        business_id=msg.get('business_id'),
        message_text=msg.get('message_text', ''),
        conversation_type=msg.get('conversation_type', 'personal')
    )

    print(f"\nMessage: {msg['message_id']}")
    print(f"User: {msg['user_id']}")
    print(f"Type: {msg['conversation_type']}")

    # Simple rule-based recommendation
    print("\nFeature Analysis:")
    print("-" * 70)

    recommendation = "NOTIFY"  # Default
    reasons = []

    # Check sender trust
    if features['sender_trust_score'] < -1.0:
        recommendation = "MUTE"
        reasons.append("Low sender trust score")

    # Check if opted out from business
    if features['has_opted_out'] == 1.0:
        recommendation = "MUTE"
        reasons.append("User opted out from business")

    # Check if group is muted
    if features['group_is_muted'] == 1.0:
        recommendation = "DIGEST"
        reasons.append("Group is muted by user")

    # Check dismissal patterns
    if features['category_dismiss_rate'] > 0.8:
        recommendation = "DIGEST"
        reasons.append("High dismissal rate for this category")

    # Check high notification load
    if features['user_notification_load'] > 20:
        if features['sender_trust_score'] < 1.0:
            recommendation = "DIGEST"
            reasons.append("High notification load + low trust")

    print(f"\nRecommendation: {recommendation}")
    if reasons:
        print("Reasons:")
        for reason in reasons:
            print(f"  - {reason}")
    else:
        print("Reasons: Good engagement indicators")

    print("\nKey Features:")
    print(f"  Sender Trust Score: {features['sender_trust_score']:.2f}")
    print(f"  User Reply Rate: {features['user_reply_rate']:.2f}")
    print(f"  Category Dismiss Rate: {features['category_dismiss_rate']:.2f}")
    print(f"  Notification Load: {features['user_notification_load']:.1f}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("UserHistoryFeatureExtractor - Usage Examples")
    print("=" * 70)

    try:
        example_1_single_message_extraction()
        example_2_batch_extraction()
        example_3_business_message_analysis()
        example_4_group_message_analysis()
        example_5_trust_score_distribution()
        example_6_feature_based_recommendation()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
