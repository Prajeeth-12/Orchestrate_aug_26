#!/usr/bin/env python3
"""
Quick Script to Extract User History Features

Usage:
    python extract_features.py                    # Extract features for all test messages
    python extract_features.py --samples          # Extract features for sample messages
    python extract_features.py --output my.csv    # Specify output file
"""

import argparse
import sys
from utils.data_loader import quick_load
from features import create_feature_extractor


def main():
    parser = argparse.ArgumentParser(
        description='Extract user history features for message routing'
    )
    parser.add_argument(
        '--samples',
        action='store_true',
        help='Extract features for sample messages instead of test messages'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='message_features.csv',
        help='Output CSV file path (default: message_features.csv)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of messages to process (for testing)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("User History Feature Extraction")
    print("=" * 70)

    # Load data
    print("\nLoading datasets...")
    data = quick_load()

    # Select dataset
    if args.samples:
        print("\nProcessing sample messages...")
        messages_df = data.samples.copy()
    else:
        print("\nProcessing test messages...")
        messages_df = data.messages.copy()

    # Limit if requested
    if args.limit:
        messages_df = messages_df.head(args.limit)
        print(f"Limited to first {args.limit} messages")

    print(f"Total messages: {len(messages_df)}")

    # Create extractor
    print("\nInitializing feature extractor...")
    extractor = create_feature_extractor(data)

    # Extract features
    print("\nExtracting features...")
    result_df = extractor.extract_batch(messages_df)

    # Show summary
    feature_cols = [col for col in result_df.columns if col not in messages_df.columns]
    print(f"\nExtracted {len(feature_cols)} features:")
    for col in sorted(feature_cols):
        print(f"  - {col}")

    # Save results
    print(f"\nSaving to {args.output}...")
    result_df.to_csv(args.output, index=False)

    print("\n" + "=" * 70)
    print(f"SUCCESS Successfully extracted features for {len(result_df)} messages")
    print(f"SUCCESS Output saved to: {args.output}")
    print(f"SUCCESS Total columns: {len(result_df.columns)}")
    print("=" * 70)

    # Show sample statistics
    print("\nFeature Statistics (top 5 features):")
    print("-" * 70)

    key_features = [
        'sender_trust_score',
        'user_reply_rate',
        'category_dismiss_rate',
        'business_interaction_count',
        'group_engagement_rate'
    ]

    for feature in key_features:
        if feature in result_df.columns:
            values = result_df[feature]
            print(f"\n{feature}:")
            print(f"  Mean:   {values.mean():.4f}")
            print(f"  Median: {values.median():.4f}")
            print(f"  Std:    {values.std():.4f}")
            print(f"  Min:    {values.min():.4f}")
            print(f"  Max:    {values.max():.4f}")

    print("\nSUCCESS Done!\n")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
