"""
AWS Bedrock Multimodal Processing for Moonshot AI
"""

import os
import requests
import base64
from typing import Dict, Optional
import io
import json
from dotenv import load_dotenv

load_dotenv()

# Secrets come from environment variables only (never hardcode in source).
BEDROCK_API_KEY = os.getenv("BEDROCK_API_KEY", "")
ENDPOINT = "https://bedrock-mantle.eu-north-1.api.aws/v1/chat/completions"


def _require_key() -> bool:
    if not BEDROCK_API_KEY:
        print("[WARN] BEDROCK_API_KEY not set; skipping API call")
        return False
    return True

def transcribe_voice_bedrock(audio_path: str) -> Optional[str]:
    """Model does not support audio input"""
    return None

def analyze_image_bedrock(image_path: str, prompt: str = None) -> Optional[Dict]:
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return None

    if not _require_key():
        return None

    if prompt is None:
        prompt = """Analyze this image for a WhatsApp notification router.

Determine:
1. Is it URGENT (deadline, time-sensitive, requires immediate action)?
2. Is it PROMOTIONAL (advertisement, sale, marketing)?
3. Is it INFORMATIONAL (news, updates, FYI)?

Extract any visible text, dates, times, or deadlines.

Respond in JSON format:
{
    "urgency": "high|medium|low",
    "category": "urgent|promotional|informational|unknown",
    "has_deadline": true/false,
    "extracted_text": "any visible text",
    "reason": "brief explanation"
}"""

    try:
        from PIL import Image
        
        img = Image.open(image_path)
        
        # Resize to max 800px on longest side
        max_size = 800
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        buffer = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format='JPEG', quality=85)
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {BEDROCK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": "moonshotai.kimi-k2.5",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ]
        }
        
        response = requests.post(ENDPOINT, headers=headers, json=body, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                parsed = json.loads(content)
                return parsed
            except:
                return {
                    'urgency': 'unknown',
                    'category': 'unknown',
                    'extracted_text': content,
                    'reason': 'Raw response from vision model'
                }
        else:
            print(f"Image analysis failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error analyzing {image_path}: {e}")
        return None
