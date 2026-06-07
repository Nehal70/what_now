from __future__ import annotations

from typing import Any

from knowledge_base.retrieval import search_kb
from tools.insurance_tool import OWN_POLICY_TRIGGERS, build_policy_moss_query


def build_moss_query(transcript: str, context: dict, phase: str) -> str:
    transcript_lower = transcript.lower()
    if context.get("policy_moss") or any(w in transcript_lower for w in OWN_POLICY_TRIGGERS):
        query = build_policy_moss_query(
            context.get("incident_type") or "car accident",
            context.get("state") or "Texas",
        )
        print(f"[MOSS QUERY] {query}")
        return query

    parts: list[str] = []

    if context.get("incident_type"):
        parts.append(context["incident_type"].replace("_", " "))
        incident = context["incident_type"].lower()
        if "slip" in incident or "fall" in incident or "premises" in incident:
            parts.append("premises liability")

    if context.get("state"):
        parts.append(context["state"])

    if phase == "inform":
        if "legal_tool" not in context.get("tools_fired", []):
            parts.append(
                "legal rights fault liability statute of limitations"
            )
        else:
            parts.append(
                "insurance adjuster claim what to say recorded statement"
            )

    if phase == "summarize":
        parts.append(
            "next steps documentation evidence checklist attorney"
        )

    transcript_words = transcript.lower()
    if "adjuster" in transcript_words:
        parts.append(
            "adjuster recorded statement what to say dont say"
        )
    if "sign" in transcript_words:
        parts.append(
            "incident report what to write what not to sign"
        )
    if "lawyer" in transcript_words or "attorney" in transcript_words:
        parts.append(
            "when need lawyer contingency free consultation"
        )
    if "doctor" in transcript_words or "hospital" in transcript_words:
        parts.append(
            "medical treatment documentation insurance coverage"
        )

    if context.get("signed_anything"):
        parts.append("signed incident report waiver what not to sign")

    if context.get("injury_severity"):
        parts.append(f"{context['injury_severity']} injury medical treatment")

    if context.get("demo_store") == "Whole Foods" or "whole foods" in transcript.lower():
        parts.append("Whole Foods San Francisco Zurich commercial liability CGL")

    if context.get("demo_insurer") == "Zurich" or "zurich" in transcript.lower():
        parts.append("Zurich adjuster recorded statement Whole Foods claim")

    transcript_lower = transcript.lower()
    if any(
        w in transcript_lower
        for w in (
            "my insurance",
            "my policy",
            "my coverage",
            "progressive",
            "deductible",
            "medpay",
            "med pay",
            "file a claim",
            "subrogation",
            "uninsured",
            "hit and run",
            "driver fled",
            "what does my",
            "will i get",
        )
    ):
        parts.insert(
            0,
            "my insurance policy Progressive TX-2847-JAK-2024 MedPay UM collision deductible subrogation Texas",
        )

    if any(w in transcript_lower for w in ("footage", "video", "camera", "cctv", "surveillance")):
        parts.append(
            "Whole Foods security footage preservation 30 72 hours written demand"
        )

    if any(w in transcript_lower for w in ("what else", "what now", "anything else")):
        fired = context.get("tools_fired", [])
        if "insurance_tool" in fired:
            parts.append(
                "Med-Pay Whole Foods Zurich medical bills 25000 regardless of fault"
            )
        else:
            parts.append("slip fall grocery store next step one action")

    if not parts:
        parts.append(transcript.strip() or "personal injury premises liability")

    query = " ".join(parts)
    print(f"[MOSS QUERY] {query}")
    return query


def run(query_or_args: str | dict[str, Any]) -> str:
    if isinstance(query_or_args, dict):
        query = build_moss_query(
            query_or_args.get("transcript", ""),
            query_or_args.get("context", {}),
            query_or_args.get("phase", ""),
        )
    else:
        query = query_or_args
        print(f"[MOSS QUERY] {query}")

    result = search_kb(query)
    return f"[Knowledge base result for: {query}]\n{result}"
