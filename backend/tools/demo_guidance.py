"""One-turn demo snippets for Whole Foods / Zurich / California scenario."""

from __future__ import annotations

from typing import Any

WHAT_ELSE = ("what else", "what now", "anything else", "what should i", "what do i do")
FOOTAGE = ("footage", "video", "security camera", "cctv", "surveillance", "recording")


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
