"""Deterministic Jake demo script — bypasses LLM when DEMO_MODE=true or session_id=jake-demo."""

from __future__ import annotations

import os
import re
from typing import Any

from tools.demo_guidance import (
    AUSTIN_DEMO_LEGAL,
    AUSTIN_DEMO_MEDICAL,
    apply_demo_context,
)

IMAGE_UPLOAD_TOKEN = "__IMAGE_UPLOAD__"
START_TOKEN = "__START__"

DEMO_RESPONSES: dict[str, str] = {
    "__START__": "I'm here. How can I help you?",
    "turn_1": (
        "I'm sorry — neck pain after a rear-end gets worse before it gets better, "
        "not better. Can you move okay, and are you still at the scene?"
    ),
    "turn_2": (
        "Don't agree to that. Without a police report he can deny everything tomorrow. "
        "Say: 'I need to call the police first.' Which state are you in?"
    ),
    "turn_3": (
        "Friendly doesn't protect you legally. Has anyone asked you to sign anything yet?"
    ),
    "turn_4": (
        "State Farm will call you within the hour — that's their playbook, not a coincidence. "
        "When they call say exactly this: 'I'm not giving a recorded statement right now. "
        "Please communicate with me in writing.' Then hang up."
    ),
    "turn_4_5": (
        "One more thing — open the What Now app and send me a photo of the damage to your "
        "car. I want to see it before State Farm does."
    ),
    "turn_4_7": (
        "That bumper is completely gone and I can see trunk and frame deformation — "
        "this is structural damage, not cosmetic. State Farm is going to call this a five "
        "hundred dollar fix. It is not. You are looking at eight to fifteen thousand dollars "
        "in repairs minimum, and that impact has permanently reduced your car's resale value "
        "by another three to five thousand. Do not let them close this claim cheaply."
    ),
    "turn_5": (
        "Your Progressive policy has MedPay — that covers up to ten thousand dollars in "
        "medical bills right now, no waiting for State Farm to decide anything. Call "
        "Progressive at 1-800-776-4737 and file a MedPay claim today. And go to the ER "
        "tonight — delayed treatment is the number one way State Farm denies injury claims."
    ),
    "turn_6": (
        "Don't take it. Four thousand dollars is their opening lowball — sent before you "
        "know how badly you're hurt or how much your car actually costs to fix. We just "
        "saw the damage. In Texas with a police report, structural damage, documented "
        "whiplash, and an ER visit you are looking at thirty to seventy five thousand "
        "dollars."
    ),
    "turn_7": (
        "Most Texas attorneys work on contingency — free consultation, nothing upfront. "
        "And those urgent care facilities on your screen right now? Go to the closest "
        "one tonight. Not tomorrow."
    ),
}

STAY_RESPONSE = "I'm with you — take your time."
PHOTO_HOLD_RESPONSE = (
    "Hold on — send that damage photo in the What Now app first. "
    "I need to see it before State Farm does."
)

# Scripted user beats — matched in order; incidental speech does NOT advance.
USER_TURN_PHRASES: dict[int, tuple[str, ...]] = {
    1: ("rear end", "rear-ended", "rear ended", "neck"),
    2: ("skip", "police", "friendly", "still here", "can move"),
    3: ("austin", "texas", "minor"),
    4: (
        "state farm",
        "filed a report",
        "police just",
        "police arrived",
        "his insurance",
        "not yet",
    ),
    5: (
        "medical",
        "medpay",
        "progressive",
        "getting worse",
        "insurance cover",
        "bills",
    ),
    6: ("4000", "4,000", "settlement", "take it", "lowball", "texted me"),
    7: ("thank you", "thanks", "thank"),
}

AGENT_FOR_USER_TURN: dict[int, str] = {
    1: "turn_1",
    2: "turn_2",
    3: "turn_3",
    4: "turn_4",
    5: "turn_5",
    6: "turn_6",
    7: "turn_7",
}

THANK_YOU_PHRASES = ("thank you", "thanks", "thank")

TURN_META: dict[str, dict[str, Any]] = {
    "turn_1": {
        "tool_called": "safety_check",
        "tools_fired": ["safety_check"],
        "phase": "questioning",
        "reasoning": "Jake demo T1 — rear-end triage, confirm mobility and scene",
        "context": {
            "incident_type": "car_accident",
            "injuries": "moderate",
            "injury_severity": "moderate",
        },
    },
    "turn_2": {
        "tool_called": "scene_guide",
        "tools_fired": ["scene_guide"],
        "phase": "questioning",
        "reasoning": "Jake demo T2 — block skip-police pressure, confirm state",
        "context": {"still_at_scene": True, "can_move": True},
    },
    "turn_3": {
        "tool_called": "scene_guide",
        "tools_fired": ["scene_guide"],
        "phase": "questioning",
        "reasoning": "Jake demo T3 — Texas confirmed, warn on friendly driver",
        "context": {
            "state": "Texas",
            "location": "Austin",
            "signed_anything": False,
        },
    },
    "turn_4": {
        "tool_called": "insurance_tool",
        "tools_fired": ["insurance_tool", "moss_retrieval", "legal_tool"],
        "phase": "guiding",
        "reasoning": "Jake demo T4 — State Farm adjuster script",
        "context": {
            "other_carrier": "State Farm",
            "police_report": True,
            "signed_anything": False,
            "witnesses": False,
        },
        "dashboard_delay_s": 3,
    },
    "turn_4_5": {
        "tool_called": "scene_guide",
        "tools_fired": ["scene_guide"],
        "phase": "guiding",
        "reasoning": "Jake demo T4.5 — request damage photo before adjuster",
        "context": {
            "awaiting_image": True,
            "image_prompt": "Send photo of the damage to your car",
        },
        "emit_image_requested": True,
    },
    "turn_4_7": {
        "tool_called": "scene_guide",
        "tools_fired": ["scene_guide"],
        "phase": "guiding",
        "reasoning": "Jake demo T4.7 — structural damage assessment from photo",
        "context": {
            "awaiting_image": False,
            "structural_damage": True,
            "damage_estimate_low": 8000,
            "damage_estimate_high": 15000,
            "scene_description": (
                "complete bumper detachment, trunk crumple, frame deformation visible"
            ),
        },
        "emit_image_processed": True,
    },
    "turn_5": {
        "tool_called": "insurance_tool",
        "tools_fired": ["insurance_tool", "moss_retrieval"],
        "phase": "guiding",
        "reasoning": "Jake demo T5 — Progressive MedPay + ER tonight",
        "context": {
            "injuries": "moderate",
            "medical_attention": True,
            "insurance_known": True,
            "demo_insurer": "Progressive",
        },
        "emit_nearby_medical": True,
    },
    "turn_6": {
        "tool_called": "legal_tool",
        "tools_fired": ["legal_tool", "moss_retrieval"],
        "phase": "guiding",
        "reasoning": "Jake demo T6 — reject lowball settlement",
        "context": {
            "demo_case_strength": 84,
            "medical_attention": True,
            "police_report": True,
            "structural_damage": True,
        },
    },
    "turn_7": {
        "tool_called": "legal_tool",
        "tools_fired": ["legal_tool", "moss_retrieval"],
        "phase": "guiding",
        "reasoning": "Jake demo T7 — attorney contingency + urgent care close",
        "context": {
            "demo_case_strength": 84,
            "medical_attention": True,
        },
        "emit_nearby_legal": True,
    },
}

JAKE_DEMO_SESSION = "jake-demo"

_JAKE_STATE_KEYS = (
    "jake_demo_image_done",
    "jake_demo_active",
    "jake_demo_key",
    "jake_vapi_call_id",
    "jake_photo_prompt_spoken",
    "jake_user_turn_done",
    "jake_pending_agent",
    "jake_pending_voice",
    "jake_awaiting_photo",
    "awaiting_image",
    "image_prompt",
    "demo_images_received",
    "last_jake_dedup_key",
    "last_jake_committed_transcript",
    "last_jake_demo_response",
    "last_jake_demo_key",
    "last_jake_demo_result",
    "last_demo_turn",
    "last_demo_response",
    "demo_script_turn",
    "final_demo_active",
)


def is_jake_demo_mode(session_id: str) -> bool:
    flag = os.getenv("DEMO_MODE", "").strip().lower()
    return flag in ("true", "1", "yes") or session_id == JAKE_DEMO_SESSION


def jake_demo_stack_id(session_id: str) -> str:
    if is_jake_demo_mode(session_id):
        return JAKE_DEMO_SESSION
    return session_id


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _matches_user_turn(text: str, turn: int) -> bool:
    phrases = USER_TURN_PHRASES.get(turn, ())
    return any(phrase in text for phrase in phrases)


def _is_thank_you(text: str) -> bool:
    norm = _norm_text(text)
    return any(phrase in norm for phrase in THANK_YOU_PHRASES)


def detect_user_turn(text: str, expected_next: int, user_done: int = 0) -> int:
    """Return matched user script turn (1-7), or 0 for noise/incidental speech."""
    norm = _norm_text(text)
    if user_done >= 6 and _is_thank_you(norm):
        return 7
    if len(norm) < 8:
        return 0
    if expected_next and _matches_user_turn(norm, expected_next):
        return expected_next
    for turn in range(1, 8):
        if turn == 7:
            continue
        if _matches_user_turn(norm, turn):
            return turn
    return 0


def jake_dedup_key(transcript: str) -> str:
    if transcript == IMAGE_UPLOAD_TOKEN:
        return "image_upload"
    if transcript == START_TOKEN:
        return "start"
    return _norm_text(transcript)


def jake_next_user_turn(stack_data: dict[str, Any]) -> int:
    return int(stack_data.get("jake_user_turn_done") or 0) + 1


def reset_jake_demo_state(stack_data: dict[str, Any], call_id: str | None = None) -> None:
    for key in _JAKE_STATE_KEYS:
        stack_data.pop(key, None)
    stack_data["jake_user_turn_done"] = 0
    if call_id:
        stack_data["jake_vapi_call_id"] = call_id


def ensure_jake_call_fresh(stack_data: dict[str, Any], session_id: str) -> None:
    if session_id == JAKE_DEMO_SESSION:
        return
    if not is_jake_demo_mode(session_id):
        return
    if stack_data.get("jake_vapi_call_id") != session_id:
        reset_jake_demo_state(stack_data, session_id)


def build_jake_demo_turn(key: str) -> dict[str, Any]:
    return _build_turn(key)


def _build_turn(key: str) -> dict[str, Any]:
    meta = TURN_META.get(key, {})
    return {
        "key": key,
        "response": DEMO_RESPONSES[key],
        "tool_called": meta.get("tool_called"),
        "tools_fired": list(meta.get("tools_fired") or []),
        "phase": meta.get("phase", "questioning"),
        "reasoning": meta.get("reasoning", f"Jake demo {key}"),
        "context": dict(meta.get("context") or {}),
        "dashboard_delay_s": meta.get("dashboard_delay_s", 0),
        "emit_nearby_medical": bool(meta.get("emit_nearby_medical")),
        "emit_nearby_legal": bool(meta.get("emit_nearby_legal")),
        "emit_image_requested": bool(meta.get("emit_image_requested")),
        "emit_image_processed": bool(meta.get("emit_image_processed")),
    }


def _build_stay_turn(stack_data: dict[str, Any]) -> dict[str, Any]:
    last = (stack_data.get("last_jake_demo_response") or "").strip()
    response = last or STAY_RESPONSE
    return {
        "key": "stay",
        "response": response,
        "tool_called": None,
        "tools_fired": [],
        "phase": stack_data.get("phase", "questioning"),
        "reasoning": "Jake demo — holding position, no script advance",
        "context": {},
        "advance_user_turn": False,
        "commit": False,
    }


def _build_photo_hold() -> dict[str, Any]:
    hold = _build_turn("turn_4_5")
    hold["key"] = "photo_hold"
    hold["response"] = PHOTO_HOLD_RESPONSE
    hold["emit_image_requested"] = True
    hold["advance_user_turn"] = False
    hold["commit"] = True
    return hold


def resolve_jake_demo_turn(
    transcript: str,
    history: list[dict],
    stack_data: dict[str, Any],
    images: list[dict] | None = None,
) -> dict[str, Any]:
    """Phrase-gated script — only advance on matched demo lines, never on noise."""
    if transcript == START_TOKEN:
        return _build_turn("__START__")

    if transcript == IMAGE_UPLOAD_TOKEN:
        if images:
            stack_data["demo_images_received"] = len(images)
        stack_data["jake_demo_image_done"] = True
        stack_data["jake_awaiting_photo"] = False
        stack_data["awaiting_image"] = False
        stack_data["jake_photo_prompt_spoken"] = True
        stack_data["jake_pending_voice"] = "turn_4_7"
        turn = _build_turn("turn_4_7")
        turn["advance_user_turn"] = False
        turn["commit"] = True
        return turn

    user_done = int(stack_data.get("jake_user_turn_done") or 0)
    expected = jake_next_user_turn(stack_data)
    matched = detect_user_turn(transcript, expected, user_done=user_done)

    if stack_data.get("jake_awaiting_photo") and not stack_data.get("jake_demo_image_done"):
        if matched >= 5:
            return _build_photo_hold()
        if matched == 0:
            return _build_stay_turn(stack_data)
        return _build_photo_hold()

    if matched == 0:
        return _build_stay_turn(stack_data)

    if matched <= user_done:
        return _build_stay_turn(stack_data)

    if matched == 7 and user_done < 6:
        return _build_stay_turn(stack_data)

    if matched > expected:
        matched = expected

    if matched == 5 and not stack_data.get("jake_demo_image_done"):
        return _build_photo_hold()

    agent_key = AGENT_FOR_USER_TURN[matched]
    turn = _build_turn(agent_key)
    turn["advance_user_turn"] = True
    turn["commit"] = True
    turn["user_turn"] = matched

    if agent_key == "turn_4":
        stack_data["jake_awaiting_photo"] = True

    return turn


def apply_jake_demo_turn(stack_data: dict[str, Any], demo: dict[str, Any]) -> None:
    apply_demo_context(stack_data, {**demo, "turn": demo.get("key")})
    stack_data["jake_demo_active"] = True
    stack_data["jake_demo_key"] = demo.get("key")
    for key, value in (demo.get("context") or {}).items():
        stack_data[key] = value
    if demo.get("key") == "turn_4_5":
        stack_data["jake_photo_prompt_spoken"] = True
        stack_data["awaiting_image"] = True
        stack_data["jake_awaiting_photo"] = True


def demo_nearby_places(event_type: str) -> list[dict[str, Any]]:
    if event_type == "nearby_medical":
        return AUSTIN_DEMO_MEDICAL
    return AUSTIN_DEMO_LEGAL
