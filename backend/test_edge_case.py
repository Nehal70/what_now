"""Edge case: dog bite, user already home, asks medical/legal questions early."""

import asyncio
import os
import re
import sys

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

BASE = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")

TURNS = [
    "A stray dog bit my ankle at the park",
    "I'm home now, it bled a little but I can walk",
    "I'm in Portland Oregon. Do I need to go to the ER or can I wait until tomorrow?",
    "The owner grabbed the dog and ran off before I could get their info",
    "Should I report this to animal control or the police?",
]

CHECKS = [
    {"must_contain_any": ["er", "urgent", "doctor", "medical", "care", "hurt", "move"]},
    {
        "must_contain_any": ["city", "state", "where", "location"],
        "must_not_contain": ["sign"],
    },
    {"must_contain_any": ["er", "urgent", "clinic", "doctor", "medical", "tomorrow", "wait", "care"]},
    {"one_thing_only": True},
    {"must_contain_any": ["report", "animal", "police", "control"]},
]


def is_list_dump(text: str) -> bool:
    # Strip disclaimer before counting — it's appended separately
    core = re.sub(r"quick note — this is guidance.*$", "", text, flags=re.I).strip()
    sentences = [s.strip() for s in re.split(r"[.!?]+", core) if s.strip()]
    list_markers = len(re.findall(r"^\s*[\-\*\d+\.]", core, re.M))
    chain_words = len(re.findall(r"\bAlso\b|\bThen\b|\bNext\b|\bYou should also\b", core))
    return list_markers > 0 or len(sentences) > 2 or chain_words >= 1


def check_turn(turn_num: int, response: str, stack_ctx: dict) -> list[str]:
    issues: list[str] = []
    resp_lower = response.lower()
    spec = CHECKS[turn_num - 1]

    group = spec.get("must_contain_any", [])
    if group and not any(w in resp_lower for w in group):
        issues.append(f"missing expected keywords (any of {group})")

    for word in spec.get("must_not_contain", []):
        if word in resp_lower:
            issues.append(f"should not mention '{word}'")

    if spec.get("one_thing_only") and is_list_dump(response):
        issues.append("Turn 4 must be ONE action only — response looks like a list dump")

    if turn_num >= 2 and stack_ctx.get("incident_type") != "dog_bite":
        issues.append(f"stack incident_type={stack_ctx.get('incident_type')}, want dog_bite")

    return issues


async def run_turn(
    client: httpx.AsyncClient,
    transcript: str,
    history: list[dict],
    session_id: str | None,
) -> tuple[str, list[dict], str, dict]:
    body: dict = {
        "transcript": transcript,
        "conversation_history": history,
        "context": {},
    }
    if session_id:
        body["session_id"] = session_id

    resp = await client.post(f"{BASE}/chat", json=body, timeout=120.0)
    resp.raise_for_status()
    data = resp.json()

    history = history + [
        {"role": "user", "text": transcript},
        {"role": "assistant", "text": data["response"]},
    ]
    sid = data.get("session_id") or session_id or ""
    return data["response"], history, sid, data


async def main() -> None:
    history: list[dict] = []
    session_id: str | None = None
    all_issues: list[str] = []
    turn2_response = ""
    turn4_response = ""

    print("EDGE CASE: Dog bite · left scene · owner fled · early ER question")
    print(f"Server: {BASE}\n")
    print("=" * 64)

    async with httpx.AsyncClient() as client:
        for i, transcript in enumerate(TURNS, 1):
            response, history, session_id, meta = await run_turn(
                client, transcript, history, session_id
            )
            ctx = meta.get("context") or {}
            phase = meta.get("phase")

            if i == 2:
                turn2_response = response
            if i == 4:
                turn4_response = response

            print(f"\nTurn {i} USER: {transcript}")
            print(f"Turn {i} AGENT: {response}")
            print(f"  phase={phase} reasoning={meta.get('reasoning', '')}")
            print(
                f"  stack: type={ctx.get('incident_type')} state={ctx.get('state')} "
                f"injuries={ctx.get('injuries')} at_scene={ctx.get('still_at_scene')} "
                f"turns={ctx.get('turns')}"
            )

            issues = check_turn(i, response, ctx)
            if issues:
                print(f"  CHECKS: FAIL — {'; '.join(issues)}")
                all_issues.extend([f"Turn {i}: {x}" for x in issues])
            else:
                print("  CHECKS: pass")
            print("-" * 64)

    print("\n=== TURN 2 RESPONSE ===")
    print(turn2_response)
    print("\n=== TURN 4 RESPONSE ===")
    print(turn4_response)
    print()

    if all_issues:
        print(f"RESULT: {len(all_issues)} issue(s)")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    print("RESULT: edge case handled cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print(f"Cannot connect to {BASE}. Start server first.", file=sys.stderr)
        sys.exit(1)
