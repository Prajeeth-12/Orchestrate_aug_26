"""
Google Gemini AI Studio Multimodal Processing
Transcribe voice notes and analyze images using Gemini REST API
"""

import os
import requests
import base64
from pathlib import Path
from typing import Dict, Optional
import json
import time
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def transcribe_voice_gemini(audio_path: str) -> Optional[str]:
    """
    Transcribe voice note using Gemini

    Args:
        audio_path: Path to audio file

    Returns:
        Transcribed text or None on error
    """
    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")
        return None

    try:
        # Read and encode audio file
        with open(audio_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')

        # Determine MIME type
        ext = Path(audio_path).suffix.lower()
        mime_type = {
            '.mp3': 'audio/mp3',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg'
        }.get(ext, 'audio/mp3')

        url = f"{BASE_URL}/models/gemini-2.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Transcribe this WhatsApp voice message accurately. Return ONLY the spoken text, nothing else."
                        },
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": audio_data
                            }
                        }
                    ]
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
        else:
            print(f"Transcription failed: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Error transcribing {audio_path}: {e}")
        return None


def analyze_image_gemini(image_path: str) -> Optional[Dict]:
    """
    Analyze image using Gemini Vision

    Args:
        image_path: Path to image file

    Returns:
        Dict with analysis results or None on error
    """
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return None

    try:
        # Read and encode image file
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Determine MIME type
        ext = Path(image_path).suffix.lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')

        url = f"{BASE_URL}/models/gemini-2.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        }

        prompt = """Analyze this WhatsApp message image for a notification router.

Extract:
1. All visible text (OCR)
2. Urgency level: HIGH (immediate action needed), MEDIUM (soon), LOW (FYI)
3. Category: urgent, promotional, informational, event, deadline, greeting
4. Any deadlines, dates, or time-sensitive information

Respond in JSON format:
{
    "urgency": "high|medium|low",
    "category": "urgent|promotional|informational|event|deadline|greeting",
    "has_deadline": true/false,
    "deadline_text": "extracted deadline if any",
    "extracted_text": "all visible text",
    "reason": "why this urgency/category"
}"""

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        },
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_data
                            }
                        }
                    ]
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']

            # Parse JSON response
            text = text.strip()

            # Remove markdown code blocks if present
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()

            parsed = json.loads(text)
            return parsed

        else:
            print(f"Image analysis failed: {response.status_code} - {response.text}")
            return None

    except json.JSONDecodeError as e:
        print(f"JSON parse error for {image_path}: {e}")
        # Return raw response as extracted_text
        return {
            'urgency': 'unknown',
            'category': 'unknown',
            'extracted_text': text if 'text' in locals() else '',
            'reason': 'Failed to parse JSON response'
        }
    except Exception as e:
        print(f"Error analyzing {image_path}: {e}")
        return None


def test_gemini_apis():
    """Test both Gemini APIs"""
    print("Testing Gemini AI Studio APIs...")
    print()

    # Test voice transcription
    voice_file = "dataset/media/audio/vn_001.mp3"
    if os.path.exists(voice_file):
        print(f"[1/2] Testing voice transcription on {voice_file}...")
        text = transcribe_voice_gemini(voice_file)
        if text:
            print(f"[OK] Transcribed: '{text[:100]}...'")
        else:
            print("[FAIL] Failed")
    else:
        print(f"[SKIP] Voice file not found: {voice_file}")

    print()

    # Test image analysis
    image_file = "dataset/media/images/img_001.jpg"
    if os.path.exists(image_file):
        print(f"[2/2] Testing image analysis on {image_file}...")
        result = analyze_image_gemini(image_file)
        if result:
            print("[OK] Success!")
            print(f"   Urgency: {result.get('urgency', 'unknown')}")
            print(f"   Category: {result.get('category', 'unknown')}")
            print(f"   Text: {result.get('extracted_text', 'none')[:100]}...")
        else:
            print("[FAIL] Failed")
    else:
        print(f"[SKIP] Image file not found: {image_file}")

    print()
    print("API test complete!")


if __name__ == "__main__":
    test_gemini_apis()
