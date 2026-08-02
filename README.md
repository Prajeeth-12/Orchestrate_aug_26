# HackerRank Orchestrate - Message Notification Router

**Competition:** August 2026
**Task:** Route incoming WhatsApp messages to `notify` / `digest` / `mute` using
personalized, multimodal reasoning (text + image + voice).

---

## What This System Does

For every incoming message in `dataset/messages.csv` the pipeline decides:

- `notify` - interrupt the user now
- `digest` - useful but can wait
- `mute` - low-value, repetitive, unwanted, suspicious, or unsafe

It uses the full provided context: user behavior, group/business relationships,
historical messages and reaction events, image analyses, and voice transcripts.

## Architecture

A LangGraph-orchestrated, ML-first hybrid pipeline (`code/agent_orchestrator.py`):

1. **Input guardrail** - blocks prompt-injection / router-manipulation attempts.
2. **Rule-based classifier** - deterministic rules for forwards, scams, urgent
   time-sensitive messages, and urgency negation (~40% coverage).
3. **XGBoost classifier** - trained on the provided labeled samples, with 59
   text + user-history + multimodal features.
4. **Confidence-based router** - low-confidence predictions pass to a reviewer
   node (deterministic pass-through; a live LLM can be swapped in without
   changing the graph).
5. **Pydantic output validator** - enforces the exact submission schema.

Multimodal content is processed offline into `dataset/voice_transcriptions.json`
and `dataset/image_analyses.json`, then injected at inference time.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (or: source venv/bin/activate)
pip install -r code/requirements.txt

# Optional API keys (only needed to regenerate multimodal analyses):
copy .env.example .env        # then fill in your keys
```

## Run (generate predictions)

```bash
python code/main.py --input dataset/messages.csv --output output.csv --models models
```

Output: `output.csv` with columns
`message_id,action,message_type,reason,confidence,evidence_message_ids`
- one row per `message_id` in `messages.csv`.

## Regenerate multimodal analyses (optional)

- Voice: transcribe `dataset/media/audio/*` (e.g. Riva ASR / Whisper) into
  `dataset/voice_transcriptions.json` keyed by message_id.
- Images: analyze `dataset/media/images/*` into `dataset/image_analyses.json`
  keyed by message_id with `urgency`, `category`, `extracted_text`, `has_deadline`.

## Project layout

```
code/
  main.py                  CLI entry point
  agent_orchestrator.py    LangGraph orchestration + guardrails
  train_pipeline.py        rules, XGBoost training, type inference, confidence
  rule_based_classifier.py deterministic rules
  features/                text + user-history + multimodal feature extraction
  utils/data_loader.py     dataset loading
  requirements.txt         dependencies
models/                    trained XGBoost model + metadata
dataset/                   competition data + multimodal artifacts
```

## Notes

- Inference is deterministic (no live LLM calls in the hot path).
- Secrets are read from environment variables only - never commit `.env` or
  API keys to source.
