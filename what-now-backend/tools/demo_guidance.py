"""Demo-specific guidance and hardcoded final demo script."""

from __future__ import annotations

from typing import Any

WHAT_ELSE = ("what else", "what now", "anything else", "what should i", "what do i do")
FOOTAGE = ("footage", "video", "security camera", "cctv", "surveillance", "recording")

FINAL_DEMO_OPENING = "I'm here. Are you hurt?"

# ── Final demo script: Jake rear-end / Austin TX / State Farm / Progressive ──
FINAL_DEMO_USER_TRIGGERS = (
    "rear ended",
    "rear-ended",
    "red light",
    "state farm",
    "austin",
    "progressive",
    "medpay",
    "med pay",
    "settlement",
    "4,000",
    "4000",
    "neck",
)

FINAL_DEMO_TURNS: dict[int, dict[str, Any]] = {
    1: {
        "response": (
            "I'm sorry — neck pain after a rear-end can get worse before it gets better. "
            "Can you move okay, and are you still at the scene?"
        ),
        "tool": None,
        "phase": "questioning",
        "tools_fired": [],
        "reasoning": "Demo T1 — rear-end triage, confirm mobility and scene",
        "context": {
            "incident_type": "car_accident",
            "injuries": "moderate",
            "injury_severity": "moderate",
        },
        "dashboard_delay_s": 0,
    },
    2: {
        "response": (
            "Don't agree to that — you need that police report. Without it he can deny "
            "everything tomorrow. Just say: 'I need to call the police first.' "
            "Which state are you in?"
        ),
        "tool": None,
        "phase": "questioning",
        "tools_fired": [],
        "reasoning": "Demo T2 — block skip-police pressure, confirm state",
        "context": {
            "still_at_scene": True,
            "can_move": True,
        },
        "dashboard_delay_s": 0,
    },
    3: {
        "response": (
            "Friendly doesn't protect you legally. "
            "Has anyone asked you to sign anything yet?"
        ),
        "tool": None,
        "phase": "questioning",
        "tools_fired": [],
        "reasoning": "Demo T3 — Texas confirmed, warn on friendly driver",
        "context": {
            "state": "Texas",
            "location": "Austin",
            "signed_anything": False,
        },
        "dashboard_delay_s": 0,
    },
    4: {
        "response": (
            "State Farm will call you within the hour — that's their playbook, not a coincidence. "
            "When they call say exactly this: 'I'm not giving a recorded statement right now. "
            "Please communicate with me in writing.' Then hang up."
        ),
        "tool": "insurance_tool",
        "phase": "guiding",
        "tools_fired": ["insurance_tool", "moss_retrieval", "legal_tool"],
        "reasoning": "Demo T4 — State Farm adjuster script + Moss/Unsiloed retrieval",
        "context": {
            "other_carrier": "State Farm",
            "police_report": True,
            "signed_anything": False,
            "witnesses": False,
        },
        "dashboard_delay_s": 3,
    },
    5: {
        "response": (
            "Your Progressive policy has MedPay — that covers up to $10,000 in medical bills "
            "right now, no waiting for State Farm. Call Progressive at 1-800-776-4737 "
            "and file a MedPay claim today."
        ),
        "tool": "insurance_tool",
        "phase": "guiding",
        "tools_fired": ["insurance_tool", "moss_retrieval"],
        "reasoning": "Demo T5 — Progressive MedPay from my_insurance.txt",
        "context": {
            "injuries": "moderate",
            "medical_attention": True,
            "insurance_known": True,
            "demo_insurer": "Progressive",
        },
        "emit_nearby_medical": True,
        "dashboard_delay_s": 0,
    },
    6: {
        "response": (
            "Don't take it — that's their opening lowball, sent before you know how badly "
            "you're hurt. In Texas with a police report, documented whiplash, and an ER visit "
            "you're looking at $25,000 to $75,000. But first — those urgent care facilities "
            "on your screen right now? Go to the closest one that's open. Tonight. Not tomorrow."
        ),
        "tool": "legal_tool",
        "phase": "guiding",
        "tools_fired": ["legal_tool", "moss_retrieval"],
        "reasoning": "Demo T6 — settlement floor + urgent care push + attorney search",
        "context": {
            "demo_case_strength": 84,
            "medical_attention": True,
            "police_report": True,
        },
        "emit_nearby_legal": True,
        "dashboard_delay_s": 0,
    },
}

AUSTIN_DEMO_MEDICAL = [
    {
        "name": "Austin Emergency Center",
        "address": "1101 W 38th St, Austin, TX",
        "phone": "(512) 407-4111",
        "distance": "0.4 mi",
        "open_now": True,
    },
    {
        "name": "CareNow Urgent Care",
        "address": "801 E 51st St, Austin, TX",
        "phone": "(512) 458-9898",
        "distance": "0.6 mi",
        "open_now": True,
    },
    {
        "name": "FastMed Urgent Care",
        "address": "2300 S Lamar Blvd, Austin, TX",
        "phone": "(512) 444-4211",
        "distance": "0.8 mi",
        "open_now": True,
    },
    {
        "name": "St. David's ER",
        "address": "3000 E 15th St, Austin, TX",
        "phone": "(512) 544-4240",
        "distance": "1.1 mi",
        "open_now": True,
    },
    {
        "name": "Ascension Seton Medical Center",
        "address": "1201 W 38th St, Austin, TX",
        "phone": "(512) 324-7000",
        "distance": "1.3 mi",
        "open_now": True,
    },
]

AUSTIN_DEMO_LEGAL = [
    {
        "name": "Glen Larson Law",
        "address": "100 Congress Ave, Austin, TX",
        "phone": "(512) 553-2000",
        "distance": "0.5 mi",
        "open_now": True,
    },
    {
        "name": "Terry & Kelly PLLC",
        "address": "901 S MoPac Expy, Austin, TX",
        "phone": "(512) 910-2000",
        "distance": "0.7 mi",
        "open_now": True,
    },
    {
        "name": "Austin Injury Lawyers",
        "address": "823 Congress Ave, Austin, TX",
        "phone": "(512) 444-1111",
        "distance": "0.9 mi",
        "open_now": True,
    },
    {
        "name": "Bonilla Law Firm",
        "address": "111 Congress Ave, Austin, TX",
        "phone": "(512) 222-3333",
        "distance": "1.0 mi",
        "open_now": True,
    },
]


def _stack(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("incident_stack") or context


def _conversation_text(history: list[dict], transcript: str) -> str:
    parts = [msg.get("text", "") for msg in history if msg.get("text")]
    parts.append(transcript)
    return " ".join(parts).lower()


def _user_turn_number(history: list[dict], transcript: str) -> int:
    count = sum(1 for msg in history if msg.get("role") == "user")
    if transcript.strip() and transcript != "__START__":
        count += 1
    return count


def is_final_demo_scenario(
    history: list[dict],
    transcript: str,
    stack_data: dict[str, Any] | None = None,
) -> bool:
    """Texas rear-end / State Farm — final judge demo."""
    if stack_data and stack_data.get("final_demo_active"):
        return True
    text = _conversation_text(history, transcript)
    if stack_data and stack_data.get("incident_type") in (
        "car_accident",
        "hit_run",
        "car accident",
    ):
        return True
    return any(trigger in text for trigger in FINAL_DEMO_USER_TRIGGERS)


def is_jake_rearend_scenario(context: dict[str, Any]) -> bool:
    stack = _stack(context)
    incident = stack.get("incident_type") or context.get("incident_type", "")
    incident_ok = incident in (
        "car accident",
        "car_accident",
        "hit_run",
        "hit and run",
    )
    state = context.get("state") or stack.get("state")
    carrier = context.get("other_carrier") or stack.get("other_carrier")
    return incident_ok and state == "Texas" and carrier == "State Farm"


def get_final_demo_turn(
    transcript: str,
    history: list[dict],
    stack_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Return hardcoded demo response for turn N (exact script lines)."""
    if not is_final_demo_scenario(history, transcript, stack_data):
        return None

    turn = _user_turn_number(history, transcript)
    spec = FINAL_DEMO_TURNS.get(turn)
    if not spec and turn > 6:
        spec = FINAL_DEMO_TURNS[6]
        turn = 6
    if not spec:
        return None

    return {
        "turn": turn,
        "response": spec["response"],
        "tool_called": spec.get("tool"),
        "phase": spec.get("phase", "questioning"),
        "tools_fired": list(spec.get("tools_fired") or []),
        "reasoning": spec.get("reasoning", f"Final demo script turn {turn}"),
        "context": dict(spec.get("context") or {}),
        "dashboard_delay_s": spec.get("dashboard_delay_s", 0),
        "emit_nearby_medical": bool(spec.get("emit_nearby_medical")),
        "emit_nearby_legal": bool(spec.get("emit_nearby_legal")),
    }


def apply_demo_context(stack_data: dict[str, Any], demo: dict[str, Any]) -> None:
    """Merge per-turn dashboard fields into the incident stack."""
    for key, value in (demo.get("context") or {}).items():
        stack_data[key] = value
    stack_data["final_demo_active"] = True
    stack_data["demo_script_turn"] = demo.get("turn")
    stack_data["last_demo_turn"] = demo.get("turn")


def get_jake_first_guiding_response(context: dict[str, Any]) -> str | None:
    if not is_jake_rearend_scenario(context):
        return None
    return FINAL_DEMO_TURNS[4]["response"]


def get_jake_settlement_response(context: dict[str, Any]) -> str | None:
    if not is_jake_rearend_scenario(context):
        return None
    return FINAL_DEMO_TURNS[6]["response"]


def get_demo_guidance(transcript: str, context: dict[str, Any], phase: str) -> str | None:
    if is_final_demo_scenario([], transcript, _stack(context)):
        return None

    if context.get("demo_store") != "Whole Foods":
        return None

    t = transcript.lower()
    fired = context.get("tools_fired") or []

    if any(w in t for w in FOOTAGE):
        return (
            "Whole Foods overwrites security footage every 30 to 72 hours. "
            "That video of the wet floor with no sign is your strongest evidence — "
            "send a written preservation demand to Whole Foods Risk Management tonight."
        )

    if any(w in t for w in WHAT_ELSE) or ("said that" in t and "else" in t):
        return (
            "Whole Foods CGL through Zurich includes Med-Pay — it covers your medical bills "
            "up to $25,000 regardless of fault. Ask the adjuster: "
            "'Does the policy include Med-Pay?' They have to tell you."
        )

    if "adjuster" in t or "zurich" in t:
        return (
            "Zurich's TPA adjuster call is recorded. Don't answer their questions. "
            "Say: 'I'm not giving a statement right now. Please communicate with me in writing.' "
            "Then hang up."
        )

    if context.get("witnesses") or "saw" in t or "witness" in t:
        return (
            "In California, that witness matters — get their name and number before they leave. "
            "They can confirm there was no wet floor sign."
        )

    if any(w in t for w in ("form", "sign", "signing")) and phase in ("gather", "inform"):
        return (
            "Don't sign that form yet — just say 'I need a moment.' "
            "Signing under pressure can hurt your claim with Zurich later."
        )

    if phase == "triage":
        return (
            "Slip and fall at Whole Foods in California — the store owes you a safe floor. "
            "First check: can you move your fingers and wrist without sharp pain?"
        )

    return None


def get_demo_fallback_response(transcript: str, context: dict[str, Any], phase: str) -> str | None:
    """Conversational one-turn reply when LLM is unavailable."""
    stack_data = context.get("incident_stack") or context
    demo = get_final_demo_turn(transcript, [], stack_data)
    if demo:
        return demo["response"]

    jake_settlement = get_jake_settlement_response(context)
    if jake_settlement and any(
        w in transcript.lower()
        for w in ("worth", "4,000", "4000", "texted", "settlement", "take it")
    ):
        return jake_settlement

    jake_first = get_jake_first_guiding_response(context)
    if jake_first and not stack_data.get("has_guided"):
        return jake_first

    if context.get("demo_store") != "Whole Foods":
        return None

    t = transcript.lower()

    if any(w in t for w in FOOTAGE):
        return (
            "Here's the thing nobody tells you — Whole Foods overwrites their security "
            "footage every 30 to 72 hours. That footage of the wet floor with no sign is "
            "your strongest evidence. Do you have access to email right now?"
        )

    if any(w in t for w in WHAT_ELSE) or ("said that" in t and "else" in t):
        return (
            "One more thing — their Zurich policy includes something called Med-Pay. "
            "It covers your medical bills up to $25,000 regardless of fault. "
            "Ask the adjuster: 'Does the policy include Med-Pay?' Did they give you a claim number?"
        )

    if "adjuster" in t or "zurich" in t:
        return (
            "That Zurich call? Don't answer their questions — "
            "say: 'I'm not giving a statement right now. Please communicate with me in writing.' "
            "Did they leave a voicemail?"
        )

    if context.get("witnesses") or "saw" in t or "witness" in t:
        return (
            "Good — in California, that witness really matters. "
            "Is that person still nearby? Get their number before they leave."
        )

    if "form" in t or "manager" in t:
        return (
            "Don't sign anything yet — just say 'I need a moment.' "
            "Are you still at the Whole Foods right now?"
        )

    if phase == "triage":
        return (
            "Hey, I hear you — slipping at Whole Foods with a hurting wrist is scary. "
            "Can you move your fingers okay? You're doing the right thing calling."
        )

    return None
