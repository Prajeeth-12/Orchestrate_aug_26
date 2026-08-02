#!/usr/bin/env python3
"""
Regenerate `dataset/image_analyses.json` from `dataset/media/images/*.jpg`
using an OpenAI-compatible vision endpoint (e.g. NVIDIA NIM / Bedrock / any
OpenAI-compatible VLM).

This is an OFFLINE reproducibility tool - it is NOT required to run the
submission (`code/main.py` reads the already-committed
`dataset/image_analyses.json`). It exists so the image artifact can be
regenerated if the images change.

Environment variables:
    NVIDIA_API_URL   Vision chat/completions URL
                     (default: https://integrate.api.nvidia.com/v1/chat/completions)
    NVIDIA_API_KEY   API key for the hosted endpoint (required unless you point
                     NVIDIA_API_URL at a local server)
    NVIDIA_MODEL     Model name (default: meta/llama-3.2-90b-vision-instruct)

Usage:
    python nvidia_multimodal.py \
        --messages dataset/messages.csv \
        --media-dir dataset/media/images \
        --output dataset/image_analyses.json
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

import requests

SYSTEM_PROMPT = (
    "You are the image-analysis module of a WhatsApp message notification router. "
    "Analyze the image and return STRICT JSON (no markdown) with exactly these keys:\n"
    "  \"urgency\": one of \"low\", \"medium\", \"high\" - how time-sensitive the content is\n"
    "  \"category\": one of \"promotional\", \"informational\", \"urgent\", \"personal\", \"unknown\"\n"
    "  \"has_deadline\": boolean - true if a date/time/expiry is visible\n"
    "  \"extracted_text\": all visible text verbatim, or \"\" if none\n"
    "  \"reason\": one sentence explaining the decision"
)


def load_message_id_map(messages_csv: Path):
    import pandas as pd

    messages = pd.read_csv(messages_csv)
    image = messages[messages['media_type'] == 'image']
    mapping = {}
    for _, row in image.iterrows():
        media_id = str(row.get('media_id') or '').strip()
        if media_id:
            mapping[media_id] = row['message_id']
    return mapping


def parse_model_json(content: str):
    """Extract the JSON object from a model response (tolerating code fences)."""
    content = content.strip()
    if content.startswith('```'):
        content = re.sub(r'^```[a-zA-Z]*\s*', '', content)
        content = re.sub(r'```$', '', content)
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in model response: {content[:200]}")
    parsed = json.loads(match.group(0))
    return {
        "urgency": str(parsed.get("urgency", "low")).lower(),
        "category": str(parsed.get("category", "unknown")).lower(),
        "has_deadline": bool(parsed.get("has_deadline", False)),
        "extracted_text": str(parsed.get("extracted_text", "")),
        "reason": str(parsed.get("reason", "")),
    }


def analyze_image(url: str, api_key: str, model: str, image_path: Path) -> dict:
    mime = "image/jpeg"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this WhatsApp image."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
        "temperature": 0.0,
        "max_tokens": 512,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return parse_model_json(content)


def main():
    parser = argparse.ArgumentParser(description='Analyze images via a vision endpoint')
    parser.add_argument('--messages', required=True, help='dataset/messages.csv')
    parser.add_argument('--media-dir', required=True, help='dataset/media/images')
    parser.add_argument('--output', required=True, help='output image_analyses.json')
    args = parser.parse_args()

    url = os.getenv('NVIDIA_API_URL',
                    'https://integrate.api.nvidia.com/v1/chat/completions')
    api_key = os.getenv('NVIDIA_API_KEY', '')
    model = os.getenv('NVIDIA_MODEL', 'meta/llama-3.2-90b-vision-instruct')

    if not api_key:
        sys.exit("ERROR: NVIDIA_API_KEY env var is required (or point NVIDIA_API_URL "
                 "at a local server). Never hardcode keys.")

    messages_csv = Path(args.messages)
    media_dir = Path(args.media_dir)
    id_map = load_message_id_map(messages_csv)
    if not id_map:
        sys.exit("ERROR: no image messages with media_id found in messages.csv")

    print(f"Analyzing {len(id_map)} images via {model} (url={url})")
    analyses = {}
    for media_id, message_id in sorted(id_map.items()):
        # try common extensions
        image_path = None
        for ext in ('.jpg', '.jpeg', '.png', '.webp'):
            candidate = media_dir / f"{media_id}{ext}"
            if candidate.exists():
                image_path = candidate
                break
        if image_path is None:
            print(f"  [skip] {media_id}: no image file found")
            continue
        try:
            result = analyze_image(url, api_key, model, image_path)
        except Exception as e:
            print(f"  [fail] {media_id}: {e}")
            continue
        analyses[message_id] = result
        print(f"  {media_id} -> {message_id}: {result['urgency']}/"
              f"{result['category']}/deadline={result['has_deadline']}")

    out_path = Path(args.output)
    out_path.write_text(json.dumps(analyses, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nWrote {len(analyses)} analyses to {out_path}")


if __name__ == '__main__':
    main()
