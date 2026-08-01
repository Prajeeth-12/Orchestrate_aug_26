#!/usr/bin/env python3
"""
HackerRank Orchestrate - Message Notification Router
Main CLI entry point for evaluation

Usage:
    python code/main.py --input dataset/messages.csv --output output.csv
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'code'))

from utils.data_loader import DatasetLoader
from train_pipeline import MessageRoutingPipeline, ConfidenceCalibrator


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Message Notification Router - HackerRank Orchestrate'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input messages CSV path'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output predictions CSV path'
    )
    parser.add_argument(
        '--models',
        default='models',
        help='Models directory path (default: models)'
    )
    parser.add_argument(
        '--dataset',
        default=None,
        help='Dataset directory path (default: auto-detect from input)'
    )

    args = parser.parse_args()

    # Resolve paths
    input_path = Path(args.input)
    output_path = Path(args.output)
    models_dir = Path(args.models)

    # Auto-detect dataset directory
    if args.dataset:
        dataset_path = Path(args.dataset)
    else:
        dataset_path = input_path.parent

    print("="*70)
    print("MESSAGE NOTIFICATION ROUTER")
    print("="*70)

    # Step 1: Load input messages
    print(f"\n[1/5] Loading messages from: {input_path}")
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    messages = pd.read_csv(input_path)
    print(f"      Loaded {len(messages)} messages")

    # Step 2: Initialize data loader
    print(f"\n[2/5] Loading dataset from: {dataset_path}")
    data_loader = DatasetLoader(dataset_path=str(dataset_path))
    print(f"      Loaded {len(data_loader.message_history)} historical messages")

    # Step 3: Initialize pipeline
    print(f"\n[3/5] Initializing prediction pipeline...")
    pipeline = MessageRoutingPipeline(data_loader)

    # Step 4: Load trained models
    print(f"\n[4/5] Loading models from: {models_dir}")
    if not models_dir.exists():
        print(f"ERROR: Models directory not found: {models_dir}")
        print(f"       Please train models first: python code/train_pipeline.py")
        sys.exit(1)

    try:
        pipeline.load(model_dir=str(models_dir))
        print(f"      Models loaded successfully")
    except Exception as e:
        print(f"ERROR: Failed to load models: {e}")
        sys.exit(1)

    # Step 5: Generate predictions
    print(f"\n[5/5] Generating predictions...")
    predictions = pipeline.predict_batch(messages, show_progress=True)

    # Format output
    output_df = pd.DataFrame({
        'message_id': messages['message_id'],
        'action': predictions['action'],
        'message_type': predictions['message_type'],
        'reason': predictions['reason'],
        'confidence': predictions['confidence'].round(4),
        'evidence_message_ids': predictions['evidence_message_ids']
    })

    # Save predictions
    output_df.to_csv(output_path, index=False)
    print(f"\n[SUCCESS] Saved {len(output_df)} predictions to: {output_path}")

    # Summary statistics
    print("\n" + "="*70)
    print("PREDICTION SUMMARY")
    print("="*70)

    print("\nAction Distribution:")
    for action, count in output_df['action'].value_counts().sort_index().items():
        pct = 100 * count / len(output_df)
        print(f"  {action.upper():8s}: {count:3d} ({pct:5.1f}%)")

    print("\nMessage Type Distribution:")
    for msg_type, count in output_df['message_type'].value_counts().head(10).items():
        pct = 100 * count / len(output_df)
        print(f"  {msg_type:20s}: {count:3d} ({pct:5.1f}%)")

    print("\nConfidence Statistics:")
    for action in ['notify', 'digest', 'mute']:
        action_confs = output_df[output_df['action'] == action]['confidence']
        if len(action_confs) > 0:
            print(f"  {action.upper():8s}: mean={action_confs.mean():.3f}, "
                  f"min={action_confs.min():.3f}, max={action_confs.max():.3f}")

    print("\n" + "="*70)
    print("[SUCCESS] COMPLETE")
    print("="*70)
    print(f"\nOutput file ready for submission: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
