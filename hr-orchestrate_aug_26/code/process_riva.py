#!/usr/bin/env python3
"""
Regenerate `dataset/voice_transcriptions.json` from `dataset/media/audio/*.wav`
using an NVIDIA Riva ASR endpoint.

This is an OFFLINE reproducibility tool - it is NOT required to run the
submission (`code/main.py` reads the already-committed
`dataset/voice_transcriptions.json`). It exists so the transcript artifact can
be regenerated if the audio files change.

Prerequisites:
    pip install riva-client soundfile numpy pandas

Environment variables (all optional except RIVA_ENDPOINT):
    RIVA_ENDPOINT       Riva ASR service host:port, e.g. 127.0.0.1:50051
    RIVA_API_KEY        Optional bearer token for authed endpoints (never hardcode)
    RIVA_USE_SSL        "true"/"1" to use TLS (default: false)
    RIVA_MODEL_URI      Optional model URI override
    RIVA_ASR_LANGUAGE_CODE  Default "en-US"

Usage:
    python process_riva.py \
        --messages dataset/messages.csv \
        --media-dir dataset/media/audio \
        --output dataset/voice_transcriptions.json
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_message_id_map(messages_csv: Path):
    """Map media_id -> message_id for all voice messages."""
    import pandas as pd

    messages = pd.read_csv(messages_csv)
    voice = messages[messages['media_type'] == 'voice']
    mapping = {}
    for _, row in voice.iterrows():
        media_id = str(row.get('media_id') or '').strip()
        if media_id:
            mapping[media_id] = row['message_id']
    return mapping


def resolve_audio_path(media_dir: Path, media_id: str):
    """Prefer the 16k PCM wav; fall back to mp3 and transcode via ffmpeg."""
    wav = media_dir / f"{media_id}.wav"
    if wav.exists():
        return wav, 'wav'
    mp3 = media_dir / f"{media_id}.mp3"
    if mp3.exists():
        return mp3, 'mp3'
    return None, None


def load_pcm16(path: Path, kind: str):
    """Return (pcm_int16_bytes, sample_rate) for Riva offline_recognize."""
    import soundfile as sf

    if kind == 'wav':
        data, sr = sf.read(path, dtype='int16')
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data.astype('<i2').tobytes(), sr

    # mp3 -> wav via ffmpeg, then read
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(path), '-ar', '16000', '-ac', '1',
             '-c:a', 'pcm_s16le', tmp_path],
            check=True, capture_output=True,
        )
        data, sr = sf.read(tmp_path, dtype='int16')
        return data.astype('<i2').tobytes(), sr
    finally:
        os.unlink(tmp_path)


def transcribe(endpoint: str, api_key: str, use_ssl: bool, model_uri: str,
               language_code: str, pcm: bytes, sample_rate: int):
    import riva.client as _rc

    auth_meta = [("authorization", f"Bearer {api_key}")] if api_key else None
    auth = _rc.Auth(
        uri=endpoint, use_ssl=use_ssl,
        metadata_credentials=auth_meta,
    )
    service = _rc.ASRService(auth)

    cfg = _rc.RecognitionConfig(
        encoding=_rc.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=sample_rate,
        language_code=language_code,
        max_alternatives=1,
        enable_word_time_offsets=False,
        model_uri=model_uri or None,
    )
    stream_cfg = _rc.StreamingRecognitionConfig(config=cfg, interim_results=False)
    results = service.offline_recognize(pcm, stream_cfg)
    if results and results.results:
        return results.results[0].alternatives[0].transcript
    return ""


def main():
    parser = argparse.ArgumentParser(description='Transcribe voice notes via Riva ASR')
    parser.add_argument('--messages', required=True, help='dataset/messages.csv')
    parser.add_argument('--media-dir', required=True, help='dataset/media/audio')
    parser.add_argument('--output', required=True, help='output voice_transcriptions.json')
    args = parser.parse_args()

    endpoint = os.getenv('RIVA_ENDPOINT', '')
    api_key = os.getenv('RIVA_API_KEY', '')
    use_ssl = os.getenv('RIVA_USE_SSL', '').lower() in ('true', '1', 'yes')
    model_uri = os.getenv('RIVA_MODEL_URI', '')
    language_code = os.getenv('RIVA_ASR_LANGUAGE_CODE', 'en-US')

    if not endpoint:
        sys.exit("ERROR: RIVA_ENDPOINT env var is required "
                 "(e.g. RIVA_ENDPOINT=127.0.0.1:50051).")

    try:
        import riva.client  # noqa: F401
    except ImportError:
        sys.exit("ERROR: riva-client not installed. Run: pip install riva-client soundfile")

    messages_csv = Path(args.messages)
    media_dir = Path(args.media_dir)
    id_map = load_message_id_map(messages_csv)
    if not id_map:
        sys.exit("ERROR: no voice messages with media_id found in messages.csv")

    print(f"Transcribing {len(id_map)} voice notes via Riva at {endpoint} (ssl={use_ssl})")
    transcriptions = {}
    for media_id, message_id in sorted(id_map.items()):
        audio_path, kind = resolve_audio_path(media_dir, media_id)
        if audio_path is None:
            print(f"  [skip] {media_id}: no audio file found")
            continue
        try:
            pcm, sr = load_pcm16(audio_path, kind)
        except Exception as e:
            print(f"  [fail] {media_id}: could not read audio: {e}")
            continue
        text = transcribe(endpoint, api_key, use_ssl, model_uri, language_code, pcm, sr)
        transcriptions[message_id] = text
        preview = text[:60].replace('\n', ' ')
        print(f"  {media_id} -> {message_id}: {preview or '(empty)'}")

    out_path = Path(args.output)
    out_path.write_text(json.dumps(transcriptions, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nWrote {sum(1 for v in transcriptions.values() if v)} non-empty "
          f"transcripts to {out_path}")


if __name__ == '__main__':
    main()
