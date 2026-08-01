"""
Generate Final Predictions for Test Messages

This script:
1. Loads trained models
2. Reads 110 test messages from dataset/messages.csv
3. Applies full pipeline (rules + features + ML + calibration)
4. Generates output.csv for submission

Expected Output Format:
message_id,action,message_type,reason,confidence,evidence_message_ids
"""

import sys
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'code'))

from train_pipeline import MessageRoutingPipeline, ConfidenceCalibrator
from utils.data_loader import DatasetLoader


def generate_predictions():
    """
    Generate predictions for all test messages
    """
    print("="*70)
    print("[PREDICTION] GENERATING FINAL PREDICTIONS FOR SUBMISSION")
    print("="*70)

    # Paths
    dataset_path = project_root / "dataset"
    output_path = project_root / "output.csv"

    # Load test messages
    print(f"\n[LOAD] Loading test messages from: {dataset_path}")
    messages = pd.read_csv(dataset_path / "messages.csv")
    print(f"   [OK] Loaded {len(messages)} test messages")

    # Initialize data loader
    print(f"\n[INIT] Initializing data loader...")
    data_loader = DatasetLoader(dataset_path=str(dataset_path))

    # Initialize pipeline
    print(f"\n[INIT] Initializing prediction pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)

    # Load trained models
    try:
        pipeline.load(model_dir=str(project_root / "models"))
    except FileNotFoundError as e:
        print(f"\n[ERROR] Error: {e}")
        print("\n[WARNING] Models not found. Please train first:")
        print("   python code/train_pipeline.py")
        return

    # Generate predictions
    print(f"\n[PREDICT] Generating predictions...")
    predictions = pipeline.predict_batch(messages, show_progress=True)

    # Prepare output DataFrame
    output_df = pd.DataFrame({
        'message_id': messages['message_id'],
        'action': predictions['action'],
        'message_type': predictions['message_type'],
        'reason': predictions['reason'],
        'confidence': predictions['confidence'].round(4),
        'evidence_message_ids': predictions['evidence_message_ids']
    })

    # Save to CSV
    output_df.to_csv(output_path, index=False)
    print(f"\n[SAVE] Saved predictions to: {output_path}")

    # Summary statistics
    print("\n" + "="*70)
    print("[STATS] PREDICTION SUMMARY")
    print("="*70)

    print(f"\nTotal Messages: {len(output_df)}")

    print("\nAction Distribution:")
    for action, count in output_df['action'].value_counts().items():
        pct = 100 * count / len(output_df)
        print(f"   {action.upper():8s}: {count:3d} ({pct:5.1f}%)")

    print("\nMessage Type Distribution:")
    for msg_type, count in output_df['message_type'].value_counts().items():
        pct = 100 * count / len(output_df)
        print(f"   {msg_type:20s}: {count:3d} ({pct:5.1f}%)")

    print("\nConfidence Statistics:")
    for action in ['notify', 'digest', 'mute']:
        action_confs = output_df[output_df['action'] == action]['confidence']
        if len(action_confs) > 0:
            print(f"   {action.upper():8s}: "
                  f"mean={action_confs.mean():.3f}, "
                  f"std={action_confs.std():.3f}, "
                  f"min={action_confs.min():.3f}, "
                  f"max={action_confs.max():.3f}")

    print("\n" + "="*70)
    print("[OK] PREDICTIONS COMPLETE!")
    print("="*70)
    print(f"\n[READY] Ready for submission: {output_path}")

    # Preview first 10 predictions
    print("\n[PREVIEW] Preview (first 10 rows):")
    print(output_df.head(10).to_string(index=False))


if __name__ == "__main__":
    generate_predictions()
