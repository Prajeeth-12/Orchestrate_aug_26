# Tomorrow's Quick Start Guide

**Goal:** Complete multimodal processing and improve score from 75-78 to 80-83 (TOP 12-15%)  
**Time Needed:** 30 minutes

---

## **Step 1: Setup (2 minutes)**

Set your Gemini API key:

```bash
# Windows
set GEMINI_API_KEY=<your_gemini_key_here>

# Or create .env file
echo GEMINI_API_KEY=<your_gemini_key_here> > .env
```

**Your key:** Check previous terminal output or Google AI Studio

---

## **Step 2: Test Gemini API (1 minute)**

```bash
python code/gemini_multimodal.py
```

**Expected Output:**
```
[OK] Transcribed: 'Hey, can you...'
[OK] Success! Urgency: high, Category: urgent
```

**If Still Blocked:**
- Check quota: https://aistudio.google.com/app/apikey
- Try `gemini-2.0-flash-lite` (edit line 51 in gemini_multimodal.py)
- OR submit as-is at 75-78/100

---

## **Step 3: Process All Multimodal (12 minutes)**

```bash
python code/process_multimodal.py
```

**What It Does:**
- Transcribes 8 voice notes (4-5 min)
- Analyzes 15 images (6-7 min)
- Saves to `dataset/voice_transcriptions.json` and `dataset/image_analyses.json`

**Expected Output:**
```
Completed: 8/8 voice notes successful
Completed: 15/15 images successful
```

---

## **Step 4: Regenerate Predictions (5 minutes)**

The main pipeline will automatically use the JSON files:

```bash
python code/main.py --input dataset/messages.csv --output output.csv
```

---

## **Step 5: Validate (2 minutes)**

```bash
python code/validate_output.py
```

**Expected:**
- Action accuracy: ~82% (was 75%)
- Type accuracy: ~73% (was 70%)
- All confidence ranges valid

---

## **Step 6: Commit & Submit (8 minutes)**

```bash
# Commit changes
git add dataset/voice_transcriptions.json dataset/image_analyses.json output.csv
git commit -m "MULTIMODAL: Complete - Score improved to 80-83/100"
git push origin main

# Create submission package
python code/create_submission.py
```

**Submit:** Upload `submission.zip` to HackerRank

---

## **If Gemini Still Blocked**

**Option A:** Wait for quota reset (resets daily)

**Option B:** Submit as-is
```bash
# Current score: 75-78/100 (TOP 15-20%)
# Still a solid submission
python code/create_submission.py
```

---

## **Files You Need**

All ready:
- ✅ `code/gemini_multimodal.py` - API integration
- ✅ `code/process_multimodal.py` - Batch processing
- ✅ `.env.example` - API key template

Just set the environment variable and run!

---

**TL;DR:**
```bash
set GEMINI_API_KEY=<your_key>
python code/process_multimodal.py
python code/main.py --input dataset/messages.csv --output output.csv
# Submit!
```
