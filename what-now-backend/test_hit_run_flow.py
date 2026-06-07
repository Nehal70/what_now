"""Test incident-stack questioning → guiding flow (hit-and-run scenario)."""

import asyncio
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

BASE = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")

TURNS = [
    "I was just hit by a car",
    "My wrist hurts but I can move",
    "I'm in San Jose California, the driver fled",
    "Yes I'm still here, I called 911 already",
    "What about my insurance, I have State Farm",
]


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

    print(f"Testing hit-and-run flow against {BASE}\n")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        for i, transcript in enumerate(TURNS, 1):
            response, history, session_id, meta = await run_turn(
                client, transcript, history, session_id
            )
            phase = meta.get("reasoning", "")
            print(f"\nTurn {i} USER: {transcript}")
            print(f"Turn {i} AGENT: {response}")
            print(f"  [{phase}] session={session_id[:8]}...")
            print("-" * 60)

    print("\nDone.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print(f"Cannot connect to {BASE}. Start server first.", file=sys.stderr)
        sys.exit(1)
