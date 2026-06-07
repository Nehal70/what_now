import asyncio
import json
import os
import re
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI, RateLimitError, APIStatusError

from incident_stack import (
    IncidentStack,
    get_next_question,
    get_or_create_stack,
)
from tools.demo_guidance import (
    get_demo_fallback_response,
    get_demo_guidance,
    get_jake_first_guiding_response,
    get_jake_settlement_response,
)
from tools.insurance_tool import OWN_POLICY_TRIGGERS, run as insurance_tool_run
from tools.legal_tool import run as legal_tool_run
from tools.moss_retrieval import run as moss_retrieval_run
from tools.safety_check import run as safety_check_run
from tools.scene_guide import run as scene_guide_run

load_dotenv(override=True)


class LatencyProfiler:
    def __init__(self):
        self.start = time.time()
        self.checkpoints: list[dict[str, int | str]] = []

    def mark(self, label: str):
        elapsed = round((time.time() - self.start) * 1000)
        self.checkpoints.append({"step": label, "ms": elapsed})
        print(f"[LATENCY] {label}: {elapsed}ms")

    def _ms(self, label: str) -> int | None:
        for cp in self.checkpoints:
            if cp["step"] == label:
                return cp["ms"]
        return None

    def _segment(self, start_label: str, end_label: str) -> int | None:
        start = self._ms(start_label)
        end = self._ms(end_label)
        if start is None or end is None:
            return None
        return end - start

    def _print_breakdown(self) -> None:
        segments = [
            ("request_received", "messages_built", "overhead"),
            ("messages_built", "first_llm_call_done", "LLM thinking"),
            ("first_llm_call_done", "tool_execution_done", "tool execution"),
            ("tool_execution_done", "first_token_streamed", "second LLM"),
            ("first_token_streamed", "last_token_streamed", "streaming"),
        ]

        print("---- LATENCY BREAKDOWN ----")
        for start_label, end_label, note in segments:
            delta = self._segment(start_label, end_label)
            if delta is None:
                continue
            print(f"{start_label} → {end_label}:{' ' * (38 - len(start_label) - len(end_label))}{delta}ms  ({note})")

        total = self.checkpoints[-1]["ms"] if self.checkpoints else 0
        first_word = self._ms("first_token_streamed")
        print("---------------------------")
        print(f"TOTAL:{' ' * 34}{total}ms")
        if first_word is not None:
            print(f"FIRST WORD AT:{' ' * 26}{first_word}ms")
        print("---------------------------")

    def report(self):
        print("\n[LATENCY REPORT]")
        prev = 0
        for cp in self.checkpoints:
            delta = cp["ms"] - prev
            print(f"  {cp['step']}: {cp['ms']}ms total (+{delta}ms)")
            prev = cp["ms"]
        if self.checkpoints:
            print(f"  TOTAL: {self.checkpoints[-1]['ms']}ms\n")
        self._print_breakdown()
        print()
        return self.checkpoints

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
LLM_EXTRA_BODY = os.getenv("LLM_EXTRA_BODY")

FALLBACK_RESPONSE = "I'm pulling that information — give me just one moment."

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
THINKING_OPEN = "<think>"
THINKING_CLOSE = "</think>"


class _StreamContentFilter:
    def __init__(self) -> None:
        self._pending = ""
        self._in_thinking = False

    def feed(self, chunk: str) -> str:
        self._pending += chunk
        emitted: list[str] = []

        while self._pending:
            if self._in_thinking:
                close_idx = self._pending.find(THINKING_CLOSE)
                if close_idx == -1:
                    break
                self._pending = self._pending[close_idx + len(THINKING_CLOSE) :].lstrip()
                self._in_thinking = False
                continue

            open_idx = self._pending.find(THINKING_OPEN)
            if open_idx == -1:
                emitted.append(self._pending)
                self._pending = ""
                break

            if open_idx > 0:
                emitted.append(self._pending[:open_idx])
            self._pending = self._pending[open_idx + len(THINKING_OPEN) :]
            self._in_thinking = True

        return "".join(emitted)

_client: OpenAI | None = None

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "safety_check",
            "description": "Run safety triage when the user may be injured. Use first before other tools.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scene_guide",
            "description": "Guide the user on documenting the scene, incident reports, witnesses, and what to say at the scene.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "moss_retrieval",
            "description": "Search the legal/insurance knowledge base for specific facts about laws, claims, or injury guidance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for the knowledge base.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "insurance_tool",
            "description": "Get insurance claim guidance for an incident type and state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_type": {
                        "type": "string",
                        "description": "Type of incident, e.g. slip and fall, car accident.",
                    },
                    "state": {
                        "type": "string",
                        "description": "US state name or abbreviation, or 'unknown'.",
                    },
                },
                "required": ["incident_type", "state"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "legal_tool",
            "description": "Get legal rights, fault rules, and statute of limitations for an incident type and state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_type": {
                        "type": "string",
                        "description": "Type of incident, e.g. slip and fall, car accident.",
                    },
                    "state": {
                        "type": "string",
                        "description": "US state name or abbreviation, or 'unknown'.",
                    },
                },
                "required": ["incident_type", "state"],
            },
        },
    },
]

TOOL_RUNNERS = {
    "safety_check": lambda args: safety_check_run(),
    "scene_guide": lambda args: scene_guide_run(),
    "moss_retrieval": lambda args: moss_retrieval_run(args),
    "insurance_tool": lambda args: insurance_tool_run(
        args.get("incident_type", "general"), args.get("state", "unknown")
    ),
    "legal_tool": lambda args: legal_tool_run(
        args.get("incident_type", "general"), args.get("state", "unknown")
    ),
}


def _normalize_base_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/chat/completions"):
        return endpoint[: -len("/chat/completions")]
    return endpoint


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY is not set in .env")
        if not LLM_ENDPOINT:
            raise ValueError("LLM_ENDPOINT is not set in .env")
        # Qwen compatible-mode: strip /chat/completions from LLM_ENDPOINT for base_url
        _client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=_normalize_base_url(LLM_ENDPOINT),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    return _client


ANTI_THINK_PREFIX = (
    "/no_think\n"
    "Do not use <think> tags.\n"
    "Do not reason before responding.\n"
    "First token = your answer.\n\n"
)


def _prepend_anti_think(system: str) -> str:
    if system.startswith("/no_think"):
        return system
    return ANTI_THINK_PREFIX + system


def _llm_extra_body() -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if LLM_EXTRA_BODY:
        extra.update(json.loads(LLM_EXTRA_BODY))
    extra["enable_thinking"] = False
    extra.setdefault("chat_template_kwargs", {})["enable_thinking"] = False
    return extra


def strip_thinking(text: str) -> str:
    text = re.sub(
        rf"{re.escape(THINKING_OPEN)}.*?{re.escape(THINKING_CLOSE)}",
        "",
        text or "",
        flags=re.DOTALL,
    )
    return text.strip()


def _clean_content(content: str) -> str:
    return strip_thinking(content)


def _finalize_questioning_response(content: str, next_q: str) -> str:
    """Force questioning to ack + exact next question only."""
    q = next_q.strip()
    if not q.endswith("?"):
        q = f"{q}?"
    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", (content or "").strip()) if p.strip()]
    ack = sentences[0] if sentences else "I hear you."
    advice_markers = (
        "should", "need to", "lawyer", "insurance", "whiplash", "police",
        "state farm", "progressive", "don't agree", "file a", "claim", "fault",
    )
    if any(m in ack.lower() for m in advice_markers):
        ack = "I hear you."
    return f"{ack} {q}".strip()


def _enforce_questioning_no_advice(content: str, next_q: str) -> str:
    """Strip advice sentences from questioning responses; keep ack + question."""
    return _finalize_questioning_response(content, next_q)


def _enforce_questioning_brevity(content: str, next_q: str = "") -> str:
    """Keep questioning responses to two sentences."""
    if next_q:
        return _finalize_questioning_response(content, next_q)
    if not content:
        return content
    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", content.strip()) if p.strip()]
    if len(sentences) <= 2:
        return content.strip()
    question = next((s for s in reversed(sentences) if s.rstrip().endswith("?")), sentences[-1])
    return f"{sentences[0]} {question}".strip()


def _enforce_guiding_brevity(content: str, allow_four: bool = False, comprehensive: bool = False) -> str:
    """Keep guiding responses brief unless comprehensive first-guiding demo."""
    if comprehensive:
        return content.strip() if content else content
    if not content:
        return content

    max_sentences = 4 if allow_four else 3
    disclaimer = ""
    lower = content.lower()
    marker = "quick note — this is guidance"
    if marker in lower:
        idx = lower.index(marker)
        disclaimer = content[idx:].strip()
        content = content[:idx].strip()

    sentences = [p.strip() for p in re.split(r"(?<=[.!?])\s+", content.strip()) if p.strip()]
    if len(sentences) <= max_sentences:
        body = " ".join(sentences)
    else:
        question = next((s for s in reversed(sentences) if s.rstrip().endswith("?")), "")
        action = next(
            (
                s
                for s in sentences
                if re.search(r"\b(call|report|file|go to|get checked|don't|need to)\b", s, re.I)
            ),
            "",
        )
        ack = sentences[0]
        why = sentences[1] if len(sentences) > 1 else ""
        if action and question and why:
            body = f"{ack} {why} {question}"
        elif action and question:
            body = f"{action} {question}"
        elif action:
            body = f"{ack} {action}" if ack != action else action
        elif question:
            body = f"{ack} {question}" if ack != question else question
        else:
            body = " ".join(sentences[:max_sentences])

    if disclaimer:
        return f"{body.rstrip()} {disclaimer}".strip()
    return body.strip()


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def get_phase(history: list[dict]) -> str:
    turns = len(history) // 2
    if turns == 0:
        return "triage"
    if turns <= 2:
        return "gather"
    if turns <= 4:
        return "inform"
    return "summarize"


PHASE_MAX_TOKENS = {
    "triage": 60,
    "gather": 100,
    "inform": 100,
    "summarize": 150,
}

DISCLAIMER_TEXT = "Quick note — this is guidance, not legal advice."

GUIDING_PHASE_RULES = """GUIDING PHASE RULES:
After delivering one piece of guidance, end with ONE follow-up question.
The question fills remaining gaps and keeps the conversation going.

Example:
"State Farm will call within the hour. Say: 'I'm not giving a statement, please communicate in writing.'
Did you get a police report number?"

ONE urgent thing per turn, then ONE question. Maximum 3 sentences total."""

FIRST_GUIDING_RESPONSE_RULE = """
FIRST GUIDING RESPONSE RULE — THE DEMO MOMENT:
You now have the full picture. Deliver EVERYTHING Jake needs in ONE response.
Start with: "Okay — here's what matters." or "Okay — based on what you've told me..."

You MUST include ALL of these (weave naturally, not as a list):
1. State Farm will call within the hour — that's their playbook, not a coincidence
2. Exact words: "I'm not giving a recorded statement. Please communicate with me in writing." Then hang up.
3. In Texas, rear-end accidents are almost always the other driver's fault
4. Neck pain is whiplash until proven otherwise — go to the ER tonight
5. YOUR Progressive policy covers up to $10,000 in medical bills RIGHT NOW through MedPay — no waiting for State Farm
6. Don't say you're okay to anyone

Reference State Farm, Texas, neck/whiplash, and MedPay by name with specific numbers.
This is earned guidance — you listened for 5 turns. Make it land.
End with ONE short follow-up question if room allows.
"""

SETTLEMENT_TRIGGERS = [
    "case worth",
    "case actually worth",
    "what's it worth",
    "what is it worth",
    "how much",
    "settlement",
    "texted me",
    "offered me",
    "$4,000",
    "$4000",
    "4,000",
    "4000",
    "lowball",
    "take it",
    "should i take",
    "worth pursuing",
]

SETTLEMENT_GUIDANCE = """
SETTLEMENT OFFER RESPONSE (required):
Say "Don't take it." With a police report, documented whiplash, and an ER visit in Texas —
realistic range is $25,000 to $75,000. State Farm's first offer is always a fraction of actual value.
Most Texas attorneys work on contingency — free consultation, nothing upfront.
Reference the $4,000 as a lowball specifically if they mentioned it.
"""

QUESTIONING_PHASE_RULES = """
YOUR ONLY JOB RIGHT NOW:
Ask one question. Get one answer. Build the picture.

You are NOT allowed to give advice in questioning phase. Ever.
No legal information. No insurance information. No "here's what you should do."
No whiplash warnings. No police report tips. No carrier warnings. Just ask. Listen.

Question sequence (fill the next gap only):
1. Are you hurt?
2. Are you still at the scene?
3. What happened exactly?
4. Which state are you in?
5. Has anyone asked you to sign anything?
6. Was anyone else there who saw what happened?

Format EVERY response as exactly:
[One warm sentence acknowledging what they just said]
[One question to fill the next gap]

Example:
"Good that you can move. Are you still at the scene right now?"

NOT:
"Good that you can move. You should be careful about whiplash. Are you still at the scene?"
"""

PHASE_INSTRUCTIONS = {
    "triage": (
        "Current phase: triage. Max 3 sentences. "
        "Make them feel less alone. One gentle safety question. No legal or insurance info. No lists."
    ),
    "gather": (
        "Current phase: gather. Max 3 sentences. "
        "If they sound scared, acknowledge that first. "
        "If state law prefetch is provided, state the exact statute of limitations naturally "
        '(e.g. "In California you have two years to file"). '
        "If scene guidance is provided, give one warm practical tip. No lists."
    ),
    "inform": (
        "Current phase: inform. Max 4 sentences. "
        "ONE action OR ONE piece of information + ONE check-in question. "
        "Do not dump multiple steps — save the next thing for the next turn. No lists."
    ),
    "summarize": (
        "Current phase: summarize. Max 4 sentences. "
        "One priority only unless they asked for full recap — then still one item at a time. "
        "Connected prose — NEVER numbered lists or bullet points."
    ),
}

_state_prefetch_cache: dict[str, str] = {}

STATE_PATTERNS: list[tuple[str, str]] = [
    ("california", "California"),
    (" ca ", "California"),
    ("texas", "Texas"),
    (" tx ", "Texas"),
    ("new york", "New York"),
    (" ny ", "New York"),
    ("florida", "Florida"),
    (" fl ", "Florida"),
    ("illinois", "Illinois"),
    (" il ", "Illinois"),
    ("ohio", "Ohio"),
    (" oh ", "Ohio"),
    ("georgia", "Georgia"),
    (" ga ", "Georgia"),
    ("pennsylvania", "Pennsylvania"),
    (" pa ", "Pennsylvania"),
    ("arizona", "Arizona"),
    (" az ", "Arizona"),
    ("colorado", "Colorado"),
    (" co ", "Colorado"),
    ("washington", "Washington"),
    (" wa ", "Washington"),
    ("nevada", "Nevada"),
    (" nv ", "Nevada"),
    ("michigan", "Michigan"),
    (" mi ", "Michigan"),
]

INCIDENT_PATTERNS: list[tuple[str, str]] = [
    ("slip", "slip and fall"),
    ("fell", "slip and fall"),
    ("wet floor", "slip and fall"),
    ("grocery", "slip and fall"),
    ("dog bite", "dog bite"),
    ("dog", "dog bite"),
    ("car accident", "car accident"),
    ("crash", "car accident"),
    ("rear-end", "car accident"),
    ("workplace", "workplace injury"),
    ("at work", "workplace injury"),
    ("on the job", "workplace injury"),
    ("workers comp", "workplace injury"),
]

VALID_CLASSIFICATIONS = frozenset({
    "safety_check",
    "scene_guide",
    "moss_retrieval",
    "legal_tool",
    "insurance_tool",
    "none",
    "all",
})

INSURANCE_TRIGGERS = [
    "insurance", "cover", "coverage",
    "claim", "adjuster", "policy",
    "pay for", "will they pay",
    "who pays", "med pay", "deductible",
]

CARRIER_TRIGGERS = [
    "state farm",
    "allstate",
    "geico",
    "progressive",
    "farmers",
    "usaa",
    "liberty mutual",
    "travelers",
    "nationwide",
    "his insurance",
    "her insurance",
    "their insurance",
    "the other driver's insurance",
    "other driver's insurance",
]

LEGAL_TRIGGERS = [
    "lawyer", "attorney", "sue", "lawsuit",
    "legal", "rights", "liable", "liability",
    "fault", "negligence", "case",
    "settle", "settlement", "court",
]

SIGN_TRIGGERS = [
    "sign", "signing", "signature",
    "form", "document", "paper",
    "release", "waiver", "statement",
]

RESEARCH_TRIGGERS = [
    "what are my rights", "what can i do",
    "is this legal", "how much",
    "too late", "days ago", "already signed",
]

ADJUSTER_TRIGGERS = [
    "adjuster", "called me", "they called",
    "insurance company called",
    "recorded statement",
]

WHAT_ELSE_TRIGGERS = [
    "what else", "what now", "anything else",
    "what should i", "what do i do",
]

FOOTAGE_TRIGGERS = [
    "footage", "video", "security camera",
    "cctv", "recording", "surveillance",
]

RETALIATION_TRIGGERS = [
    "boss", "employer", "pressuring",
    "don't file", "not to file",
    "telling me not to",
    "workers comp", "work injury",
    "got hurt at work",
    "hurt at my job",
    "workplace",
]

GATHER_SCENE_KEYWORDS = [
    "photo", "picture", "photograph",
    "witness", "saw", "manager",
    "employee", "staff", "report",
]

_classification_cache: dict[str, tuple[str, bool]] = {}

INTENT_OVERRIDE_PROMPT = """
CURRENT MODE: DIRECT ANSWER REQUIRED
The user asked a direct question — answer it now, but ONE thing only. Then stop.

Do NOT give pure empathy without an answer.
Do NOT dump everything from the tool result — pick the ONE most urgent piece for THIS question.
Lead with ONE warm sentence, then answer directly in 2-3 sentences max. End with ONE check-in question.

Structure:
- 1 warm acknowledgment
- 1 specific answer (exact words to say if applicable)
- 1 question OR stop — do not add extra steps for future turns

Example for adjuster question:
"That call? Don't answer their questions. Say exactly: 'I'm not giving a statement right now. Please communicate with me in writing.' Did they already call?"

Example for lawyer question:
"Fair question — most injury lawyers work on contingency, so the consult is free and they only get paid if you win. Is your wrist still hurting today?"

Max 4 sentences. One idea. Then wait.
"""

POLICY_VOICE_INSTRUCTION = """
POLICY VOICE (required — user's OWN Progressive policy TX-2847-JAK-2024):
Speak as if reading their actual policy document from [moss_retrieval].
Use: "Based on your policy...", "Your coverage includes...", "According to your plan..."
Key facts: MedPay $10,000, collision $500 deductible, UM/UIM $100,000/$300,000,
Progressive claims 1-800-776-4737, policy number TX-2847-JAK-2024.
They opted OUT of PIP — use MedPay, NOT generic Texas PIP advice.
Do NOT say "typically", "you might have", "depending on your policy", or "likely includes".
Prefer [moss_retrieval] over [insurance_tool] generic text and over [state_law_prefetch].

When insurance_tool fires AND Moss returns policy details:
Lead with the user's own coverage.
Say "your policy" not "insurance."
Say "your MedPay" not "medical payments."
Reference specific numbers: $10,000 MedPay, $500 deductible.
Reference Progressive by name.
This feels personal and specific — NOT generic insurance advice.
"""

SUMMARIZE_NEARBY_PROMPT = """
The user has 5 urgent care facilities visible on their screen right now.
Include this naturally in your summary:

"Even if you feel okay right now — adrenaline is probably masking some of that — you need to get checked out today, not tomorrow. I've already pulled up the 5 nearest urgent care facilities on your screen. The closest one is open right now. Delayed treatment is the number one way insurance companies deny claims — don't give them that."
"""

RESPONSE_LENGTH_RULES = """
RESPONSE LENGTH — HARD LIMITS:
- Questioning phase: 2 sentences MAX
  Sentence 1: acknowledge what they said
  Sentence 2: ONE question
  Nothing else. Full stop.

- Guiding phase: 3 sentences MAX
  Sentence 1: the most important thing
  Sentence 2: why it matters
  Sentence 3: one question or next step
  Nothing else. Full stop.

- Summarize: 4 sentences MAX

If you feel the urge to say more:
Don't. The user will ask follow-up questions. Trust the conversation.
"""


def _build_state_injection(stack_data: dict) -> str:
    known: list[str] = []
    if stack_data.get("incident_type"):
        known.append(f"incident: {stack_data['incident_type']}")
    if stack_data.get("state"):
        known.append(f"state: {stack_data['state']}")
    if stack_data.get("injuries"):
        known.append(f"injuries: {stack_data['injuries']}")
    if stack_data.get("still_at_scene") is not None:
        known.append(f"at scene: {stack_data['still_at_scene']}")
    if stack_data.get("witnesses") is not None:
        known.append(f"witnesses: {stack_data['witnesses']}")
    if stack_data.get("signed_anything") is not None:
        known.append(f"signed: {stack_data['signed_anything']}")
    if stack_data.get("police_report"):
        known.append("police report: filed")
    if stack_data.get("store_name"):
        known.append(f"store: {stack_data['store_name']}")
    if stack_data.get("other_carrier"):
        known.append(f"other driver's insurance: {stack_data['other_carrier']}")

    known_str = (
        "What you know so far: " + ", ".join(known)
        if known
        else "What you know: nothing yet"
    )

    gaps: list[str] = []
    if stack_data.get("injuries") is None:
        gaps.append("injuries")
    if stack_data.get("state") is None:
        gaps.append("state/location")
    if stack_data.get("still_at_scene") is None:
        gaps.append("still at scene?")
    if stack_data.get("witnesses") is None and stack_data.get("turns", 0) > 2:
        gaps.append("witnesses")
    if stack_data.get("signed_anything") is None and stack_data.get("turns", 0) > 2:
        gaps.append("signed anything?")

    gaps_str = (
        "Still need to know: " + ", ".join(gaps[:2])
        if gaps
        else "You have enough context."
    )

    return f"""
{known_str}
{gaps_str}

USE THIS CONTEXT:
When you already know something — reference it directly.
"Since you're in Texas..."
"Given that your neck hurts..."
"You mentioned a witness nearby..."
NEVER ask about something you already know.
NEVER give information irrelevant to their specific situation.
"""


def _tools_fired_from_history(history: list[dict]) -> list[str]:
    """Infer which tools already ran from prior turns."""
    fired: list[str] = []
    turns = len(history) // 2
    if turns >= 1:
        fired.append("safety_check")
    if turns >= 2:
        fired.append("scene_guide")

    for msg in history:
        if msg.get("role") != "user":
            continue
        t = msg.get("text", "").lower()
        if any(w in t for w in INSURANCE_TRIGGERS) and "insurance_tool" not in fired:
            fired.append("insurance_tool")
        if any(w in t for w in LEGAL_TRIGGERS) and "legal_tool" not in fired:
            fired.append("legal_tool")
        if any(w in t for w in RESEARCH_TRIGGERS) and "moss_retrieval" not in fired:
            fired.append("moss_retrieval")
    return fired


def classify_tool(transcript: str, phase: str, context: dict) -> tuple[str, bool]:
    cache_key = f"{phase}:{transcript.strip().lower()}"
    if cache_key in _classification_cache:
        return _classification_cache[cache_key]

    t = transcript.lower()
    tools_fired = context.get("tools_fired", [])

    def _save(tool: str, override: bool) -> tuple[str, bool]:
        print(f"[ROUTER] {'intent override' if override else 'phase rule'}: {tool}")
        result = (tool, override)
        _classification_cache[cache_key] = result
        return result

    if any(w in t for w in SETTLEMENT_TRIGGERS):
        return _save("legal_tool", True)

    if any(w in t for w in OWN_POLICY_TRIGGERS):
        return _save("insurance_tool", True)

    if context.get("other_carrier") or any(c in t for c in CARRIER_TRIGGERS):
        return _save("insurance_tool", True)

    if any(w in t for w in FOOTAGE_TRIGGERS):
        return _save("moss_retrieval", True)

    if any(w in t for w in WHAT_ELSE_TRIGGERS):
        return _save("moss_retrieval", True)

    if any(w in t for w in RETALIATION_TRIGGERS):
        return _save("legal_tool", True)

    if any(w in t for w in INSURANCE_TRIGGERS):
        return _save("insurance_tool", True)

    if any(w in t for w in LEGAL_TRIGGERS):
        return _save("legal_tool", True)

    if any(w in t for w in SIGN_TRIGGERS):
        return _save("scene_guide", True)

    if any(w in t for w in ADJUSTER_TRIGGERS):
        return _save("insurance_tool", True)

    if any(w in t for w in RESEARCH_TRIGGERS):
        return _save("moss_retrieval", True)

    if phase == "triage":
        return _save("safety_check", False)

    if phase == "gather":
        if any(w in t for w in GATHER_SCENE_KEYWORDS):
            return _save("scene_guide", False)
        if "scene_guide" not in tools_fired:
            return _save("scene_guide", False)
        return _save("none", False)

    if phase == "inform":
        if "legal_tool" not in tools_fired:
            return _save("legal_tool", False)
        if "insurance_tool" not in tools_fired:
            return _save("insurance_tool", False)
        return _save("moss_retrieval", False)

    if phase == "summarize":
        return _save("all", False)

    return _save("safety_check", False)


def _tool_spec(
    name: str,
    context: dict,
    transcript: str,
    phase: str = "",
    planned_tools: list[str] | None = None,
) -> dict[str, Any]:
    if name == "moss_retrieval":
        moss_context = dict(context)
        planned = [t for t in (planned_tools or []) if t != "moss_retrieval"]
        fired = list(context.get("tools_fired") or [])
        for t in planned:
            if t not in fired:
                fired.append(t)
        moss_context["tools_fired"] = fired
        if "insurance_tool" in planned or any(
            w in transcript.lower() for w in OWN_POLICY_TRIGGERS
        ):
            moss_context["policy_moss"] = True
        return {
            "name": name,
            "arguments": {
                "transcript": transcript,
                "context": moss_context,
                "phase": phase,
            },
        }
    if name in ("legal_tool", "insurance_tool"):
        return {
            "name": name,
            "arguments": {
                "incident_type": context.get("incident_type") or "general",
                "state": context.get("state") or "unknown",
            },
        }
    return {"name": name, "arguments": {}}


def tools_from_classification(
    phase: str,
    transcript: str,
    context: dict,
    classified: str,
    intent_override: bool = False,
) -> list[dict[str, Any]]:
    state = context.get("state") or "unknown"
    incident = context.get("incident_type") or "general"
    _ = state, incident
    has_prefetch = bool(context.get("prefetched_state_law"))

    if intent_override and classified in ("legal_tool", "insurance_tool", "moss_retrieval"):
        if classified == "legal_tool":
            names = ["legal_tool"] if has_prefetch else ["legal_tool", "moss_retrieval"]
        elif classified == "insurance_tool":
            names = ["insurance_tool", "moss_retrieval"]
        else:
            names = ["moss_retrieval"]
        return [_tool_spec(n, context, transcript, phase, names) for n in names]

    if intent_override and classified == "scene_guide":
        names = ["scene_guide", "moss_retrieval"] if "signed" in transcript.lower() else ["scene_guide"]
        return [_tool_spec(n, context, transcript, phase, names) for n in names]

    if phase in ("triage", "gather"):
        if classified in ("none", "all") or classified not in TOOL_RUNNERS:
            return []
        return [_tool_spec(classified, context, transcript, phase, [classified])]

    if phase == "inform":
        if classified == "legal_tool":
            names = ["legal_tool"] if has_prefetch else ["legal_tool", "moss_retrieval"]
        elif classified == "insurance_tool":
            names = ["insurance_tool", "moss_retrieval"]
        elif classified == "moss_retrieval":
            names = ["moss_retrieval", "legal_tool"]
        elif classified in TOOL_RUNNERS:
            names = [classified]
        else:
            names = ["legal_tool", "insurance_tool"]
            if not has_prefetch:
                names.append("moss_retrieval")
        return [_tool_spec(n, context, transcript, phase, names) for n in names]

    if phase == "summarize" or classified == "all":
        names = ["legal_tool", "insurance_tool"]
        if not has_prefetch:
            names.append("moss_retrieval")
        if classified == "scene_guide":
            names.append("scene_guide")
        return [_tool_spec(n, context, transcript, phase, names) for n in names]

    return []


def _conversation_text(transcript: str, history: list[dict]) -> str:
    parts = [msg.get("text", "") for msg in history if msg.get("text")]
    parts.append(transcript)
    return " ".join(parts).lower()


def extract_context(transcript: str, history: list[dict], existing: dict | None = None) -> dict:
    context: dict[str, Any] = {
        "state": None,
        "incident_type": None,
        "signed_anything": False,
        "injury_severity": None,
        "witnesses": False,
        "disclaimer_given": False,
        "prefetched_state_law": None,
        "tools_fired": [],
    }
    if existing:
        context.update(existing)

    context["tools_fired"] = _tools_fired_from_history(history)

    text = f" {_conversation_text(transcript, history)} "

    for pattern, state in STATE_PATTERNS:
        if pattern in text:
            context["state"] = state
            break

    if not context.get("state") and (
        "whole foods" in text or "san francisco" in text
    ):
        context["state"] = "California"

    if "whole foods" in text:
        context["demo_store"] = "Whole Foods"
    if "zurich" in text:
        context["demo_insurer"] = "Zurich"

    for pattern, incident in INCIDENT_PATTERNS:
        if pattern in text:
            context["incident_type"] = incident
            break

    if any(k in text for k in ("signed", "sign the", "signing", "made me sign", "waiver")):
        context["signed_anything"] = True
    if any(k in text for k in ("witness", "saw it", "someone saw", "bystander", "people saw")):
        context["witnesses"] = True

    if any(k in text for k in ("911", "ambulance", "unconscious", "can't move", "cant move", "head injury", "bleeding badly")):
        context["injury_severity"] = "serious"
    elif any(k in text for k in ("911", "severe", "broken", "surgery", "emergency room")):
        context["injury_severity"] = "serious"
    elif any(k in text for k in ("hurt", "pain", "sprain", "wrist", "ankle", "bruised")):
        context["injury_severity"] = context.get("injury_severity") or "moderate"
    elif any(k in text for k in ("fine", "okay", "ok", "minor", "small bruise", "just a bruise")):
        context["injury_severity"] = context.get("injury_severity") or "mild"

    context["disclaimer_given"] = any(
        msg.get("role") == "assistant"
        and (
            "not legal advice" in msg.get("text", "").lower()
            or "this is guidance" in msg.get("text", "").lower()
        )
        for msg in history
    )

    state = context.get("state")
    if state and state in _state_prefetch_cache:
        context["prefetched_state_law"] = _state_prefetch_cache[state]

    return context


def _build_system_prompt(
    phase: str,
    context: dict,
    tool_names: list[str] | None = None,
    *,
    intent_override: bool = False,
    tool_name: str | None = None,
    incident_guiding: bool = False,
    first_guiding: bool = False,
) -> str:
    base = _load_system_prompt()
    context_line = f"Collected context so far: {json.dumps({k: v for k, v in context.items() if k != 'prefetched_state_law'})}"

    direct_answer_tools = {"legal_tool", "insurance_tool", "moss_retrieval", "scene_guide"}
    if intent_override and tool_name in direct_answer_tools and not first_guiding:
        phase_line = INTENT_OVERRIDE_PROMPT
    else:
        phase_line = PHASE_INSTRUCTIONS[phase]

    legal_tool_fired = tool_names and "legal_tool" in tool_names
    if legal_tool_fired and not context.get("disclaimer_given"):
        disclaimer_line = (
            f"Include this disclaimer once at the very end: \"{DISCLAIMER_TEXT}\""
        )
    else:
        disclaimer_line = "Do NOT include any legal disclaimer in this response."

    nearby_line = ""
    if phase == "summarize":
        nearby_line = SUMMARIZE_NEARBY_PROMPT

    guiding_line = ""
    if incident_guiding:
        if first_guiding:
            guiding_line = f"\n\n{FIRST_GUIDING_RESPONSE_RULE}"
        else:
            guiding_line = f"\n\n{GUIDING_PHASE_RULES}"

    stack_data = context.get("incident_stack") or {}
    state_injection = _build_state_injection(stack_data) if stack_data else ""

    carrier = context.get("other_carrier") or stack_data.get("other_carrier") or ""
    carrier_note = ""
    if incident_guiding and carrier:
        carrier_note = f"""
CARRIER ALERT: The other driver has {carrier} insurance.

{carrier} will call within 1 hour.
Warn the user about this specifically.
Tell them exactly what to say.
Reference {carrier} by name.
Don't say "their insurance" — say "{carrier}."
"""

    return _prepend_anti_think(
        f"{base}\n\n{RESPONSE_LENGTH_RULES}\n\n{phase_line}{guiding_line}"
        f"{carrier_note}{state_injection}\n{context_line}\n{disclaimer_line}\n{nearby_line}"
    )


async def _prefetch_state_law(
    phase: str,
    context: dict,
    profiler: LatencyProfiler | None = None,
) -> None:
    state = context.get("state")
    if not state:
        return
    if state in _state_prefetch_cache:
        context["prefetched_state_law"] = _state_prefetch_cache[state]
        return

    query = f"{state} personal injury statute of limitations"
    if profiler:
        profiler.mark("moss_search_start")
    result = await asyncio.to_thread(moss_retrieval_run, query)
    if profiler:
        profiler.mark("moss_search_done")
    _state_prefetch_cache[state] = result
    context["prefetched_state_law"] = result


def _build_messages(
    transcript: str,
    conversation_history: list[dict],
    phase: str,
    context: dict,
    tool_results: list[tuple[str, str]] | None = None,
    intent_override: bool = False,
    tool_name: str | None = None,
    incident_guiding: bool = False,
    first_guiding: bool = False,
) -> list[dict]:
    tool_names = [name for name, _ in tool_results] if tool_results else []
    messages: list[dict] = [
        {
            "role": "system",
            "content": _build_system_prompt(
                phase,
                context,
                tool_names,
                intent_override=intent_override,
                tool_name=tool_name,
                incident_guiding=incident_guiding,
                first_guiding=first_guiding,
            ),
        }
    ]
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["text"]})
    messages.append({"role": "user", "content": transcript})

    guidance_parts: list[str] = []
    if intent_override:
        guidance_parts.append(
            "CRITICAL: Answer their direct question now using the guidance below. "
            "Do not deflect to safety-only triage."
        )
    tool_names_list = [name for name, _ in tool_results] if tool_results else []
    if tool_name == "insurance_tool" or "insurance_tool" in tool_names_list:
        guidance_parts.append(POLICY_VOICE_INSTRUCTION)
    if any(w in transcript.lower() for w in SETTLEMENT_TRIGGERS):
        guidance_parts.append(SETTLEMENT_GUIDANCE)
    if context.get("prefetched_state_law"):
        guidance_parts.append(
            f"[state_law_prefetch]\n{context['prefetched_state_law']}"
        )
    demo_guidance = get_demo_guidance(transcript, context, phase)
    if demo_guidance:
        guidance_parts.append(f"[demo_scenario]\n{demo_guidance}")
    if tool_results:
        ordered = sorted(
            tool_results,
            key=lambda pair: 0 if pair[0] == "moss_retrieval" else 1,
        )
        guidance_parts.extend(f"[{name}]\n{result}" for name, result in ordered)

    if guidance_parts:
        messages.append(
            {
                "role": "system",
                "content": _prepend_anti_think(
                    "Internal guidance (use naturally in your response, never mention tools or retrieval):\n"
                    + "\n\n".join(guidance_parts)
                ),
            }
        )
    return messages


async def _run_programmatic_tools(
    tools: list[dict[str, Any]], profiler: LatencyProfiler | None = None
) -> list[tuple[str, str]]:
    if not tools:
        return []

    async def run_one(spec: dict[str, Any]) -> tuple[str, str]:
        name = spec["name"]
        args = spec.get("arguments", {})
        if profiler:
            profiler.mark(f"{name}_start")
        result = await asyncio.to_thread(_execute_tool, name, json.dumps(args))
        if profiler:
            profiler.mark(f"{name}_done")
        return name, result

    return list(await asyncio.gather(*[run_one(t) for t in tools]))


def _create_completion(
    client: OpenAI,
    messages: list[dict],
    *,
    stream: bool,
    use_tools: bool = True,
    max_tokens: int = 400,
    temperature: float = 0.0,
):
    if not LLM_MODEL:
        raise ValueError("LLM_MODEL is not set in .env")
    kwargs: dict[str, Any] = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
        "timeout": LLM_TIMEOUT_SECONDS,
    }
    if use_tools:
        kwargs["tools"] = TOOL_DEFINITIONS
    kwargs["extra_body"] = _llm_extra_body()
    return client.chat.completions.create(**kwargs)


def _stream_llm(
    client: OpenAI,
    messages: list[dict],
    *,
    emit_tokens: bool = True,
    use_tools: bool = False,
    max_tokens: int = 400,
    temperature: float = 0.0,
) -> Iterator[tuple[str, str | Any]]:
    try:
        stream = _create_completion(
            client,
            messages,
            stream=True,
            use_tools=use_tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except (APITimeoutError, RateLimitError, APIStatusError):
        yield ("timeout", None)
        return

    content_parts: list[str] = []
    tool_calls_acc: dict[int, dict] = {}
    content_filter = _StreamContentFilter()

    try:
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                visible = content_filter.feed(delta.content)
                if visible:
                    content_parts.append(visible)
                    if emit_tokens:
                        yield ("token", visible)
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    _accumulate_tool_calls(tool_calls_acc, tool_call_delta)
    except (APITimeoutError, RateLimitError, APIStatusError):
        yield ("timeout", None)
        return

    assistant_message = _build_assistant_message(
        strip_thinking("".join(content_parts)), tool_calls_acc
    )
    yield ("message", assistant_message)


def _message_to_dict(message: Any) -> dict:
    data: dict[str, Any] = {"role": message.role, "content": message.content or ""}
    if message.tool_calls:
        data["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ]
    if getattr(message, "reasoning_details", None):
        data["reasoning_details"] = message.reasoning_details
    return data


def _execute_tool(name: str, arguments: str) -> str:
    args = json.loads(arguments) if arguments else {}
    runner = TOOL_RUNNERS.get(name)
    if not runner:
        return f"Unknown tool: {name}"
    return runner(args)


async def _execute_tools_parallel(
    tool_calls: list[Any], profiler: LatencyProfiler | None = None
) -> list[tuple[str, str, str]]:
    async def run_one(tool_call: Any) -> tuple[str, str, str]:
        name = tool_call.function.name
        arguments = tool_call.function.arguments
        if name == "moss_retrieval" and profiler:
            profiler.mark("moss_search_start")
        result = await asyncio.to_thread(_execute_tool, name, arguments)
        if name == "moss_retrieval" and profiler:
            profiler.mark("moss_search_done")
        return tool_call.id, name, result

    return list(await asyncio.gather(*[run_one(tc) for tc in tool_calls]))


def _accumulate_tool_calls(tool_calls_acc: dict[int, dict], tool_call_delta: Any) -> None:
    idx = tool_call_delta.index
    if idx not in tool_calls_acc:
        tool_calls_acc[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
    entry = tool_calls_acc[idx]
    if tool_call_delta.id:
        entry["id"] = tool_call_delta.id
    if tool_call_delta.function:
        if tool_call_delta.function.name:
            entry["function"]["name"] = tool_call_delta.function.name
        if tool_call_delta.function.arguments:
            entry["function"]["arguments"] += tool_call_delta.function.arguments


def _build_assistant_message(content: str, tool_calls_acc: dict[int, dict]) -> Any:
    class Function:
        def __init__(self, name: str, arguments: str):
            self.name = name
            self.arguments = arguments

    class ToolCall:
        def __init__(self, id: str, name: str, arguments: str):
            self.id = id
            self.type = "function"
            self.function = Function(name, arguments)

    class AssistantMessage:
        def __init__(self, content: str, tool_calls: list[ToolCall] | None):
            self.role = "assistant"
            self.content = content
            self.tool_calls = tool_calls
            self.reasoning_details = None

    tool_calls = None
    if tool_calls_acc:
        tool_calls = [
            ToolCall(
                tc["id"],
                tc["function"]["name"],
                tc["function"]["arguments"],
            )
            for _, tc in sorted(tool_calls_acc.items())
            if tc["function"]["name"]
        ]
    return AssistantMessage(content, tool_calls or None)


def _route_tools(client: OpenAI, messages: list[dict]) -> Any | None:
    """Non-streaming tool-routing call — reliable tool_calls on all providers."""
    try:
        response = _create_completion(client, messages, stream=False, use_tools=True)
        return _coerce_tool_calls(response.choices[0].message)
    except (APITimeoutError, RateLimitError, APIStatusError):
        return None


def _coerce_tool_calls(message: Any) -> Any:
    """Some models (e.g. llama-3.1-8b) emit <tool_name></tool_name> instead of tool_calls."""
    if message.tool_calls:
        return message
    if not message.content:
        return message

    match = re.match(r"^\s*<(\w+)>\s*(?:</\1>\s*)?$", message.content.strip())
    if not match or match.group(1) not in TOOL_RUNNERS:
        return message

    tool_name = match.group(1)

    class Function:
        def __init__(self, name: str):
            self.name = name
            self.arguments = "{}"

    class ToolCall:
        def __init__(self, name: str):
            self.id = f"call_{name}"
            self.type = "function"
            self.function = Function(name)

    message.content = ""
    message.tool_calls = [ToolCall(tool_name)]
    return message


def _call_llm(
    client: OpenAI,
    messages: list[dict],
    *,
    use_tools: bool = False,
    max_tokens: int = 400,
    temperature: float = 0.0,
) -> Any | None:
    tokens: list[str] = []
    assistant_message = None

    for event_type, payload in _stream_llm(
        client,
        messages,
        use_tools=use_tools,
        max_tokens=max_tokens,
        temperature=temperature,
    ):
        if event_type == "timeout":
            return None
        if event_type == "token":
            tokens.append(payload)
        elif event_type == "message":
            assistant_message = payload

    if assistant_message is None:
        return None
    if tokens and not assistant_message.content:
        assistant_message.content = "".join(tokens)
    return assistant_message


def _tool_reasoning(tool_names: list[str]) -> str:
    if len(tool_names) == 1:
        return f"Selected {tool_names[0]} based on user situation"
    return f"Selected {', '.join(tool_names)} based on user situation"


def _extract_reasoning(message: Any, fallback: str | None) -> str | None:
    if fallback:
        return fallback
    if getattr(message, "reasoning_details", None):
        return str(message.reasoning_details)[:300]
    return None


def _phase_reasoning(phase: str, tool_names: list[str]) -> str:
    if tool_names:
        return f"Phase {phase}: {', '.join(tool_names)}"
    return f"Phase {phase}: conversational"


def _append_disclaimer_if_needed(
    content: str,
    phase: str,
    context: dict,
    tool_results: list[tuple[str, str]],
) -> str:
    legal_tool_fired = any(name == "legal_tool" for name, _ in tool_results)
    if (
        not legal_tool_fired
        or context.get("disclaimer_given")
        or "not legal advice" in content.lower()
        or "this is guidance" in content.lower()
    ):
        return content
    context["disclaimer_given"] = True
    return f"{content.rstrip()} {DISCLAIMER_TEXT}"


def _stack_summary_block(stack: IncidentStack) -> str:
    d = stack.data
    return (
        "WHAT YOU KNOW ABOUT THIS PERSON:\n"
        f"Incident: {d.get('incident_type')}\n"
        f"Location: {d.get('state')}\n"
        f"Store: {d.get('store_name')}\n"
        f"Injuries: {d.get('injuries')}\n"
        f"Still at scene: {d.get('still_at_scene')}\n"
        f"Signed anything: {d.get('signed_anything')}\n"
        f"Witnesses: {d.get('witnesses')}\n"
        f"Photos taken: {d.get('photos_taken')}\n"
        f"Police called: {d.get('called_911')}\n"
        f"Owner/driver fled: {d.get('driver_fled')}\n\n"
        "Use this context to give SPECIFIC advice. Not generic. Their exact situation."
    )


def _build_questioning_messages(
    stack: IncidentStack,
    next_q: str,
    history: list[dict],
    transcript: str,
) -> list[dict]:
    state_injection = _build_state_injection(stack.data)
    system = _prepend_anti_think(f"""You are What Now — a calm warm voice assistant for people who just got hurt.

{QUESTIONING_PHASE_RULES}

{RESPONSE_LENGTH_RULES}

Your job this turn — ask ONLY this question next:
"{next_q}"

Two sentences maximum: one acknowledgment, one question. Nothing else.
{state_injection}
""")
    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["text"]})
    messages.append({"role": "user", "content": transcript})
    return messages


async def _questioning_turn(
    transcript: str,
    history: list[dict],
    stack: IncidentStack,
    profiler: LatencyProfiler,
) -> dict:
    next_q = get_next_question(stack) or "Can you tell me a bit more about what happened?"
    messages = _build_questioning_messages(stack, next_q, history, transcript)
    client = _get_client()

    profiler.mark("first_llm_call_start")
    final_message = await asyncio.to_thread(
        _call_llm,
        client,
        messages,
        use_tools=False,
        max_tokens=60,
        temperature=0.3,
    )
    profiler.mark("first_llm_call_done")

    if final_message is None:
        profiler.mark("response_complete")
        return {
            "response": FALLBACK_RESPONSE,
            "tool_called": None,
            "reasoning": f"Questioning: filling gap '{next_q}'",
            "phase": "questioning",
            "context": stack.data,
            "profile": profiler.checkpoints,
        }

    content = strip_thinking(final_message.content or "")
    content = _enforce_questioning_no_advice(content, next_q)
    content = _enforce_questioning_brevity(content, next_q)
    if content:
        profiler.mark("first_token_streamed")
        profiler.mark("last_token_streamed")

    profiler.mark("response_complete")
    return {
        "response": content or FALLBACK_RESPONSE,
        "tool_called": None,
        "reasoning": f"Questioning: filling gap '{next_q}'",
        "phase": "questioning",
        "context": stack.data,
        "profile": profiler.checkpoints,
    }


async def _questioning_turn_stream(
    transcript: str,
    history: list[dict],
    stack: IncidentStack,
    profiler: LatencyProfiler,
) -> AsyncIterator[dict[str, Any]]:
    next_q = get_next_question(stack) or "Can you tell me a bit more about what happened?"
    messages = _build_questioning_messages(stack, next_q, history, transcript)
    client = _get_client()

    response_parts: list[str] = []
    first_token_marked = False
    final_message = None

    profiler.mark("first_llm_call_start")
    for event_type, payload in _stream_llm(
        client,
        messages,
        emit_tokens=True,
        use_tools=False,
        max_tokens=60,
        temperature=0.3,
    ):
        if event_type == "token":
            if not first_token_marked:
                profiler.mark("first_token_streamed")
                first_token_marked = True
            response_parts.append(payload)
            yield {"type": "token", "content": payload}
        elif event_type == "message":
            final_message = payload
    profiler.mark("first_llm_call_done")

    content = strip_thinking(
        "".join(response_parts) or ((final_message.content or "") if final_message else "")
    )
    content = _enforce_questioning_no_advice(content, next_q)
    content = _enforce_questioning_brevity(content, next_q)
    if first_token_marked:
        profiler.mark("last_token_streamed")

    profiler.mark("response_complete")
    profile = profiler.report()
    yield {
        "type": "done",
        "response": content or FALLBACK_RESPONSE,
        "tool_called": None,
        "reasoning": f"Questioning: filling gap '{next_q}'",
        "phase": "questioning",
        "context": stack.data,
        "latency_ms": profile[-1]["ms"] if profile else 0,
        "profile": profile,
    }


async def _run_agent_turn(
    transcript: str,
    history: list[dict],
    session_id: str,
    profiler: LatencyProfiler,
    context: dict[str, Any] | None = None,
) -> dict:
    stack = get_or_create_stack(session_id, context)
    if transcript.strip() and transcript != "__START__":
        stack.update_from_transcript(transcript)
        profiler.mark("stack_update")

    if not stack.is_ready_to_guide() and not stack.needs_immediate_medical():
        stack.data["phase"] = "questioning"
        return await _questioning_turn(transcript, history, stack, profiler)

    first_guiding = not stack.data.get("has_guided")
    stack.data["phase"] = "guiding"
    result = await _run_phase_loop(
        transcript, history, profiler, stack=stack, first_guiding=first_guiding
    )
    stack.data["has_guided"] = True
    stack.sync_from_agent_context(result["context"])
    result["context"] = stack.data
    result["phase"] = "guiding"
    return result


async def _run_agent_turn_stream(
    transcript: str,
    history: list[dict],
    session_id: str,
    profiler: LatencyProfiler,
    context: dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    stack = get_or_create_stack(session_id, context)
    if transcript.strip() and transcript != "__START__":
        stack.update_from_transcript(transcript)

    if not stack.is_ready_to_guide() and not stack.needs_immediate_medical():
        stack.data["phase"] = "questioning"
        async for event in _questioning_turn_stream(transcript, history, stack, profiler):
            yield event
        return

    stack.data["phase"] = "guiding"
    first_guiding = not stack.data.get("has_guided")
    async for event in _run_phase_loop_stream(
        transcript, history, profiler, stack=stack, first_guiding=first_guiding
    ):
        if event.get("type") == "done":
            ctx = event.get("context") or {}
            stack.sync_from_agent_context(ctx)
            stack.data["has_guided"] = True
            event["context"] = stack.data
            event["phase"] = "guiding"
        yield event


async def _prepare_phase_run(
    transcript: str,
    history: list[dict],
    profiler: LatencyProfiler,
    stack: IncidentStack | None = None,
    first_guiding: bool = False,
) -> tuple[str, dict, list[dict], int, str | None, str, list[tuple[str, str]]]:
    phase = get_phase(history)
    if stack is not None:
        context = stack.to_agent_context()
        fresh = extract_context(transcript, history)
        for key in (
            "state",
            "signed_anything",
            "witnesses",
            "injury_severity",
            "incident_type",
            "demo_store",
            "demo_insurer",
        ):
            if fresh.get(key) and not context.get(key):
                context[key] = fresh[key]
        for tool in fresh.get("tools_fired") or []:
            if tool not in context["tools_fired"]:
                context["tools_fired"].append(tool)
    else:
        context = extract_context(transcript, history)

    profiler.mark("tool_classification_start")
    if first_guiding and stack is not None:
        classified, intent_override = "insurance_tool", True
        print("[ROUTER] first guiding bundle: insurance_tool + moss + legal_tool")
    else:
        classified, intent_override = await asyncio.to_thread(
            classify_tool, transcript, phase, context
        )
    profiler.mark("tool_classification_done")

    skip_state_prefetch = intent_override and classified == "insurance_tool" and not first_guiding

    if context.get("state") and not skip_state_prefetch and (
        phase in ("gather", "inform", "summarize") or intent_override or first_guiding
    ):
        await _prefetch_state_law(phase, context, profiler)

    if first_guiding and stack is not None:
        bundle = ["insurance_tool", "moss_retrieval", "legal_tool"]
        tool_specs = [_tool_spec(n, context, transcript, phase, bundle) for n in bundle]
    else:
        tool_specs = tools_from_classification(
            phase, transcript, context, classified, intent_override
        )
    profiler.mark("tool_decision_made")
    tool_results: list[tuple[str, str]] = []
    if tool_specs:
        profiler.mark("tool_execution_start")
        tool_results = await _run_programmatic_tools(tool_specs, profiler)
        profiler.mark("tool_execution_done")
        fired = list(context.get("tools_fired") or [])
        for name, _ in tool_results:
            if name not in fired:
                fired.append(name)
        context["tools_fired"] = fired

    if (
        context.get("state")
        and not skip_state_prefetch
        and not context.get("prefetched_state_law")
        and phase in ("gather", "inform", "summarize")
    ):
        await _prefetch_state_law(phase, context, profiler)

    messages = _build_messages(
        transcript,
        history,
        phase,
        context,
        tool_results,
        intent_override=intent_override,
        tool_name=classified,
        incident_guiding=stack is not None,
        first_guiding=first_guiding,
    )
    if stack is not None and stack.needs_immediate_medical():
        messages[0]["content"] += (
            "\n\nMEDICAL URGENCY: Lead with ONE urgent medical action "
            "(ER or urgent care today). Dog bites and serious injuries "
            "need professional evaluation now."
        )
    context["intent_override"] = intent_override
    override_tools = {"legal_tool", "insurance_tool", "moss_retrieval", "scene_guide"}
    max_tokens = (
        PHASE_MAX_TOKENS["inform"]
        if intent_override and classified in override_tools
        else PHASE_MAX_TOKENS[phase]
    )
    tool_called = tool_results[0][0] if tool_results else None
    reasoning = _phase_reasoning(phase, [name for name, _ in tool_results])
    if stack is not None:
        max_tokens = 150 if phase == "summarize" else (220 if first_guiding else 100)
    if intent_override:
        reasoning = f"Intent override: {classified} → {', '.join(n for n, _ in tool_results) or classified}"
    elif classified != "none" and not tool_results:
        reasoning = f"Phase {phase}: classified {classified}, conversational"
    elif classified != "none":
        reasoning = f"Phase {phase}: classified {classified} → {', '.join(n for n, _ in tool_results)}"

    return phase, context, messages, max_tokens, tool_called, reasoning, tool_results


async def _run_phase_loop(
    transcript: str,
    history: list[dict],
    profiler: LatencyProfiler,
    stack: IncidentStack | None = None,
    first_guiding: bool = False,
) -> dict:
    client = _get_client()
    phase, context, messages, max_tokens, tool_called, reasoning, tool_results = await _prepare_phase_run(
        transcript, history, profiler, stack=stack, first_guiding=first_guiding
    )

    if first_guiding and stack is not None:
        jake_response = get_jake_first_guiding_response(context)
        if jake_response:
            profiler.mark("response_complete")
            return {
                "response": jake_response,
                "tool_called": tool_called,
                "reasoning": reasoning,
                "phase": phase,
                "context": context,
                "profile": profiler.checkpoints,
            }

    if any(w in transcript.lower() for w in SETTLEMENT_TRIGGERS):
        jake_settlement = get_jake_settlement_response(context)
        if jake_settlement:
            content = _append_disclaimer_if_needed(jake_settlement, phase, context, tool_results)
            profiler.mark("response_complete")
            return {
                "response": content,
                "tool_called": tool_called or "legal_tool",
                "reasoning": reasoning,
                "phase": phase,
                "context": context,
                "profile": profiler.checkpoints,
            }

    profiler.mark("first_llm_call_start")
    final_message = await asyncio.to_thread(
        _call_llm, client, messages, use_tools=False, max_tokens=max_tokens
    )
    profiler.mark("first_llm_call_done")

    if final_message is None:
        profiler.mark("response_complete")
        return {
            "response": FALLBACK_RESPONSE,
            "tool_called": tool_called,
            "reasoning": reasoning,
            "phase": phase,
            "context": context,
            "profile": profiler.checkpoints,
        }

    content = strip_thinking(final_message.content or "")
    content = _append_disclaimer_if_needed(content, phase, context, tool_results)
    if stack is not None:
        content = _enforce_guiding_brevity(content, allow_four=first_guiding, comprehensive=first_guiding)
    if content:
        profiler.mark("first_token_streamed")
        profiler.mark("last_token_streamed")

    profiler.mark("response_complete")
    return {
        "response": content or FALLBACK_RESPONSE,
        "tool_called": tool_called,
        "reasoning": reasoning,
        "phase": phase,
        "context": context,
        "profile": profiler.checkpoints,
    }


def run_agent_sync(
    transcript: str,
    conversation_history: list[dict],
    profiler: LatencyProfiler | None = None,
    session_id: str = "",
) -> dict:
    """Sync wrapper for scripts; prefer async run_agent in FastAPI."""
    if profiler is None:
        profiler = LatencyProfiler()
        profiler.mark("request_received")
    profiler.mark("messages_built")
    result = asyncio.run(
        _run_agent_turn(transcript, conversation_history, session_id, profiler)
    )
    profiler.report()
    return result


async def run_agent(
    transcript: str,
    conversation_history: list[dict],
    profiler: LatencyProfiler | None = None,
    session_id: str = "",
    context: dict[str, Any] | None = None,
) -> dict:
    if profiler is None:
        profiler = LatencyProfiler()
        profiler.mark("request_received")
    profiler.mark("messages_built")
    result = await _run_agent_turn(
        transcript, conversation_history, session_id, profiler, context
    )
    profiler.report()
    return result


async def _run_phase_loop_stream(
    transcript: str,
    history: list[dict],
    profiler: LatencyProfiler,
    stack: IncidentStack | None = None,
    first_guiding: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    client = _get_client()
    phase, context, messages, max_tokens, tool_called, reasoning, tool_results = await _prepare_phase_run(
        transcript, history, profiler, stack=stack, first_guiding=first_guiding
    )

    if first_guiding and stack is not None:
        jake_response = get_jake_first_guiding_response(context)
        if jake_response:
            profiler.mark("response_complete")
            profile = profiler.report()
            yield {
                "type": "done",
                "response": jake_response,
                "tool_called": tool_called,
                "reasoning": reasoning,
                "phase": phase,
                "context": context,
                "latency_ms": profile[-1]["ms"] if profile else 0,
                "profile": profile,
            }
            return

    if any(w in transcript.lower() for w in SETTLEMENT_TRIGGERS):
        jake_settlement = get_jake_settlement_response(context)
        if jake_settlement:
            content = _append_disclaimer_if_needed(jake_settlement, phase, context, tool_results)
            profiler.mark("response_complete")
            profile = profiler.report()
            yield {
                "type": "done",
                "response": content,
                "tool_called": tool_called or "legal_tool",
                "reasoning": reasoning,
                "phase": phase,
                "context": context,
                "latency_ms": profile[-1]["ms"] if profile else 0,
                "profile": profile,
            }
            return

    response_parts: list[str] = []
    first_token_marked = False
    final_message = None

    for attempt in range(2):
        response_parts = []
        first_token_marked = False
        final_message = None
        if attempt:
            profiler.mark("llm_retry_start")

        profiler.mark("first_llm_call_start")
        timed_out = False
        for event_type, payload in _stream_llm(
            client, messages, emit_tokens=True, use_tools=False, max_tokens=max_tokens
        ):
            if event_type == "timeout":
                timed_out = True
                break
            if event_type == "token":
                if not first_token_marked:
                    profiler.mark("first_token_streamed")
                    first_token_marked = True
                response_parts.append(payload)
                yield {"type": "token", "content": payload}
            elif event_type == "message":
                final_message = payload
        profiler.mark("first_llm_call_done")

        content = strip_thinking(
            "".join(response_parts) or ((final_message.content or "") if final_message else "")
        )
        if not timed_out and final_message is not None and content:
            break

    if final_message is None and not response_parts:
        demo_reply = get_demo_fallback_response(transcript, context, phase)
        if demo_reply:
            profiler.mark("response_complete")
            profile = profiler.report()
            yield {
                "type": "done",
                "response": demo_reply,
                "tool_called": tool_called,
                "reasoning": reasoning,
                "phase": phase,
                "context": context,
                "latency_ms": profile[-1]["ms"] if profile else 0,
                "profile": profile,
            }
            return
        profiler.mark("response_complete")
        profile = profiler.report()
        yield {
            "type": "done",
            "response": FALLBACK_RESPONSE,
            "tool_called": tool_called,
            "reasoning": reasoning,
            "phase": phase,
            "context": context,
            "latency_ms": profile[-1]["ms"] if profile else 0,
            "profile": profile,
        }
        return

    if first_token_marked:
        profiler.mark("last_token_streamed")
    content = strip_thinking("".join(response_parts) or (final_message.content or ""))
    content = _append_disclaimer_if_needed(content, phase, context, tool_results)
    if stack is not None:
        content = _enforce_guiding_brevity(content, allow_four=first_guiding, comprehensive=first_guiding)

    if not content:
        content = get_demo_fallback_response(transcript, context, phase) or ""

    profiler.mark("response_complete")
    profile = profiler.report()
    yield {
        "type": "done",
        "response": content or FALLBACK_RESPONSE,
        "tool_called": tool_called,
        "reasoning": reasoning,
        "phase": phase,
        "context": context,
        "latency_ms": profile[-1]["ms"] if profile else 0,
        "profile": profile,
    }


async def run_agent_stream(
    transcript: str,
    conversation_history: list[dict],
    profiler: LatencyProfiler,
    session_id: str = "",
    context: dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    profiler.mark("messages_built")
    async for event in _run_agent_turn_stream(
        transcript, conversation_history, session_id, profiler, context
    ):
        yield event


def warmup_llm() -> None:
    try:
        client = _get_client()
        if not LLM_MODEL:
            return
        client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
            stream=False,
            timeout=LLM_TIMEOUT_SECONDS,
            extra_body=_llm_extra_body(),
        )
        print(f"[warmup] LLM pre-warmed ({LLM_MODEL})")
    except Exception as exc:
        print(f"[warmup] LLM pre-warm skipped: {exc}")
