"""
Process all multimodal content (voice + images) using Gemini API
Run this script tomorrow when quota resets
"""

import pandas as pd
import json
import os
from pathlib import Path
from bedrock_multimodal import transcribe_voice_bedrock as transcribe_voice
from bedrock_multimodal import analyze_image_bedrock as analyze_image
import time


def process_voice_notes():
    """Transcribe all 8 voice notes"""
    print("="*60)
    print("PROCESSING VOICE NOTES")
    print("="*60)
    print()

    messages = pd.read_csv('dataset/messages.csv')
    voice_msgs = messages[messages['media_type'] == 'voice']
    voice_notes = pd.read_csv('dataset/voice_notes.csv').set_index('voice_note_id')

    print(f"Found {len(voice_msgs)} voice messages to transcribe")
    print()

    results = {}
    success_count = 0

    for idx, row in voice_msgs.iterrows():
        msg_id = row['message_id']
        media_id = row['media_id']
        if media_id in voice_notes.index:
            media_file = voice_notes.loc[media_id, 'file_path']
            audio_path = f"dataset/{media_file}"
        else:
            audio_path = ""

        print(f"[{success_count+1}/{len(voice_msgs)}] {msg_id}: {media_id}")

        if not os.path.exists(audio_path):
            print(f"   [SKIP] File not found: {audio_path}")
            results[msg_id] = None
            continue

        text = transcribe_voice(audio_path)

        if text:
            print(f"   [OK] Transcribed: '{text[:60]}...'")
            results[msg_id] = text
            success_count += 1
        else:
            print(f"   [FAIL] Transcription failed")
            results[msg_id] = None

        # Bedrock API is quite fast, 1s delay is enough
        time.sleep(1)

    print()
    print(f"Completed: {success_count}/{len(voice_msgs)} successful")
    print()

    # Save results
    output_path = 'dataset/voice_transcriptions.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_path}")
    return results


def process_images():
    """Analyze all 15 images"""
    print()
    print("="*60)
    print("PROCESSING IMAGES")
    print("="*60)
    print()

    messages = pd.read_csv('dataset/messages.csv')
    image_msgs = messages[messages['media_type'] == 'image']
    images = pd.read_csv('dataset/images.csv').set_index('image_id')

    print(f"Found {len(image_msgs)} images to analyze")
    print()

    results = {}
    success_count = 0

    for idx, row in image_msgs.iterrows():
        msg_id = row['message_id']
        media_id = row['media_id']
        if media_id in images.index:
            media_file = images.loc[media_id, 'file_path']
            image_path = f"dataset/{media_file}"
        else:
            image_path = ""

        print(f"[{success_count+1}/{len(image_msgs)}] {msg_id}: {media_id}")

        if not os.path.exists(image_path):
            print(f"   [SKIP] File not found: {image_path}")
            results[msg_id] = None
            continue

        analysis = analyze_image(image_path)

        if analysis:
            print(f"   [OK] Urgency: {analysis.get('urgency', 'unknown')}, Category: {analysis.get('category', 'unknown')}")
            if analysis.get('extracted_text'):
                print(f"       Text: '{analysis['extracted_text'][:50]}...'")
            results[msg_id] = analysis
            success_count += 1
        else:
            print(f"   [FAIL] Analysis failed")
            results[msg_id] = None

        # Bedrock API is fast enough, 1s delay
        time.sleep(1)

    print()
    print(f"Completed: {success_count}/{len(image_msgs)} successful")
    print()

    # Save results
    output_path = 'dataset/image_analyses.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_path}")
    return results


def main():
    """Process all multimodal content"""
    print()
    print("MULTIMODAL PROCESSING PIPELINE")
    print("Gemini 2.0 Flash - Voice Transcription + Image Analysis")
    print()

    import sys

    voice_only = '--voice-only' in sys.argv
    images_only = '--images-only' in sys.argv

    if not voice_only and not images_only:
        # Process both
        voice_results = process_voice_notes()
        image_results = process_images()
    elif voice_only:
        voice_results = process_voice_notes()
    elif images_only:
        image_results = process_images()

    print()
    print("="*60)
    print("MULTIMODAL PROCESSING COMPLETE")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Run: python code/main.py --input dataset/messages.csv --output output.csv")
    print("2. Predictions will automatically use voice_transcriptions.json and image_analyses.json")
    print("3. Validate: python code/validate_output.py")
    print()


if __name__ == "__main__":
    main()
