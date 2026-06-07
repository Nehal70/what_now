"""Conversational response quality tests — checks actual TEXT, not just tool labels."""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field

import httpx

BASE_URL = "http://localhost:8000/chat/stream"
TIMEOUT = 120.0

# ── Helpers ────────────────────────────────────────────────────────────


def call_stream(transcript: str, history: list[dict]) -> dict:
    payload = {"transcript": transcript, "conversation_history": history}
    with httpx.Client(timeout=TIMEOUT) as client:
        with client.stream("POST", BASE_URL, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.startswith("data: ") and '"type": "done"' in line:
                    return json.loads(line[6:])
    raise RuntimeError("No done event from /chat/stream")


def has_numbered_list(text: str) -> bool:
    return bool(
        re.search(r"^\s*\d+[\.\)]\s", text, re.M)
        or re.search(r"\n\s*\d+[\.\)]\s", text)
        or re.search(r"^\s*[•\-]\s", text, re.M)
    )


def sentence_count(text: str) -> int:
    parts = [p.strip() for p in re.split(r"[.!?]+", text.strip()) if p.strip()]
    return len(parts)


def first_sentence(text: str) -> str:
    m = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    return m[0] if m else text.strip()


@dataclass
class Check:
    name: str
    passed: bool
    critical: bool = False
    detail: str = ""


@dataclass
class TestCase:
    tid: str
    group: str
    title: str
    transcript: str
    history: list[dict] | None = None  # None = use accumulated (Group 1)
    checks_fn: str = ""  # resolved at runtime


@dataclass
class TestResult:
    tid: str
    group: str
    title: str
    done: dict
    checks: list[Check] = field(default_factory=list)
    response: str = ""

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def critical_failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed and c.critical]


# ── Per-test check functions ───────────────────────────────────────────


def checks_1a(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check("No numbered list", not has_numbered_list(resp), critical=True),
        Check("Acknowledges pain/situation", any(w in lower for w in ("hurt", "pain", "slipped", "sorry", "hear", "scary", "tough")), detail=""),
        Check("Asks if safe", any(w in lower for w in ("safe", "move", "okay", "ok ", "can you")), detail=""),
        Check("Under 4 sentences", sentence_count(resp) <= 4),
        Check('No "Want me to go deeper"', "go deeper" not in lower and "elaborate" not in lower, critical=True),
        Check(
            "Does not start with legal info",
            not re.match(r"^(in |under |the statute|premises liability|california|texas|your injury may)", lower),
            critical=True,
        ),
    ]


def checks_1b(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    first = first_sentence(lower)
    empathy = any(p in lower for p in ("i hear you", "breathe", "you're okay", "you are okay", "i'm here", "im here", "it's okay", "its okay"))
    list_fail = has_numbered_list(resp) or len(re.findall(r"\b(then|also|next)\b", lower)) >= 3
    legal_jump = any(w in lower for w in ("statute", "liability", "comparative fault", "lawsuit", "negligence"))
    return [
        Check("First sentence acknowledges fear", empathy or any(w in first for w in ("hey", "i hear", "breathe", "okay", "here")), critical=True),
        Check("Empathy phrase present", empathy, critical=True),
        Check("ONE clear action (not a list)", not list_fail and sentence_count(resp) <= 5),
        Check("No legal advice dump", not legal_jump, critical=True),
    ]


def checks_1c(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check("Says don't sign or wait", any(w in lower for w in ("don't sign", "do not sign", "don't sign", "wait", "need a moment", "need a minute")), critical=True),
        Check("Tells them what to say", any(w in lower for w in ("say", "tell them", "just say", '"', "'"))),
        Check("Specific not generic", len(resp) > 40 and "sign" in lower),
        Check("No numbered list", not has_numbered_list(resp), critical=True),
    ]


def checks_1d(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    tool = done.get("tool_called")
    specific = any(
        w in lower
        for w in (
            "med-pay", "med pay", "medpay", "liability", "health insurance",
            "store's", "stores", "general liability", "your insurance",
            "property owner", "premises",
        )
    )
    vague_yes = bool(re.search(r"^(yes|yeah|insurance (will|should|may) cover)", lower))
    return [
        Check("tool_called = insurance_tool", tool == "insurance_tool", critical=True, detail=f"got {tool}"),
        Check("Mentions coverage types", specific, detail="Med-Pay/liability/health"),
        Check("Specific not vague yes", not vague_yes or specific),
        Check("Not safety_check/none only", tool not in (None, "safety_check", "none"), critical=True),
    ]


def checks_2a(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    tool = done.get("tool_called")
    return [
        Check("tool_called = legal_tool", tool == "legal_tool", critical=True, detail=f"got {tool}"),
        Check("Mentions contingency/free consult", any(w in lower for w in ("contingency", "free consultation", "no fee", "pay nothing")), detail=""),
        Check("Answers lawyer question directly", any(w in lower for w in ("lawyer", "attorney", "yes", "worth", "consult"))),
        Check("Does not deflect to safety only", "later" not in lower and "first let's" not in lower or tool == "legal_tool"),
    ]


def checks_2b(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    tool = done.get("tool_called")
    recorded = any(w in lower for w in ("recorded statement", "recorded", "don't talk", "do not talk", "in writing", "not comfortable"))
    bad = "just answer" in lower or "answer their questions" in lower
    return [
        Check("tool_called = insurance_tool", tool == "insurance_tool", critical=True, detail=f"got {tool}"),
        Check("Recorded statement warning", "recorded" in lower or "don't give" in lower or "do not give" in lower, critical=True),
        Check("Exact words or don't talk", recorded),
        Check('Not "just answer their questions"', not bad, critical=True),
    ]


def checks_2c(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    ctx = done.get("context") or {}
    state = ctx.get("state")
    law_dump = bool(re.search(r"\b(ccp|335\.1|two years|statute|§)\b", lower))
    warm = any(w in lower for w in ("safe", "hurt", "here", "hear", "okay", "sorry", "scary"))
    return [
        Check('context.state = "California"', state == "California", critical=True, detail=f"got {state}"),
        Check("No statute dump on turn 1", not law_dump, critical=True),
        Check("Warm triage tone", warm),
    ]


def checks_3a(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check("Does not say no Montana laws", "don't have info" not in lower and "no information" not in lower),
        Check("Gives general guidance", len(resp) > 30),
        Check("Acknowledges situation", any(w in lower for w in ("slipped", "fell", "hurt", "montana", "state", "here"))),
        Check("No fake Montana statutes", not bool(re.search(r"montana.{0,40}(§|statute \d|code \d)", lower)), critical=True),
    ]


def checks_3b(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check("Recognizes premises/liability", any(w in lower for w in ("report", "document", "store", "home depot", "employee", "incident", "safe", "hurt"))),
        Check("Not slip-only framing", "wet floor" not in lower or "shelf" in lower or "fell" in lower),
        Check("Mentions documenting/reporting", any(w in lower for w in ("photo", "report", "document", "witness", "manager", "record"))),
        Check("Not empty/generic", len(resp) > 40),
    ]


def checks_3c(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check('Does NOT say "you\'re screwed"', "screwed" not in lower or ("not" in lower and "screwed" in lower)),
        Check("Gives hope / next steps", any(w in lower for w in ("not", "still", "okay", "can", "next", "don't panic", "help"))),
        Check("Addresses signing concern", "sign" in lower),
        Check(
            "Form distinction or rights preserved",
            any(w in lower for w in ("incident report", "waiver", "release", "rights", "not giving up", "doesn't mean", "does not mean")),
            detail="incident report vs waiver",
        ),
    ]


def checks_3d(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    too_late = bool(
        re.search(r"missed your chance|can't do anything|cannot do anything", lower)
        or re.search(r"\b(too late|it's too late|is too late)\b", lower)
        and "not too late" not in lower
    )
    return [
        Check("Says NOT too late", not too_late, critical=True),
        Check("Mentions statute/years timeframe", any(w in lower for w in ("year", "statute", "limit", "time", "still"))),
        Check("What to do now", any(w in lower for w in ("doctor", "medical", "document", "photo", "report", "now"))),
        Check("Urgency on medical care", any(w in lower for w in ("doctor", "medical", "urgent", "today", "now", "treatment"))),
    ]


def checks_3e(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check("Retaliation illegal mentioned", any(w in lower for w in ("illegal", "retaliat", "cannot fire", "can't fire", "against the law", "right to file"))),
        Check("Workers comp rights", any(w in lower for w in ("workers comp", "workers' comp", "worker", "comp claim", "workplace"))),
        Check("Document boss statement", any(w in lower for w in ("document", "writing", "written", "record", "email", "text"))),
        Check("Does not side with boss", "listen to your boss" not in lower and "don't file" not in lower.replace("don't tell you not to file", "")), 
    ]


def checks_3f(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    ctx = done.get("context") or {}
    state = ctx.get("state")
    ca_law = "california" in lower and "3342" in lower
    return [
        Check('context.state = "Texas"', state == "Texas", critical=True, detail=f"got {state}"),
        Check("Texas or dog/insurance guidance", any(w in lower for w in ("texas", "dog", "insurance", "animal control", "neighbor", "bite"))),
        Check("No California law for Texas", not ca_law, critical=True),
    ]


def checks_3g(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    accepts_fault = bool(re.search(r"(yes|you were|your fault|entirely your fault|you're at fault)", lower))
    return [
        Check("Does not agree it was their fault", not accepts_fault or "not" in lower[:80], critical=True),
        Check("Comparative fault mentioned", any(w in lower for w in ("comparative", "partial", "still recover", "not entirely", "doesn't mean", "does not mean", "share fault", "percent"))),
        Check("Pushes back warmly", any(w in lower for w in ("doesn't mean", "does not mean", "not necessarily", "store", "still", "sign", "warning"))),
    ]


def checks_3h(resp: str, done: dict) -> list[Check]:
    return [
        Check("Non-empty response", len(resp.strip()) > 10, critical=True),
        Check("Warm / asks what happened", any(w in resp.lower() for w in ("here", "help", "happened", "what", "safe", "tell me"))),
        Check("Under 3 sentences", sentence_count(resp) <= 3),
        Check("No legal dump without context", not bool(re.search(r"statute|liability|comparative fault", resp.lower()))),
    ]


def checks_3i(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    return [
        Check("Acknowledges they have a lawyer", any(w in lower for w in ("lawyer", "attorney", "your lawyer"))),
        Check("Encourages following lawyer advice", any(w in lower for w in ("lawyer", "attorney", "follow", "listen", "told you"))),
        Check("Still addresses insurance generally", any(w in lower for w in ("insurance", "cover", "med", "policy", "claim"))),
        Check("Does not say talk to adjuster freely", "give a recorded statement" not in lower or "don't" in lower),
    ]


def checks_3j(resp: str, done: dict) -> list[Check]:
    lower = resp.lower()
    empathy_first = any(
        p in first_sentence(lower)
        for p in ("i hear", "hey", "this is a lot", "breathe", "you don't have", "i'm here", "im here", "it's okay")
    )
    legal_jump = any(w in lower for w in ("statute", "insurance claim", "liability", "lawsuit", "adjuster"))
    return [
        Check("Empathy first", empathy_first or any(w in lower[:80] for w in ("hear you", "a lot", "okay", "here")), critical=True),
        Check("Warm human tone", any(w in lower for w in ("hear", "okay", "here", "breathe", "moment", "one thing"))),
        Check("No legal/insurance dump", not legal_jump or sentence_count(resp) <= 2, critical=True),
        Check("No numbered list", not has_numbered_list(resp), critical=True),
    ]


CHECK_REGISTRY = {
    "1A": checks_1a,
    "1B": checks_1b,
    "1C": checks_1c,
    "1D": checks_1d,
    "2A": checks_2a,
    "2B": checks_2b,
    "2C": checks_2c,
    "3A": checks_3a,
    "3B": checks_3b,
    "3C": checks_3c,
    "3D": checks_3d,
    "3E": checks_3e,
    "3F": checks_3f,
    "3G": checks_3g,
    "3H": checks_3h,
    "3I": checks_3i,
    "3J": checks_3j,
}

TESTS: list[tuple[str, str, str, str]] = [
    ("1", "1A", "Opening scared user", "I just slipped on a wet floor at a grocery store my wrist really hurts"),
    ("1", "1B", "Panic mode", "please please help me I'm so scared I don't know what to do"),
    ("1", "1C", "Document to sign", "the manager came over and wants me to sign something"),
    ("1", "1D", "Insurance mid-flow", "will my insurance cover this or the store's insurance"),
    ("2", "2A", "Lawyer on turn 1", "I got hurt at a store do I need a lawyer"),
    ("2", "2B", "Adjuster called", "the store's insurance company just called me"),
    ("2", "2C", "California early mention", "I'm in California and I slipped at Target"),
    ("3", "3A", "Montana non-covered state", "I slipped and fell in Montana, am I screwed"),
    ("3", "3B", "Shelf fell unusual injury", "a shelf fell on me at Home Depot while an employee was moving stock"),
    ("3", "3C", "Already signed form", "I already signed the form they gave me, am I screwed now"),
    ("3", "3D", "Injury 3 days ago", "I slipped at a store 3 days ago but I didn't do anything about it, is it too late"),
    ("3", "3E", "Workplace retaliation", "I got hurt at my job, my boss is telling me not to file a workers comp claim"),
    ("3", "3F", "Dog bite Texas", "my neighbor's dog bit me pretty badly, I'm in Texas"),
    ("3", "3G", "Manager blame phone", "the manager said it was my fault because I was on my phone when I fell"),
    ("3", "3H", "Very short help", "help"),
    ("3", "3I", "Already has lawyer", "my lawyer told me not to talk to anyone but I'm confused about what my insurance covers"),
    ("3", "3J", "Emotional breakdown", "I just want to cry I don't know what to do this is too much I can't handle this"),
]


def print_test_result(result: TestResult) -> None:
    done = result.done
    bar = "━" * 30
    print(f"\n{bar}")
    print(f"Test {result.tid}: {result.title}")
    print(bar)
    print(f"Tool: {done.get('tool_called')} | Phase: {done.get('phase')}")
    print(f"Latency: {done.get('latency_ms', 0)}ms")
    print()
    print("RESPONSE:")
    print(f'"{result.response}"')
    print()
    print("CHECKS:")
    for c in result.checks:
        mark = "✅" if c.passed else "❌"
        crit = " (CRITICAL)" if c.critical and not c.passed else ""
        detail = f" — {c.detail}" if c.detail and not c.passed else ""
        print(f"{mark} {c.name}{detail}{crit}")
    print(bar)


def run_tests() -> tuple[list[TestResult], dict]:
    accumulated: list[dict] = []
    results: list[TestResult] = []
    latencies: list[int] = []

    for group, tid, title, transcript in TESTS:
        history = list(accumulated) if group == "1" else []

        time.sleep(0.4)
        try:
            done = call_stream(transcript, history)
        except Exception as exc:
            done = {"response": "", "tool_called": None, "phase": None, "latency_ms": 0, "context": {}}
            checks = [Check("Request succeeded", False, critical=True, detail=str(exc))]
            result = TestResult(tid, group, title, done, checks, "")
            results.append(result)
            print_test_result(result)
            if group == "1":
                accumulated.append({"role": "user", "text": transcript})
                accumulated.append({"role": "assistant", "text": ""})
            continue

        response = done.get("response", "")
        latencies.append(done.get("latency_ms", 0))
        checks = CHECK_REGISTRY[tid](response, done)
        result = TestResult(tid, group, title, done, checks, response)
        results.append(result)
        print_test_result(result)

        if group == "1":
            accumulated.append({"role": "user", "text": transcript})
            accumulated.append({"role": "assistant", "text": response})

    # Aggregate stats
    total = len(results)
    passed_all = sum(1 for r in results if r.all_passed)
    critical_fails = sum(len(r.critical_failures) for r in results)
    warnings = sum(1 for r in results if not r.all_passed and not r.critical_failures)

    g1 = sum(1 for r in results if r.group == "1" and r.all_passed)
    g2 = sum(1 for r in results if r.group == "2" and r.all_passed)
    g3 = sum(1 for r in results if r.group == "3" and r.all_passed)

    numbered_fails = sum(
        1 for r in results
        if any(not c.passed and "numbered list" in c.name.lower() for c in r.checks)
    )
    empathy_fails = sum(
        1 for r in results
        if r.tid in ("1B", "3J")
        and any(not c.passed and c.critical and ("empathy" in c.name.lower() or "fear" in c.name.lower()) for c in r.checks)
    )
    wrong_tool = sum(
        1 for r in results
        if any(not c.passed and "tool_called" in c.name for c in r.checks)
    )
    hallucination = sum(
        1 for r in results
        if r.tid in ("3A", "3F")
        and any(not c.passed and ("fake" in c.name.lower() or "california law for texas" in c.name.lower()) for c in r.checks)
    )

    avg_lat = sum(latencies) / len(latencies) if latencies else 0

    demo_ready = (
        passed_all >= 11
        and numbered_fails == 0
        and empathy_fails == 0
        and critical_fails == 0
        and not any(len(r.response.strip()) < 10 for r in results)
    )

    print("\n╔════════════════════════════════════╗")
    print("║       RESPONSE QUALITY REPORT      ║")
    print("╠════════════════════════════════════╣")
    print(f"║ Total tests:           {total:<11}║")
    print(f"║ Passed all checks:     {passed_all}/{total:<8}║")
    print(f"║ Failed (critical):     {critical_fails:<11}║")
    print(f"║ Warnings:              {warnings:<11}║")
    print("║                                    ║")
    print(f"║ GROUP 1 (Normal flow):   {g1}/4       ║")
    print(f"║ GROUP 2 (Intent override): {g2}/3     ║")
    print(f"║ GROUP 3 (Edge cases):    {g3}/10      ║")
    print("║                                    ║")
    print(f"║ Numbered list failures:  {numbered_fails:<9}║")
    print(f"║ Empathy failures:        {empathy_fails:<9}║")
    print(f"║ Wrong tool fires:        {wrong_tool:<9}║")
    print(f"║ Hallucination warnings:  {hallucination:<9}║")
    print("║                                    ║")
    print(f"║ Avg latency:             {avg_lat:.0f}ms     ║")
    print("║                                    ║")
    print(f"║ DEMO READY: {'YES' if demo_ready else 'NO ':<18}║")
    print("║ (threshold: 11/17 pass,            ║")
    print("║  0 critical empathy fails,         ║")
    print("║  0 numbered list fails)            ║")
    print("╚════════════════════════════════════╝")

    return results, {"demo_ready": demo_ready, "passed_all": passed_all, "total": total}


def main() -> int:
    print("=== RESPONSE QUALITY TESTS (17 cases) ===\n")
    try:
        httpx.get("http://localhost:8000/health", timeout=5.0).raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Server not running on :8000 — {exc}")
        return 1

    results, summary = run_tests()
    return 0 if summary["demo_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
