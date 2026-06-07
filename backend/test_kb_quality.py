"""KB quality go/no-go test — 10 panicked-user questions via /chat/stream."""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field

import httpx

BASE_URL = "http://localhost:8000/chat/stream"
TIMEOUT = 120.0

# ── Scoring keyword banks ──────────────────────────────────────────────

SPECIFICITY_KEYWORDS = [
    r"\bCalifornia\b",
    r"\bTexas\b",
    r"\bNew York\b",
    r"\bFlorida\b",
    r"\bIllinois\b",
    r"\$\d",
    r"\b\d+\s*years?\b",
    r"\b24\s*hours?\b",
    r"\b48\s*hours?\b",
    r"\b14\s*days?\b",
    r"\bState Farm\b",
    r"\bAllstate\b",
    r"\bGEICO\b",
    r"\bProgressive\b",
    r"\bFarmers\b",
    r"recorded statement",
    r"Med-?Pay",
    r"constructive notice",
    r"comparative fault",
    r"one.?bite",
    r"strict liability",
    r"statute of limitations",
    r"workers.?comp",
    r"Colossus",
    r"contingency",
    r"CCP|Civil Code|CPRC|CPLR|735 ILCS",
    r"\b51\s*%\b",
    r"retaliation",
    r"surveillance",
    r"72\s*hours?",
]

EMPATHY_KEYWORDS = [
    r"\byou\b",
    r"\byour\b",
    r"I'm here",
    r"are you safe",
    r"that sounds",
    r"I understand",
    r"sorry",
    r"first",
]

ACTIONABILITY_KEYWORDS = [
    r"right now",
    r"say exactly",
    r"just say",
    r"do not",
    r"don't",
    r"don’t",
    r"before you",
    r"\bcall\b",
    r"photograph",
    r"take a photo",
    r"take photos",
    r"photos of",
    r"write down",
    r"keep a copy",
    r"fill out",
    r"in writing",
    r"next step",
    r"one more thing",
    r"make sure",
    r"get the witness",
    r"get medical",
    r"report it",
    r"stay put",
]

ACKNOWLEDGMENT_STARTS = (
    "are you",
    "you okay",
    "i'm here",
    "first",
    "that sounds",
    "i understand",
    "okay",
    "ok ",
    "good ",
    "don't",
    "do not",
    "tell them",
)

COLD_STARTS = (
    "in california",
    "in texas",
    "the statute",
    "personal injury",
    "under california",
    "under texas",
    "generally",
    "typically",
    "it is important",
)


@dataclass
class Question:
    qid: int
    label: str
    transcript: str
    expected_tool: str | None = None
    expected_phase: str | None = None
    known_state: str | None = None
    history: list[dict] | None = None  # None = use accumulated history
    expect_keywords: list[str] = field(default_factory=list)
    allow_numbered: bool = False


QUESTIONS: list[Question] = [
    Question(
        1,
        "Triage slip at Walmart",
        "I just slipped on a wet floor at Walmart, my back hurts",
        expected_tool="safety_check",
        expected_phase="triage",
    ),
    Question(
        2,
        "Gather — manager form",
        "I can move but the manager just came over with a paper to sign",
        expected_tool="scene_guide",
        expected_phase="gather",
    ),
    Question(
        3,
        "Gather — California witness",
        "okay I didn't sign it, I'm in California, one person saw it happen",
        expected_tool="scene_guide",
        expected_phase="gather",
        known_state="California",
        expect_keywords=["2 year", "witness"],
    ),
    Question(
        4,
        "Inform — adjuster called",
        "the store's adjuster just called me",
        expected_tool="insurance_tool",
        expected_phase="inform",
        known_state="California",
        expect_keywords=["recorded statement"],
    ),
    Question(
        5,
        "Inform — need lawyer?",
        "do I actually need a lawyer for this",
        expected_tool="legal_tool",
        expected_phase="inform",
        known_state="California",
        expect_keywords=["contingency", "comparative fault"],
    ),
    Question(
        6,
        "Dog bite Texas (new scenario)",
        "my neighbor's dog bit me pretty bad, I'm in Texas",
        expected_tool="safety_check",
        expected_phase="triage",
        known_state="Texas",
        history=[],
        expect_keywords=["Texas", "one bite", "insurance"],
    ),
    Question(
        7,
        "State Farm calling",
        "State Farm keeps calling me, what do they actually want",
        expected_tool="insurance_tool",
        expected_phase="inform",
        expect_keywords=["State Farm", "recorded statement"],
        history=[
            {"role": "user", "text": "I was rear-ended last week, neck is sore"},
            {"role": "assistant", "text": "Are you safe? Did you get checked out?"},
            {"role": "user", "text": "Yeah urgent care said whiplash, I'm in Ohio"},
            {"role": "assistant", "text": "Good you went. Document everything and follow up with your doctor."},
            {"role": "user", "text": "The other driver's insurer already called once"},
            {"role": "assistant", "text": "Don't give them a recorded statement yet. Keep it brief."},
        ],
    ),
    Question(
        8,
        "Workplace pressure",
        "I got hurt at work, my employer is pressuring me not to file anything",
        expected_tool="legal_tool",
        expected_phase="inform",
        expect_keywords=["workers comp", "retaliation"],
        history=[
            {"role": "user", "text": "I fell off a ladder at my warehouse job"},
            {"role": "assistant", "text": "Are you safe? Did you report it to a supervisor?"},
            {"role": "user", "text": "Yes but my boss told me to just go home and rest"},
            {"role": "assistant", "text": "You still need medical care and a written report on file."},
            {"role": "user", "text": "I'm in Illinois, shoulder is killing me"},
            {"role": "assistant", "text": "Get seen today if you haven't. Illinois workers comp covers job injuries."},
        ],
    ),
    Question(
        9,
        "Documentation checklist",
        "what evidence do I need for my case",
        expected_phase="inform",
        known_state="California",
        expect_keywords=["photo", "witness", "surveillance", "journal"],
        history=[
            {"role": "user", "text": "I slipped at a grocery store in California, hurt my wrist"},
            {"role": "assistant", "text": "Are you safe? What happened exactly?"},
            {"role": "user", "text": "Manager had a form, I didn't sign"},
            {"role": "assistant", "text": "Good call not signing. Take photos if you can."},
            {"role": "user", "text": "There's a witness and I have photos of the wet floor"},
            {"role": "assistant", "text": "In California you have two years to file. Keep that witness info."},
        ],
    ),
    Question(
        10,
        "Summarize everything",
        "okay summarize everything I need to do",
        expected_phase="summarize",
        known_state="California",
        allow_numbered=True,
        history=None,  # filled from Q1–Q5 run
    ),
]


# ── HTTP / SSE ─────────────────────────────────────────────────────────


def call_stream(transcript: str, history: list[dict]) -> dict:
    payload = {"transcript": transcript, "conversation_history": history}
    with httpx.Client(timeout=TIMEOUT) as client:
        with client.stream("POST", BASE_URL, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: ") and '"type": "done"' in line:
                    return json.loads(line[6:])
    raise RuntimeError("No done event received from /chat/stream")


# ── Scoring ───────────────────────────────────────────────────────────


def _find_keywords(text: str, patterns: list[str]) -> list[str]:
    found = []
    lower = text.lower()
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            found.append(pat.replace("\\b", "").replace("\\", "")[:40])
    return found


def _keyword_present(text: str, kw: str) -> bool:
    lower = text.lower()
    kw_lower = kw.lower()
    if kw_lower in lower:
        return True
    # "2 year" matches "two years"
    if "2 year" in kw_lower and re.search(r"two\s+years?|2\s+years?", lower):
        return True
    if "workers comp" in kw_lower and re.search(r"workers.?comp", lower):
        return True
    return False


def score_specificity(text: str, expect: list[str]) -> tuple[int, list[str], list[str]]:
    found = _find_keywords(text, SPECIFICITY_KEYWORDS)
    for kw in expect:
        if _keyword_present(text, kw) and kw not in found:
            found.append(kw)

    if re.search(r"\$\d", text) or re.search(r"\b\d+\s*years?\b", text, re.I):
        score = 5
    elif len(found) >= 3:
        score = 5
    elif len(found) >= 1:
        score = 3
    else:
        score = 1
    missing = [k for k in expect if not _keyword_present(text, k)]
    return score, found, missing


def score_empathy(text: str) -> tuple[int, str]:
    lower = text.lower().strip()
    notes: list[str] = []

    has_you = bool(re.search(r"\byou(r)?\b", lower))
    has_warm = any(re.search(p, lower) for p in EMPATHY_KEYWORDS)

    if lower.startswith("i'm an ai") or "as an ai" in lower:
        return 1, "robotic / AI disclosure"

    starts_ack = any(lower.startswith(s) for s in ACKNOWLEDGMENT_STARTS)
    starts_cold = any(lower.startswith(s) for s in COLD_STARTS)

    if starts_cold and not starts_ack:
        notes.append("cold legal dump opening")
    if has_you and (starts_ack or has_warm):
        score = 5
        notes.append("warm, person-first")
    elif has_you or has_warm:
        score = 3
        notes.append("neutral")
    else:
        score = 1
        notes.append("robotic, no you/your")

    return score, "; ".join(notes)


def score_actionability(text: str) -> tuple[int, str]:
    found = _find_keywords(text, ACTIONABILITY_KEYWORDS)
    has_quotes = ('"' in text or "'" in text) and re.search(r"say|tell them", text, re.I)

    if len(found) >= 2 or (has_quotes and len(found) >= 1):
        return 5, f"specific next steps ({', '.join(found[:4])})"
    if len(found) >= 1:
        return 3, "direction but vague"
    return 1, "no clear next step"


def check_flags(text: str, q: Question) -> list[str]:
    flags: list[str] = []
    lower = text.lower()

    if re.search(r"i'm an ai|as an ai|language model", lower):
        flags.append("FAIL: says 'I'm an AI'")

    if len(text) < 50:
        flags.append("FAIL: under 50 chars (too short)")

    if len(text) > 800:
        flags.append("WARN: over 800 chars (too long for voice)")

    if re.search(r"consult a (professional|attorney|lawyer)", lower):
        if not re.search(r"free consultation|contingency|33%|say exactly|do not|don't", lower):
            flags.append("WARN: consult professional without specific guidance")

    if re.search(r"^\s*\d+[\.\)]\s", text, re.M) or re.search(r"\n\s*\d+[\.\)]\s", text):
        if not q.allow_numbered:
            flags.append("WARN: numbered list (should be prose for voice)")

    if q.known_state and q.known_state.lower() not in lower:
        if q.expected_phase in ("inform", "summarize", "gather") and q.qid <= 5:
            flags.append(f"WARN: does not mention {q.known_state}")

    return flags


def print_question_report(
    q: Question,
    done: dict,
    spec: int,
    spec_found: list[str],
    spec_missing: list[str],
    emp: int,
    emp_note: str,
    act: int,
    act_note: str,
    flags: list[str],
) -> dict:
    tool = done.get("tool_called")
    phase = done.get("phase")
    latency = done.get("latency_ms", 0)
    response = done.get("response", "")

    tool_ok = q.expected_tool is None or tool == q.expected_tool
    phase_ok = q.expected_phase is None or phase == q.expected_phase
    total = spec + emp + act

    bar = "━" * 28
    print(f"\n{bar}")
    print(f'Q{q.qid}: "{q.transcript}"')
    print(bar)
    print(f"Tool fired: {tool} {'✅' if tool_ok else '❌'} (expected {q.expected_tool or 'any'})")
    print(f"Phase: {phase} {'✅' if phase_ok else '❌'} (expected {q.expected_phase or 'any'})")
    print(f"Latency: {latency}ms")
    print()
    print("RESPONSE:")
    print(f'"{response}"')
    print()
    print("SCORE:")
    print(f'  Specificity:   {spec}/5 [found: {", ".join(spec_found[:6]) or "none"}]')
    print(f"  Empathy:       {emp}/5 [{emp_note}]")
    print(f"  Actionability: {act}/5 [{act_note}]")
    print(f"  TOTAL:         {total}/15")
    print()
    print(f"Keywords found: {spec_found[:10]}")
    print(f"Keywords missing: {spec_missing}")
    if flags:
        print(f"Flags: {', '.join(flags)}")
    print(bar)

    return {
        "qid": q.qid,
        "tool_ok": tool_ok,
        "phase_ok": phase_ok,
        "spec": spec,
        "emp": emp,
        "act": act,
        "total": total,
        "latency": latency,
        "flags": flags,
        "response": response,
    }


def print_final_summary(results: list[dict]) -> bool:
    n = len(results)
    tool_ok = sum(1 for r in results if r["tool_ok"])
    phase_ok = sum(1 for r in results if r["phase_ok"])
    avg_spec = sum(r["spec"] for r in results) / n
    avg_emp = sum(r["emp"] for r in results) / n
    avg_act = sum(r["act"] for r in results) / n
    avg_total = sum(r["total"] for r in results) / n
    avg_lat = sum(r["latency"] for r in results) / n

    fails = [f"Q{r['qid']}" for r in results if any("FAIL" in f for f in r["flags"])]
    demo_ready = avg_total >= 10 and tool_ok >= 8 and not fails

    print("\n╔══════════════════════════════╗")
    print("║     KB QUALITY REPORT        ║")
    print("╠══════════════════════════════╣")
    print(f"║ Questions tested:    {n:<8}║")
    print(f"║ Correct tool:        {tool_ok}/{n:<7}║")
    print(f"║ Correct phase:       {phase_ok}/{n:<7}║")
    print(f"║ Avg specificity:     {avg_spec:.1f}/5   ║")
    print(f"║ Avg empathy:         {avg_emp:.1f}/5   ║")
    print(f"║ Avg actionability:   {avg_act:.1f}/5   ║")
    print(f"║ Avg total score:     {avg_total:.1f}/15  ║")
    print(f"║ Avg latency:         {avg_lat:.0f}ms    ║")
    print("║                              ║")
    print(f"║ DEMO READY: {'YES' if demo_ready else 'NO ':<13}║")
    print("║ (threshold: 10/15 avg,       ║")
    print("║  8/10 correct tools)         ║")
    print("╚══════════════════════════════╝")

    if fails:
        print(f"\nHard FAILs: {', '.join(fails)}")

    return demo_ready


def main() -> int:
    print("=== KB QUALITY TEST (10 questions) ===\n")

    # Health check
    try:
        httpx.get("http://localhost:8000/health", timeout=5.0).raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Server not reachable at localhost:8000 — start uvicorn first.\n{exc}")
        return 1

    accumulated: list[dict] = []
    results: list[dict] = []

    for q in QUESTIONS:
        if q.qid == 10:
            history = list(accumulated)
        elif q.history is not None:
            history = list(q.history)
        elif q.qid <= 5:
            history = list(accumulated)
        else:
            history = []

        time.sleep(0.5)
        try:
            done = call_stream(q.transcript, history)
        except Exception as exc:
            print(f"\nQ{q.qid} ERROR: {exc}")
            results.append(
                {
                    "qid": q.qid,
                    "tool_ok": False,
                    "phase_ok": False,
                    "spec": 0,
                    "emp": 0,
                    "act": 0,
                    "total": 0,
                    "latency": 0,
                    "flags": ["FAIL: request error"],
                    "response": "",
                }
            )
            continue

        response = done.get("response", "")
        spec, spec_found, spec_missing = score_specificity(response, q.expect_keywords)
        emp, emp_note = score_empathy(response)
        act, act_note = score_actionability(response)
        flags = check_flags(response, q)

        row = print_question_report(
            q, done, spec, spec_found, spec_missing, emp, emp_note, act, act_note, flags
        )
        results.append(row)

        # Accumulate history for Q1–Q5 chain only
        if q.qid <= 5:
            accumulated.append({"role": "user", "text": q.transcript})
            accumulated.append({"role": "assistant", "text": response})

    demo_ready = print_final_summary(results)
    return 0 if demo_ready else 1


if __name__ == "__main__":
    sys.exit(main())
