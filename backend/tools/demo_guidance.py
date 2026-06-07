"""Demo-specific guidance and fallbacks for judge demos."""

from __future__ import annotations

from typing import Any

WHAT_ELSE = ("what else", "what now", "anything else", "what should i", "what do i do")
FOOTAGE = ("footage", "video", "security camera", "cctv", "surveillance", "recording")


def _stack(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("incident_stack") or {}


def is_jake_rearend_scenario(context: dict[str, Any]) -> bool:
    """Texas rear-end + State Farm — final demo script."""
    stack = _stack(context)
    incident = stack.get("incident_type") or context.get("incident_type", "")
    if incident in ("car accident", "car_accident", "hit_run", "hit and run"):
        incident_ok = True
    else:
        incident_ok = False
    state = context.get("state") or stack.get("state")
    carrier = context.get("other_carrier") or stack.get("other_carrier")
    return incident_ok and state == "Texas" and carrier == "State Farm"


def get_jake_first_guiding_response(context: dict[str, Any]) -> str | None:
    if not is_jake_rearend_scenario(context):
        return None
    return (
        "Okay — here's what matters. State Farm will call you within the hour, "
        "that's their playbook not a coincidence. When they call say exactly: "
        "\"I'm not giving a recorded statement. Please communicate with me in writing.\" "
        "Then hang up. In Texas rear-end accidents are almost always the other driver's fault. "
        "Your neck pain is whiplash until proven otherwise — go to the ER tonight. "
        "Your Progressive policy covers up to $10,000 in medical bills right now through MedPay, "
        "no waiting for State Farm. And don't say you're okay to anyone."
    )


def get_jake_settlement_response(context: dict[str, Any]) -> str | None:
    if not is_jake_rearend_scenario(context):
        return None
    return (
        "Don't take it. With a police report, documented whiplash, and an ER visit in Texas — "
        "you're looking at $25,000 to $75,000. State Farm's first offer is always a fraction "
        "of actual value. Most Texas attorneys work on contingency — free consultation, nothing upfront."
    )


def get_demo_guidance(transcript: str, context: dict[str, Any], phase: str) -> str | None:
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
    jake_settlement = get_jake_settlement_response(context)
    if jake_settlement and any(w in transcript.lower() for w in ("worth", "4,000", "4000", "texted", "settlement", "take it")):
        return jake_settlement

    jake_first = get_jake_first_guiding_response(context)
    stack_data = context.get("incident_stack") or {}
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
