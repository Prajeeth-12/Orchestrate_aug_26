# Message Notification Router - Implementation

**Competition:** HackerRank Orchestrate August 2026

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (or: source venv/bin/activate)
pip install -r requirements.txt

# Optional: only needed to regenerate multimodal artifacts
copy ..\.env.example .env        # add API keys if you regenerate image/voice analyses
```

Generate predictions:

```bash
python main.py --input ../dataset/messages.csv --output ../output.csv --models ../models
```

Reads `dataset/voice_transcriptions.json` and `dataset/image_analyses.json` (already
committed) to enrich voice/image messages at inference time.

## Code Structure

```
code/
├── main.py                      # CLI entry point
├── agent_orchestrator.py        # LangGraph pipeline: guardrail -> rules -> XGBoost -> router -> validation
├── train_pipeline.py            # MessageRoutingPipeline, MessageTypeInferer, ConfidenceCalibrator, training
├── rule_based_classifier.py     # Deterministic rules (forwards, scams, urgency, negation)
├── bedrock_multimodal.py        # Image analysis via Bedrock (env key, optional offline)
├── nvidia_multimodal.py         # NVIDIA multimodal analysis (optional offline tool)
├── process_riva.py              # Voice transcription via Riva ASR (offline regen tool)
├── requirements.txt             # Inference dependencies
├── features/
│   ├── text_features.py
│   ├── user_features.py
│   └── multimodal_features.py   # 59 total features
└── utils/
    └── data_loader.py           # Dataset loading + history lookups
```

Models live in `../models/` (trained XGBoost + label encoder + metadata).

## Pipeline

1. **Input guardrail** (`agent_orchestrator.py`): blocks prompt-injection and
   router-manipulation attempts -> `mute` / `scam` / 0.99.
2. **Rule-based classifier** (`rule_based_classifier.py`): forwards, scam terms,
   urgent time-sensitive patterns, and urgency negation (~40% of messages).
3. **XGBoost classifier**: trained on the provided labeled samples.
4. **Router**: predictions below the confidence threshold pass to a reviewer
   node (deterministic pass-through; swap in a live LLM without graph changes).
5. **Pydantic validator**: enforces the exact output schema.

## Message Type Inference

`MessageTypeInferer` order matters (first match wins):
`scam` -> `injection` -> `forward` -> `event` -> `payment` -> `greeting` ->
`urgent` -> `promotion` -> `unknown`, with an early negation-of-urgency check so
polite, non-urgent messages ("No need to reply", "when you get a chance") route
to `digest` instead of `notify`.

## Confidence

`ConfidenceCalibrator.transform(p, cls)` returns the raw predicted probability
smoothed toward the majority class: `clip(0.5*p + 0.5*max(p, 1-p), 0.05, 0.95)`.
No fabricated ranges - confidence reflects model uncertainty.

## Multimodal Regeneration (optional)

Voice transcripts and image analyses are already committed; regenerate only if
the media files change:

```bash
# Voice (requires a Riva endpoint)
set RIVA_ENDPOINT=127.0.0.1:50051
python process_riva.py --messages ../dataset/messages.csv --media-dir ../dataset/media/audio --output ../dataset/voice_transcriptions.json

# Images (requires a vision API key)
python nvidia_multimodal.py --messages ../dataset/messages.csv --media-dir ../dataset/media/images --output ../dataset/image_analyses.json
```

## Tests

```bash
python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('*.py')]; print('syntax OK')"
```
