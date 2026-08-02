"""
Multimodal Feature Extraction for Message Notification Router

Handles:
- Image analysis (using Claude 3.5 Sonnet vision)
- Voice note transcription (using Whisper ASR)
- Content extraction for routing decisions
"""

from pathlib import Path
from typing import Dict, Any, Optional
import os


class MultimodalFeatureExtractor:
    """
    Extract features from images and voice notes

    Images: Analyzed with Claude 3.5 Sonnet vision
    Voice: Transcribed with Whisper, then processed as text
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize multimodal feature extractor

        Args:
            anthropic_api_key: API key for Claude (optional, reads from env)
        """
        self.anthropic_api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        self._claude_client = None
        self._whisper_model = None

    @property
    def claude_client(self):
        """Lazy load Claude client"""
        if self._claude_client is None:
            try:
                import anthropic
                self._claude_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            except ImportError:
                raise ImportError("anthropic package required. Install: pip install anthropic")
        return self._claude_client

    @property
    def whisper_model(self):
        """Lazy load Whisper model"""
        if self._whisper_model is None:
            try:
                import whisper
                self._whisper_model = whisper.load_model("base")
            except ImportError:
                raise ImportError("whisper package required. Install: pip install openai-whisper")
        return self._whisper_model

    def extract_image_features(self, image_path: Path) -> Dict[str, Any]:
        """
        Analyze image with Claude 3.5 Sonnet vision

        Args:
            image_path: Path to image file

        Returns:
            Dict with:
              - image_type: promotion/event_poster/screenshot/personal_photo/scam
              - image_urgency: high/medium/low
              - image_content: text description
              - image_suspicious: bool
              - image_has_text: bool
              - image_text_content: extracted text if any
        """
        if not self.anthropic_api_key:
            return {
                'image_type': 'unknown',
                'image_urgency': 'low',
                'image_content': 'API key not configured',
                'image_suspicious': False,
                'image_has_text': False,
                'image_text_content': ''
            }

        # Read and encode image
        import base64
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        # Get image type for content_type
        suffix = image_path.suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(suffix, 'image/jpeg')

        # Analyze with Claude Vision
        prompt = """Analyze this WhatsApp image for notification routing.

Extract:
1. Type: promotion/event_poster/screenshot/personal_photo/scam
2. Urgency: high (same-day event)/medium (this week)/low
3. Content: brief description (2-3 sentences)
4. Suspicious: yes/no (fake QR, phishing, scam patterns)
5. Has text: yes/no
6. Text content: any visible text

Output JSON only:
{
  "type": "...",
  "urgency": "...",
  "content": "...",
  "suspicious": "yes/no",
  "has_text": "yes/no",
  "text_content": "..."
}"""

        try:
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }]
            )

            # Parse JSON from response
            import json
            import re

            content = response.content[0].text

            # Try to extract JSON
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = json.loads(content)

            return {
                'image_type': analysis.get('type', 'unknown'),
                'image_urgency': analysis.get('urgency', 'low'),
                'image_content': analysis.get('content', ''),
                'image_suspicious': analysis.get('suspicious', 'no') == 'yes',
                'image_has_text': analysis.get('has_text', 'no') == 'yes',
                'image_text_content': analysis.get('text_content', '')
            }

        except Exception as e:
            print(f"[!] Image analysis failed: {e}")
            return {
                'image_type': 'unknown',
                'image_urgency': 'low',
                'image_content': f'Analysis failed: {str(e)}',
                'image_suspicious': False,
                'image_has_text': False,
                'image_text_content': ''
            }

    def extract_voice_features(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe voice note with Whisper

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with:
              - voice_duration: duration in seconds
              - voice_language: detected language
              - voice_text: transcription
              - voice_confidence: transcription confidence
        """
        try:
            result = self.whisper_model.transcribe(str(audio_path))

            return {
                'voice_duration': result.get('duration', 0),
                'voice_language': result.get('language', 'unknown'),
                'voice_text': result.get('text', ''),
                'voice_confidence': 1.0  # Whisper doesn't return confidence
            }

        except Exception as e:
            print(f"[!] Voice transcription failed: {e}")
            return {
                'voice_duration': 0,
                'voice_language': 'unknown',
                'voice_text': f'Transcription failed: {str(e)}',
                'voice_confidence': 0.0
            }

    def extract(self,
                media_type: Optional[str],
                media_path: Optional[Path]) -> Dict[str, Any]:
        """
        Extract features from media file

        Args:
            media_type: 'image' or 'voice' or None
            media_path: Path to media file or None

        Returns:
            Feature dictionary (empty if no media)
        """
        if not media_type or not media_path:
            return {}

        if media_type == 'image':
            return self.extract_image_features(media_path)
        elif media_type == 'voice':
            return self.extract_voice_features(media_path)
        else:
            return {}


# Quick test
if __name__ == "__main__":
    print("Multimodal Feature Extractor")
    print("=" * 50)
    print("\nThis module handles:")
    print("  - Image analysis (Claude 3.5 Sonnet)")
    print("  - Voice transcription (Whisper)")
    print("\nRequires:")
    print("  - ANTHROPIC_API_KEY environment variable")
    print("  - pip install anthropic openai-whisper")
    print("\n✓ Module loaded successfully")
