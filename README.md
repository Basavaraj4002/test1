# CogniScan — Test 1: Word Recall Service

Episodic memory assessment microservice. Part of the CogniScan dementia screening platform.

---

## What This Service Does

1. **`/api/test/word-recall/start`** — Returns a word set + distractor arithmetic questions
2. **`/api/test/word-recall/submit`** — Accepts recall responses, runs Gemini analysis, returns `memory_score` (0–10)

The `memory_score` output feeds directly into the Aggregator service (Service 7).

---

## Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Gemini API key
export GEMINI_API_KEY=your_gemini_key_here

# 3. Run the server
uvicorn main:app --reload

# 4. Test it
python test_api.py

# 5. View auto-generated API docs
open http://localhost:8000/docs
```

---

## Deploy to Render

1. Push this folder to a GitHub repo (can be a sub-folder in a monorepo)
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable: `GEMINI_API_KEY` = your key
6. Deploy — you get a URL like `https://cogni-word-recall.onrender.com`
7. Update `BASE_URL` in `word_recall_service.dart`

---

## API Response (what goes to Aggregator)

```json
{
  "memory_score": 6.2,
  "immediate_recall_score": 3.0,
  "delayed_recall_score": 2.0,
  "intrusion_errors": 1,
  "encoding_efficiency": "moderate",
  "retention_ratio": 0.67,
  "clinical_flags": ["Immediate recall below age-expected norm"],
  "interpretation": "Patient recalled 3 of 5 words. Mild memory concern noted.",
  "raw_data": { ... }
}
```

---

## Test Flow in Flutter App

```
Show 5 words for 10 seconds
         ↓
3 arithmetic questions (2 minute distractor)
         ↓
"Please type the words you remember"
         ↓
POST /submit → get memory_score
         ↓
Store result → move to Test 2
```
