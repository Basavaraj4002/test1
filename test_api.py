"""
Run this to test the Word Recall API locally before deploying to Render.

Usage:
  1. Set your Gemini API key:     export GEMINI_API_KEY=your_key_here
  2. Start the server:            uvicorn main:app --reload
  3. In another terminal:         python test_api.py
"""

import requests
import json

BASE = "http://localhost:8000"

def run_test():
    print("=" * 55)
    print("  CogniScan — Word Recall API Test")
    print("=" * 55)

    # ── Step 1: Start test ─────────────────────────────────────
    print("\n[1] Starting test session...")
    start_res = requests.post(f"{BASE}/api/test/word-recall/start", json={
        "patient_id": "test_patient_001",
        "age": 68,
        "education_years": 12,
        "language": "en"
    })
    assert start_res.status_code == 200, f"Start failed: {start_res.text}"
    session = start_res.json()

    print(f"    Session ID : {session['session_id']}")
    print(f"    Words shown: {session['words']}")
    print(f"    Distractor : {session['distractor_task']}")

    # ── Step 2: Simulate patient recall ───────────────────────
    # Patient remembered 3 of 5 words + 1 wrong word (intrusion)
    words_shown = session["words"]
    immediate_recall = [words_shown[0], words_shown[2], words_shown[4], "house"]

    print(f"\n[2] Submitting recall...")
    print(f"    Shown    : {words_shown}")
    print(f"    Recalled : {immediate_recall}")

    submit_res = requests.post(f"{BASE}/api/test/word-recall/submit", json={
        "session_id": session["session_id"],
        "patient_id": "test_patient_001",
        "age": 68,
        "education_years": 12,
        "language": "en",
        "words_shown": words_shown,
        "immediate_recall": immediate_recall,
        "immediate_recall_time_ms": 18500,
        "per_word_time_ms": [1200, 3400, 5600, 8900],
        "distractor_completed": True,
        "delayed_recall": [words_shown[0], words_shown[2]],
        "delayed_recall_time_ms": 12000,
        "yes_no_score": 4
    })

    assert submit_res.status_code == 200, f"Submit failed: {submit_res.text}"
    result = submit_res.json()

    print("\n[3] Results:")
    print(f"    Memory Score      : {result['memory_score']}/10")
    print(f"    Immediate Recall  : {result['immediate_recall_score']}/5")
    print(f"    Delayed Recall    : {result['delayed_recall_score']}/5")
    print(f"    Intrusion Errors  : {result['intrusion_errors']}")
    print(f"    Encoding          : {result['encoding_efficiency']}")
    print(f"    Retention Ratio   : {result['retention_ratio']}")
    print(f"    Clinical Flags    : {result['clinical_flags']}")
    print(f"\n    Interpretation: {result['interpretation']}")
    print(f"\n[4] Full result JSON:")
    print(json.dumps(result, indent=2))
    print("\n[SUCCESS] Test passed — ready to deploy on Render")

if __name__ == "__main__":
    run_test()
