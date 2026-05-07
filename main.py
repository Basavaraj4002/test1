from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import os
import json
import random
import time

app = FastAPI(
    title="CogniScan — Word Recall Service",
    description="Test 1: Episodic Memory Assessment via Word Recall",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ─── Word Banks ────────────────────────────────────────────────────────────────
# Words chosen by concreteness, imageability, and cross-language recognizability
WORD_SETS = {
    "en": [
        ["apple", "table", "river", "honesty", "purple"],
        ["doctor", "garden", "music", "window", "elephant"],
        ["candle", "justice", "banana", "carpet", "village"],
    ],
    "hi": [
        ["सेब", "मेज़", "नदी", "ईमानदारी", "बैंगनी"],
        ["डॉक्टर", "बगीचा", "संगीत", "खिड़की", "हाथी"],
        ["मोमबत्ती", "न्याय", "केला", "कालीन", "गाँव"],
    ]
}

DISTRACTOR_QUESTIONS = [
    {"question": "What is 14 + 9?", "answer": "23"},
    {"question": "What is 27 - 8?", "answer": "19"},
    {"question": "What is 6 × 4?", "answer": "24"},
    {"question": "What is 36 ÷ 6?", "answer": "6"},
    {"question": "What is 15 + 17?", "answer": "32"},
]

# ─── Request / Response Models ─────────────────────────────────────────────────

class StartTestRequest(BaseModel):
    patient_id: str
    age: int
    education_years: int
    language: str = "en"  # "en" or "hi"

class StartTestResponse(BaseModel):
    session_id: str
    words: List[str]
    display_duration_seconds: int  # how long to show words
    distractor_questions: List[dict]  # arithmetic to do before recall
    distractor_duration_seconds: int

class SubmitRecallRequest(BaseModel):
    session_id: str
    patient_id: str
    age: int
    education_years: int
    language: str = "en"
    words_shown: List[str]
    immediate_recall: List[str]          # words recalled right after
    immediate_recall_time_ms: int        # total time taken for immediate recall
    per_word_time_ms: Optional[List[int]] = None   # ms taken per word recalled
    distractor_completed: bool = True
    delayed_recall: Optional[List[str]] = None     # recalled at end of full battery
    delayed_recall_time_ms: Optional[int] = None

class WordRecallResult(BaseModel):
    session_id: str
    patient_id: str
    # Raw scores
    immediate_recall_score: float        # 0-5
    delayed_recall_score: Optional[float]  # 0-5
    intrusion_errors: int                # recalled words NOT in original list
    # Normalized score for aggregator
    memory_score: float                  # 0-10, age & education normalized
    # Breakdown
    encoding_efficiency: str             # "good" / "moderate" / "poor"
    retention_ratio: Optional[float]     # delayed/immediate — measures forgetting
    clinical_flags: List[str]            # e.g. ["high intrusion errors", "rapid forgetting"]
    interpretation: str                  # plain English for family
    raw_data: dict                       # full data for aggregator


# ─── In-memory session store (replace with Redis for production) ───────────────
sessions = {}


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "CogniScan Word Recall", "status": "running", "test": "Test 1 — Episodic Memory"}


@app.post("/api/test/word-recall/start", response_model=StartTestResponse)
def start_test(req: StartTestRequest):
    """
    Call this first. Returns a word set and distractor arithmetic questions.
    Flutter shows words for 10 seconds, then runs distractor for 2 minutes,
    then calls /submit.
    """
    lang = req.language if req.language in WORD_SETS else "en"
    word_set = random.choice(WORD_SETS[lang])
    session_id = f"{req.patient_id}_{int(time.time())}"

    sessions[session_id] = {
        "patient_id": req.patient_id,
        "words": word_set,
        "language": lang,
        "started_at": time.time()
    }

    return StartTestResponse(
        session_id=session_id,
        words=word_set,
        display_duration_seconds=10,
        distractor_questions=random.sample(DISTRACTOR_QUESTIONS, 3),
        distractor_duration_seconds=120
    )


@app.post("/api/test/word-recall/submit", response_model=WordRecallResult)
def submit_recall(req: SubmitRecallRequest):
    """
    Submit recall results. Gemini scores and interprets the performance.
    """
    # ── Basic scoring ──────────────────────────────────────────────────────────
    words_shown_lower = [w.lower().strip() for w in req.words_shown]

    immediate_lower = [w.lower().strip() for w in req.immediate_recall]
    immediate_correct = [w for w in immediate_lower if w in words_shown_lower]
    immediate_score = len(immediate_correct)
    immediate_intrusions = len([w for w in immediate_lower if w not in words_shown_lower])

    delayed_score = None
    delayed_intrusions = 0
    retention_ratio = None

    if req.delayed_recall is not None:
        delayed_lower = [w.lower().strip() for w in req.delayed_recall]
        delayed_correct = [w for w in delayed_lower if w in words_shown_lower]
        delayed_score = len(delayed_correct)
        delayed_intrusions = len([w for w in delayed_lower if w not in words_shown_lower])
        if immediate_score > 0:
            retention_ratio = round(delayed_score / immediate_score, 2)

    total_intrusions = immediate_intrusions + delayed_intrusions

    # ── Gemini analysis ────────────────────────────────────────────────────────
    prompt = f"""
You are a neuropsychologist scoring a word recall test for early dementia screening.

Patient Info:
- Age: {req.age}
- Education: {req.education_years} years
- Language: {req.language}

Test Data:
- Words shown: {req.words_shown}
- Immediate recall (right after distractor): {req.immediate_recall}
- Immediate recall score: {immediate_score}/5
- Time for immediate recall: {req.immediate_recall_time_ms}ms
- Intrusion errors (wrong words recalled): {total_intrusions}
- Delayed recall (end of battery): {req.delayed_recall if req.delayed_recall else "not yet administered"}
- Delayed recall score: {delayed_score if delayed_score is not None else "pending"}
- Retention ratio: {retention_ratio if retention_ratio else "pending"}

Scoring norms (age-adjusted):
- Ages 50-59: Immediate ≥4 normal, Delayed ≥3 normal
- Ages 60-69: Immediate ≥3 normal, Delayed ≥3 normal  
- Ages 70-79: Immediate ≥3 normal, Delayed ≥2 normal
- Ages 80+:   Immediate ≥2 normal, Delayed ≥2 normal
- Education adjustment: <8 years → lower threshold by 1
- Intrusion errors > 2 is clinically significant

Provide analysis in this EXACT JSON format (no markdown, no extra text):
{{
  "memory_score": <float 0-10, age and education normalized>,
  "encoding_efficiency": "<good|moderate|poor>",
  "clinical_flags": [<list of clinical concerns as strings, empty if none>],
  "interpretation": "<2 sentences max, plain English for family member>",
  "doctor_note": "<1 sentence clinical note for neurologist>"
}}
"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        gemini_data = json.loads(raw_text.strip())
    except Exception as e:
        # Fallback scoring if Gemini fails
        gemini_data = _fallback_scoring(immediate_score, delayed_score, total_intrusions, req.age)

    return WordRecallResult(
        session_id=req.session_id,
        patient_id=req.patient_id,
        immediate_recall_score=float(immediate_score),
        delayed_recall_score=float(delayed_score) if delayed_score is not None else None,
        intrusion_errors=total_intrusions,
        memory_score=gemini_data.get("memory_score", 5.0),
        encoding_efficiency=gemini_data.get("encoding_efficiency", "moderate"),
        retention_ratio=retention_ratio,
        clinical_flags=gemini_data.get("clinical_flags", []),
        interpretation=gemini_data.get("interpretation", "Results recorded."),
        raw_data={
            "words_shown": req.words_shown,
            "immediate_recall": req.immediate_recall,
            "immediate_score": immediate_score,
            "delayed_recall": req.delayed_recall,
            "delayed_score": delayed_score,
            "intrusion_errors": total_intrusions,
            "retention_ratio": retention_ratio,
            "immediate_recall_time_ms": req.immediate_recall_time_ms,
            "per_word_time_ms": req.per_word_time_ms,
            "age": req.age,
            "education_years": req.education_years,
            "doctor_note": gemini_data.get("doctor_note", "")
        }
    )


# ─── Fallback scoring (if Gemini API is down) ──────────────────────────────────
def _fallback_scoring(immediate: int, delayed, intrusions: int, age: int) -> dict:
    # Age-adjusted thresholds
    if age < 60:
        norm = 4
    elif age < 70:
        norm = 3
    elif age < 80:
        norm = 3
    else:
        norm = 2

    ratio = immediate / 5.0
    base_score = ratio * 10

    if intrusions > 2:
        base_score -= 1.5
    if immediate < norm:
        base_score -= 1.0

    base_score = max(0.0, min(10.0, base_score))

    flags = []
    if intrusions > 2:
        flags.append("High intrusion errors — may indicate confabulation")
    if immediate < norm:
        flags.append(f"Immediate recall below age-expected norm ({norm}/5)")

    efficiency = "good" if immediate >= norm else ("moderate" if immediate >= norm - 1 else "poor")

    return {
        "memory_score": round(base_score, 1),
        "encoding_efficiency": efficiency,
        "clinical_flags": flags,
        "interpretation": f"Patient recalled {immediate} of 5 words immediately. {'Some concerns noted.' if flags else 'Performance within normal range.'}",
        "doctor_note": f"Immediate recall: {immediate}/5. Intrusion errors: {intrusions}."
    }
