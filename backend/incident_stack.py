"""Server-side incident stack and session store."""

from __future__ import annotations

import time
from typing import Any

SESSION_TTL_SECONDS = 3600
CLEANUP_INTERVAL_SECONDS = 1800

# session_id -> {"stack": IncidentStack, "created_at": float}
sessions: dict[str, dict[str, Any]] = {}


INCIDENT_TYPE_MAP = {
    "slip_fall": "slip and fall",
    "hit_run": "car accident",
    "dog_bite": "dog bite",
    "workplace": "workplace injury",
    "assault": "assault",
    "other": "general",
}


QUESTIONS: dict[str, list[str]] = {
    "injuries": [
        "Are you hurt anywhere?",
        "How are you feeling physically right now?",
    ],
    "can_move": [
        "Can you move safely without sharp pain?",
    ],
    "incident_type": [
        "Can you tell me exactly what happened?",
        "What were you doing when you got hurt?",
    ],
    "state": [
        "Which city or state are you in?",
        "Where did this happen?",
    ],
    "still_at_scene": [
        "Are you still at the scene right now?",
        "Are you still there?",
    ],
    "signed_anything": [
        "Has anyone asked you to sign anything yet?",
    ],
    "witnesses": [
        "Was anyone else around who saw what happened?",
        "Any witnesses nearby?",
    ],
}


PRE_GUIDE_GAPS = frozenset(
    {"injuries", "can_move", "incident_type", "state", "still_at_scene"}
)


class IncidentStack:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {
            "incident_type": None,
            "location": None,
            "state": None,
            "store_name": None,
            "injuries": None,
            "can_move": None,
            "called_911": None,
            "ambulance_needed": None,
            "still_at_scene": None,
            "driver_fled": None,
            "witnesses": None,
            "signed_anything": None,
            "photos_taken": None,
            "police_report": None,
            "medical_attention": None,
            "insurance_known": None,
            "other_carrier": None,
            "employer_name": None,
            "disclaimer_given": False,
            "tools_fired": [],
            "nearby_legal_fired": False,
            "questions_asked": [],
            "phase": "questioning",
            "turns": 0,
        }

    def gaps(self) -> list[str]:
        critical: list[str] = []

        # PRIORITY 1 — Physical safety always first
        if self.data["injuries"] is None:
            critical.append("injuries")
        if self.data["can_move"] is None:
            critical.append("can_move")

        # PRIORITY 2 — What happened
        if self.data["incident_type"] is None:
            critical.append("incident_type")

        # PRIORITY 3 — Where
        if self.data["state"] is None:
            critical.append("state")

        # PRIORITY 4 — Still at scene (skip if serious injury)
        if (
            self.data["still_at_scene"] is None
            and self.data["incident_type"] is not None
            and self.data["injuries"] != "serious"
        ):
            critical.append("still_at_scene")

        # PRIORITY 5 — Scene-specific (only at scene, turn 3+)
        if self.data["turns"] >= 3 and self.data["still_at_scene"] is True:
            if self.data["witnesses"] is None:
                critical.append("witnesses")
            if self.data["signed_anything"] is None:
                critical.append("signed_anything")

        return critical

    def needs_immediate_medical(self) -> bool:
        # Dog bites need ER — skip questioning until injury status is known
        return (
            self.data["incident_type"] == "dog_bite"
            and self.data["injuries"] is None
        ) or self.data["injuries"] == "serious"

    def is_ready_to_guide(self) -> bool:
        return (
            self.data["injuries"] is not None
            and self.data["incident_type"] is not None
            and self.data["state"] is not None
            and self.data["still_at_scene"] is not None
            and self.data["turns"] >= 3
        )

    def update_from_transcript(self, transcript: str) -> None:
        t = transcript.lower()
        self.data["turns"] += 1

        if any(w in t for w in ("slip", "fell", "fall", "wet floor", "tripped")):
            self.data["incident_type"] = "slip_fall"
        elif any(
            w in t
            for w in (
                "hit and run",
                "hit by a car",
                "hit by car",
                "hit me",
                "rear ended",
                "rear-ended",
                "fled",
                "drove away",
                "ran away",
                "car accident",
                "crashed",
                "collision",
            )
        ):
            self.data["incident_type"] = "hit_run"
        elif any(w in t for w in ("dog", "bit", "bite", "attacked")):
            self.data["incident_type"] = "dog_bite"
        elif any(w in t for w in ("work", "job", "employer", "warehouse", "construction")):
            self.data["incident_type"] = "workplace"

        if any(w in t for w in ("fled", "drove away", "ran away", "ran off", "driver left")):
            self.data["driver_fled"] = True

        us_states = {
            "california": "California",
            "texas": "Texas",
            "new york": "New York",
            "florida": "Florida",
            "illinois": "Illinois",
            "washington": "Washington",
            "arizona": "Arizona",
            "colorado": "Colorado",
            "georgia": "Georgia",
            "nevada": "Nevada",
            "oregon": "Oregon",
            "virginia": "Virginia",
            "ohio": "Ohio",
            "michigan": "Michigan",
            "pennsylvania": "Pennsylvania",
            "north carolina": "North Carolina",
            "new jersey": "New Jersey",
            "san jose": "California",
            "san francisco": "California",
            "los angeles": "California",
            "new york city": "New York",
            "chicago": "Illinois",
            "houston": "Texas",
            "dallas": "Texas",
            "austin": "Texas",
            "miami": "Florida",
            "seattle": "Washington",
            "portland": "Oregon",
            "denver": "Colorado",
            "las vegas": "Nevada",
            "phoenix": "Arizona",
            "atlanta": "Georgia",
        }
        for city_state, state in us_states.items():
            if city_state in t:
                self.data["state"] = state
                self.data["location"] = city_state.title()
                break

        if any(
            w in t
            for w in (
                "i can move",
                "i'm okay",
                "i'm fine",
                "can move",
                "can walk",
                "moving okay",
                "not hurt badly",
            )
        ):
            self.data["can_move"] = True
            if self.data["injuries"] is None:
                self.data["injuries"] = "minor"
        if any(
            w in t
            for w in ("can't move", "cannot move", "stuck", "severe pain", "broken", "fracture")
        ):
            self.data["can_move"] = False
            self.data["injuries"] = "serious"
        if any(w in t for w in ("wrist hurts", "back hurts", "pain", "hurts", "injured", "hurt")):
            if self.data["injuries"] is None:
                self.data["injuries"] = "moderate"
        if any(w in t for w in ("bled", "bleeding", "blood", "bite", "bit me", "bitten")):
            if self.data["injuries"] is None:
                self.data["injuries"] = "moderate"

        if any(w in t for w in ("still at", "still here", "i'm here", "at the scene", "at the store")):
            self.data["still_at_scene"] = True
        if any(w in t for w in ("left", "went home", "i'm home", "i'm at home")):
            self.data["still_at_scene"] = False

        if any(w in t for w in ("called 911", "called the police", "police are here", "cops are here")):
            self.data["called_911"] = True
            self.data["police_report"] = True
        if any(w in t for w in ("took photos", "took pictures", "photographed", "took a photo")):
            self.data["photos_taken"] = True
        if any(w in t for w in ("signed", "i signed")):
            self.data["signed_anything"] = True
        if any(w in t for w in ("didn't sign", "did not sign", "haven't signed", "won't sign")):
            self.data["signed_anything"] = False
        if any(w in t for w in ("witness", "someone saw", "person saw", "they saw")):
            self.data["witnesses"] = True

        stores = [
            "whole foods",
            "walmart",
            "target",
            "kroger",
            "safeway",
            "costco",
            "home depot",
            "lowes",
            "walgreens",
            "cvs",
            "trader joe",
        ]
        for store in stores:
            if store in t:
                self.data["store_name"] = store.title()
                break

        if (self.data.get("store_name") or "").lower().startswith("whole foods"):
            self.data["state"] = "California"

        carriers = [
            "state farm",
            "allstate",
            "geico",
            "progressive",
            "farmers",
            "usaa",
            "liberty mutual",
            "travelers",
            "nationwide",
        ]
        for carrier in carriers:
            if carrier in t:
                display = "USAA" if carrier == "usaa" else carrier.title()
                self.data["other_carrier"] = display
                self.data["insurance_known"] = True
                print(f"[STACK] Carrier detected: {display}")
                break

    def to_agent_context(self) -> dict[str, Any]:
        """Map stack fields to agent context dict used by tools/router."""
        injuries = self.data.get("injuries")
        severity_map = {
            "none": "mild",
            "minor": "mild",
            "moderate": "moderate",
            "serious": "serious",
        }
        incident_key = self.data.get("incident_type")
        store = self.data.get("store_name") or ""
        ctx: dict[str, Any] = {
            "state": self.data.get("state"),
            "incident_type": INCIDENT_TYPE_MAP.get(incident_key, incident_key or "general"),
            "signed_anything": bool(self.data.get("signed_anything")),
            "witnesses": bool(self.data.get("witnesses")),
            "injury_severity": severity_map.get(injuries, injuries),
            "disclaimer_given": bool(self.data.get("disclaimer_given")),
            "tools_fired": list(self.data.get("tools_fired") or []),
            "nearby_legal_fired": bool(self.data.get("nearby_legal_fired")),
            "prefetched_state_law": None,
            "stack_phase": self.data.get("phase"),
            "incident_stack": dict(self.data),
        }
        if store.lower() == "whole foods":
            ctx["demo_store"] = "Whole Foods"
        if self.data.get("other_carrier"):
            ctx["other_carrier"] = self.data["other_carrier"]
        if not ctx.get("state") and store.lower() == "whole foods":
            ctx["state"] = "California"
        return ctx

    def sync_from_agent_context(self, context: dict[str, Any]) -> None:
        if context.get("disclaimer_given"):
            self.data["disclaimer_given"] = True
        if context.get("nearby_legal_fired"):
            self.data["nearby_legal_fired"] = True
        for tool in context.get("tools_fired") or []:
            if tool not in self.data["tools_fired"]:
                self.data["tools_fired"].append(tool)


def get_next_question(stack: IncidentStack) -> str | None:
    gaps = stack.gaps()
    if not gaps:
        return None

    top_gap = gaps[0]
    questions = QUESTIONS.get(top_gap, [])
    asked = stack.data["questions_asked"]

    for q in questions:
        if q not in asked:
            stack.data["questions_asked"].append(q)
            return q

    return questions[0] if questions else None


def get_or_create_stack(session_id: str) -> IncidentStack:
    entry = sessions.get(session_id)
    if entry is None:
        stack = IncidentStack()
        sessions[session_id] = {"stack": stack, "created_at": time.time()}
        return stack
    entry["created_at"] = time.time()
    return entry["stack"]


def cleanup_expired_sessions() -> int:
    cutoff = time.time() - SESSION_TTL_SECONDS
    expired = [k for k, v in sessions.items() if v["created_at"] < cutoff]
    for k in expired:
        del sessions[k]
    if expired:
        print(f"[SESSION] Cleaned {len(expired)} expired session(s)")
    return len(expired)
