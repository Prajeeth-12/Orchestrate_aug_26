"""
Example Usage: GPU-Trained Message Routing Pipeline

This script demonstrates how to use the trained pipeline for:
1. Single message prediction
2. Batch prediction
3. Integration with competition submission
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'code'))

from utils.data_loader import DatasetLoader
from train_pipeline import MessageRoutingPipeline


def example_single_prediction():
    """Example: Predict action for a single message"""
    print("\n" + "="*80)
    print("EXAMPLE 1: SINGLE MESSAGE PREDICTION")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    data_loader = DatasetLoader(dataset_path=str(project_root / "dataset"))

    # Load trained pipeline
    print("📦 Loading trained pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)
    pipeline.load(model_dir=str(project_root / "models"))
    print("✓ Pipeline loaded successfully")

    # Create test message
    message = pd.Series({
        'message_id': 'test_001',
        'user_id': 'u_001',
        'message_text': '@john Can you review this by 3pm today? Urgent!',
        'conversation_type': 'group',
        'group_id': 'group_001',
        'sender_user_id': 'u_002',
        'business_id': '',
        'forwarded_count': 0,
        'media_type': '',
        'media_id': '',
        'created_at': '2026-08-01 14:30:00',
        'evidence_message_ids': ''
    })

    # Predict
    print("\n🔮 Making prediction...")
    result = pipeline.predict(message)

    # Display result
    print("\n📊 Prediction Result:")
    print("-" * 80)
    print(f"Message: {message['message_text'][:60]}...")
    print(f"\nAction: {result['action'].upper()}")
    print(f"Confidence: {result['confidence']:.3f}")
    print(f"Message Type: {result['message_type']}")
    print(f"Reason: {result['reason']}")
    print("-" * 80)


def example_batch_prediction():
    """Example: Predict actions for multiple messages"""
    print("\n" + "="*80)
    print("EXAMPLE 2: BATCH PREDICTION")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    data_loader = DatasetLoader(dataset_path=str(project_root / "dataset"))

    # Load sample messages
    samples_path = project_root / "dataset" / "sample_messages.csv"
    messages_df = pd.read_csv(samples_path).head(10)  # First 10 messages
    print(f"✓ Loaded {len(messages_df)} messages")

    # Load trained pipeline
    print("\n📦 Loading trained pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)
    pipeline.load(model_dir=str(project_root / "models"))
    print("✓ Pipeline loaded successfully")

    # Predict
    print("\n🔮 Making predictions...")
    predictions_df = pipeline.predict_batch(messages_df, show_progress=True)

    # Display results
    print("\n📊 Prediction Results:")
    print("-" * 80)

    for idx, (_, msg_row) in enumerate(messages_df.iterrows()):
        pred = predictions_df.iloc[idx]
        msg_text = str(msg_row['message_text'])[:50]
        true_action = msg_row['action']
        pred_action = pred['action']
        confidence = pred['confidence']

        match = "✓" if true_action == pred_action else "✗"

        print(f"\n{match} Message {idx+1}:")
        print(f"  Text: {msg_text}...")
        print(f"  True: {true_action}, Predicted: {pred_action}")
        print(f"  Confidence: {confidence:.3f}")

    # Calculate accuracy
    accuracy = sum(
        predictions_df.iloc[i]['action'] == messages_df.iloc[i]['action']
        for i in range(len(messages_df))
    ) / len(messages_df)

    print("\n" + "="*80)
    print(f"Batch Accuracy: {accuracy*100:.1f}%")
    print("="*80)


def example_competition_submission():
    """Example: Generate competition submission file"""
    print("\n" + "="*80)
    print("EXAMPLE 3: COMPETITION SUBMISSION")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    data_loader = DatasetLoader(dataset_path=str(project_root / "dataset"))

    # Load test messages (use sample_messages for demo)
    test_path = project_root / "dataset" / "sample_messages.csv"
    test_df = pd.read_csv(test_path)
    print(f"✓ Loaded {len(test_df)} test messages")

    # Load trained pipeline
    print("\n📦 Loading trained pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)
    pipeline.load(model_dir=str(project_root / "models"))
    print("✓ Pipeline loaded successfully")

    # Generate predictions
    print("\n🔮 Generating predictions...")
    predictions_df = pipeline.predict_batch(test_df, show_progress=True)

    # Format for submission
    output_df = predictions_df[[
        'message_id', 'action', 'message_type',
        'reason', 'confidence', 'evidence_message_ids'
    ]]

    # Save
    output_path = project_root / "dataset" / "output.csv"
    output_df.to_csv(output_path, index=False)

    print(f"\n✅ Submission file created: {output_path}")
    print(f"   Total predictions: {len(output_df)}")

    # Show sample predictions
    print("\n📋 Sample predictions (first 5):")
    print("-" * 80)
    print(output_df.head(5).to_string(index=False))
    print("-" * 80)

    # Action distribution
    print("\n📊 Prediction Distribution:")
    print(output_df['action'].value_counts())


def example_feature_importance():
    """Example: Analyze feature importance"""
    print("\n" + "="*80)
    print("EXAMPLE 4: FEATURE IMPORTANCE ANALYSIS")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    data_loader = DatasetLoader(dataset_path=str(project_root / "dataset"))

    # Load trained pipeline
    print("📦 Loading trained pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)
    pipeline.load(model_dir=str(project_root / "models"))
    print("✓ Pipeline loaded successfully")

    # Get feature importance
    print("\n⭐ Feature Importance (Top 20):")
    print("-" * 80)

    importance_dict = pipeline.xgb_model.get_score(importance_type='gain')
    importance_sorted = sorted(
        importance_dict.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for rank, (feature, score) in enumerate(importance_sorted[:20], 1):
        print(f"{rank:2d}. {feature:40s}: {score:8.2f}")

    print("-" * 80)

    # Feature categories
    print("\n📊 Feature Categories:")
    text_features = sum(1 for f, _ in importance_sorted if any(
        keyword in f for keyword in ['has_', 'urgency', 'scam', 'time', 'forward']
    ))
    user_features = sum(1 for f, _ in importance_sorted if any(
        keyword in f for keyword in ['sender', 'user', 'group', 'business']
    ))

    print(f"  Text features in top 20: {text_features}")
    print(f"  User features in top 20: {user_features}")


def example_confidence_ranges():
    """Example: Verify confidence calibration"""
    print("\n" + "="*80)
    print("EXAMPLE 5: CONFIDENCE RANGE VERIFICATION")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    data_loader = DatasetLoader(dataset_path=str(project_root / "dataset"))

    # Load sample messages
    samples_path = project_root / "dataset" / "sample_messages.csv"
    messages_df = pd.read_csv(samples_path)

    # Load trained pipeline
    print("📦 Loading trained pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)
    pipeline.load(model_dir=str(project_root / "models"))
    print("✓ Pipeline loaded successfully")

    # Predict
    print("\n🔮 Making predictions...")
    predictions_df = pipeline.predict_batch(messages_df, show_progress=True)

    # Analyze confidence ranges
    print("\n📊 Confidence Ranges by Action:")
    print("-" * 80)

    target_ranges = {
        'notify': (0.85, 0.91),
        'mute': (0.81, 0.87),
        'digest': (0.78, 0.84)
    }

    for action in ['notify', 'mute', 'digest']:
        action_preds = predictions_df[predictions_df['action'] == action]

        if len(action_preds) > 0:
            confidences = action_preds['confidence']
            target_min, target_max = target_ranges[action]

            print(f"\n{action.upper()}:")
            print(f"  Count: {len(action_preds)}")
            print(f"  Target range: [{target_min:.2f}, {target_max:.2f}]")
            print(f"  Actual range: [{confidences.min():.3f}, {confidences.max():.3f}]")
            print(f"  Mean: {confidences.mean():.3f}")

            # Check if in range
            in_range = (
                (confidences >= target_min) &
                (confidences <= target_max)
            ).sum()
            print(f"  In range: {in_range}/{len(action_preds)} ({in_range/len(action_preds)*100:.1f}%)")

    print("-" * 80)


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("GPU-TRAINED PIPELINE: USAGE EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates how to use the trained pipeline.")
    print("Make sure you've run 'python train_pipeline.py' first!")
    print("="*80)

    try:
        # Check if models exist
        models_path = project_root / "models" / "xgboost_gpu.json"
        if not models_path.exists():
            print("\n❌ ERROR: Trained models not found!")
            print("\nPlease run training first:")
            print("  python code/train_pipeline.py")
            return

        # Run examples
        example_single_prediction()
        example_batch_prediction()
        example_competition_submission()
        example_feature_importance()
        example_confidence_ranges()

        print("\n" + "="*80)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
