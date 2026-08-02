#!/usr/bin/env python3
"""
HackerRank Orchestrate - Message Notification Router
Main CLI entry point for evaluation

Usage:
    python code/main.py --input dataset/messages.csv --output output.csv
"""

import sys
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'code'))

from utils.data_loader import DatasetLoader
from train_pipeline import MessageRoutingPipeline, ConfidenceCalibrator


def load_multimodal_data(dataset_path: Path):
    """Load voice transcriptions and image analyses if available."""
    voice_data = {}
    image_data = {}

    voice_path = dataset_path / 'voice_transcriptions.json'
    if voice_path.exists():
        with open(voice_path, 'r', encoding='utf-8') as f:
            voice_data = json.load(f)
        print(f"      Loaded {sum(1 for v in voice_data.values() if v)} voice transcriptions")

    image_path = dataset_path / 'image_analyses.json'
    if image_path.exists():
        with open(image_path, 'r', encoding='utf-8') as f:
            image_data = json.load(f)
        print(f"      Loaded {sum(1 for v in image_data.values() if v is not None)} image analyses")

    return voice_data, image_data


def enrich_messages_with_multimodal(messages: pd.DataFrame, voice_data: dict, image_data: dict) -> pd.DataFrame:
    """Inject voice transcriptions and image features into messages before prediction."""
    messages = messages.copy()

    voice_injected = 0
    image_enriched = 0

    for idx, row in messages.iterrows():
        msg_id = row['message_id']

        # Voice: inject transcript as message_text if text is empty
        if row.get('media_type') == 'voice' and msg_id in voice_data:
            transcript = voice_data[msg_id]
            if transcript and (pd.isna(row['message_text']) or str(row['message_text']).strip() == ''):
                messages.at[idx, 'message_text'] = transcript
                voice_injected += 1

        # Image: add analysis metadata as auxiliary columns
        if row.get('media_type') == 'image' and msg_id in image_data:
            analysis = image_data[msg_id]
            if analysis:
                messages.at[idx, 'image_urgency'] = analysis.get('urgency', 'low')
                messages.at[idx, 'image_category'] = analysis.get('category', 'unknown')
                messages.at[idx, 'image_extracted_text'] = analysis.get('extracted_text', '')
                messages.at[idx, 'image_has_deadline'] = analysis.get('has_deadline', False)
                image_enriched += 1

    print(f"      Voice transcripts injected: {voice_injected}")
    print(f"      Image analyses enriched: {image_enriched}")
    return messages


def enforce_consistency(output_df: pd.DataFrame, messages: pd.DataFrame) -> pd.DataFrame:
    """
    Consistency pass: identical messages (same user, sender, conversation, media,
    forward count, normalized text) must route identically. This avoids scoring
    losses when duplicate content is labelled consistently.
    """
    df = output_df.copy()
    m = messages.copy()
    m['_key'] = (
        m['user_id'].astype(str) + '|' +
        m['sender_user_id'].astype(str) + '|' +
        m['conversation_type'].astype(str) + '|' +
        m['media_type'].astype(str) + '|' +
        m['forwarded_count'].astype(str) + '|' +
        m['message_text'].fillna('').astype(str).str.lower().str.strip()
    )
    df['_key'] = m['_key'].values

    for key, group in df.groupby('_key'):
        if len(group) <= 1:
            continue
        # Representative row = highest confidence
        rep = group.loc[group['confidence'].idxmax()]
        df.loc[group.index, 'action'] = rep['action']
        df.loc[group.index, 'message_type'] = rep['message_type']
        df.loc[group.index, 'confidence'] = rep['confidence']
        df.loc[group.index, 'reason'] = rep['reason']
        df.loc[group.index, 'evidence_message_ids'] = rep['evidence_message_ids']

    return df.drop(columns=['_key'])


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
    print(f"\n[1/6] Loading messages from: {input_path}")
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    messages = pd.read_csv(input_path)
    print(f"      Loaded {len(messages)} messages")

    # Step 2: Load multimodal data
    print(f"\n[2/6] Loading multimodal data from: {dataset_path}")
    voice_data, image_data = load_multimodal_data(dataset_path)

    # Step 3: Enrich messages with multimodal content
    print(f"\n[3/6] Enriching messages with multimodal content...")
    messages = enrich_messages_with_multimodal(messages, voice_data, image_data)

    # Step 4: Initialize data loader and pipeline
    print(f"\n[4/6] Loading dataset and initializing pipeline...")
    data_loader = DatasetLoader(dataset_path=str(dataset_path))
    print(f"      Loaded {len(data_loader.message_history)} historical messages")
    pipeline = MessageRoutingPipeline(data_loader)

    # Step 5: Load trained models
    print(f"\n[5/6] Loading models from: {models_dir}")
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

    # Step 6: Generate predictions with AgentOrchestrator
    print(f"\n[6/6] Generating predictions with AgentOrchestrator...")
    from agent_orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(pipeline)

    results = []
    from tqdm import tqdm
    for _, row in tqdm(messages.iterrows(), total=len(messages)):
        results.append(orchestrator.process_message(row))

    predictions = pd.DataFrame(results)

    # Print verifier trace summary
    print(f"\n{'='*70}")
    print("VERIFIER TRACE")
    print("="*70)
    print(orchestrator.get_trace_summary())

    # Format output
    output_df = pd.DataFrame({
        'message_id': messages['message_id'],
        'action': predictions['action'],
        'message_type': predictions['message_type'],
        'reason': predictions['reason'],
        'confidence': predictions['confidence'].round(4),
        'evidence_message_ids': predictions['evidence_message_ids']
    })

    # Consistency pass: identical messages must route identically
    output_df = enforce_consistency(output_df, messages)

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
