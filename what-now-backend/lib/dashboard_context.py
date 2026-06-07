"""Serialize incident stack fields for dashboard SSE (no circular refs)."""

from __future__ import annotations

import json
from typing import Any

# Never send these over the wire — they create cycles or hold full agent payloads.
_INTERNAL_KEYS = frozenset(
    {
        "last_jake_demo_result",
        "last_jake_committed_transcript",
        "last_jake_demo_response",
        "last_jake_demo_key",
        "last_demo_response",
        "incident_stack",
    }
)

_DASHBOARD_KEYS = frozenset(
    {
        "incident_type",
        "location",
        "state",
        "injuries",
        "injury_severity",
        "awaiting_image",
        "image_prompt",
        "still_at_scene",
        "can_move",
        "signed_anything",
        "witnesses",
        "other_carrier",
        "police_report",
        "medical_attention",
        "insurance_known",
        "demo_insurer",
        "demo_case_strength",
        "structural_damage",
        "damage_estimate_low",
        "damage_estimate_high",
        "scene_description",
        "tools_fired",
        "phase",
        "has_guided",
        "disclaimer_given",
        "jake_demo_active",
        "jake_demo_phase",
        "jake_main_turn",
        "jake_photo_prompt_spoken",
        "demo_images_received",
        "final_demo_active",
        "demo_script_turn",
    }
)


def _json_safe(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def dashboard_context(stack_or_ctx: dict[str, Any] | None) -> dict[str, Any]:
    if not stack_or_ctx:
        return {}
    out: dict[str, Any] = {}
    for key, value in stack_or_ctx.items():
        if key in _INTERNAL_KEYS:
            continue
        if key not in _DASHBOARD_KEYS and not key.startswith("demo_"):
            continue
        if _json_safe(value):
            out[key] = value
    return out


def jake_result_cache(result: dict[str, Any], stack_data: dict[str, Any]) -> dict[str, Any]:
    """Cache last demo turn without storing circular context references."""
    return {
        "response": result.get("response", ""),
        "tool_called": result.get("tool_called"),
        "reasoning": result.get("reasoning"),
        "phase": result.get("phase"),
        "context": dashboard_context(stack_data),
        "demo_turn": result.get("demo_turn"),
        "dashboard_delay_s": result.get("dashboard_delay_s", 0),
        "emit_nearby_medical": bool(result.get("emit_nearby_medical")),
        "emit_nearby_legal": bool(result.get("emit_nearby_legal")),
        "emit_image_requested": bool(result.get("emit_image_requested")),
        "emit_image_processed": bool(result.get("emit_image_processed")),
    }
