"""Jake hit-and-run demo — 5 turns with own-policy MedPay on turn 4."""

import json
import re
import subprocess
import time

TURNS = [
    "I just got rear ended in Austin, the other driver wants to skip police",
    "my neck hurts but I can move, still here",
    "yeah I got his plates. Police just arrived and filed a report. His insurance is State Farm",
    "My neck is getting worse. I'm worried about the medical bills — will my insurance cover this?",
    "What if State Farm calls me before I hear back from Progressive?",
]

EXPECTED_T4 = [
    "progressive",
    "medpay",
    "med pay",
    "10,000",
    "10000",
    "$10",
    "er",
    "urgent",
    "hospital",
    "doctor",
    "your policy",
    "your coverage",
]


def call(transcript: str, history: list[dict], session_id: str | None = None) -> dict:
    body: dict = {"transcript": transcript, "conversation_history": history}
    if session_id:
        body["session_id"] = session_id
    proc = subprocess.run(
        [
            "curl", "-s", "-X", "POST", "http://localhost:8000/chat",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(body),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return json.loads(proc.stdout)


def score_t4(response: str, done: dict) -> dict:
    lower = response.lower()
    return {
        "insurance_tool": done.get("tool_called") == "insurance_tool",
        "progressive": "progressive" in lower,
        "medpay": "medpay" in lower or "med pay" in lower or "med-pay" in lower,
        "10000": any(x in lower for x in ("10,000", "10000", "$10,000")),
        "er": any(x in lower for x in ("er", "emergency", "urgent care", "hospital", "tonight", "today")),
        "under_3_sentences": len(re.split(r"(?<=[.!?])\s+", response.strip())) <= 3,
    }


def main():
    history: list[dict] = []
    session_id: str | None = None
    print("=== JAKE 5-TURN DEMO ===\n")

    for i, transcript in enumerate(TURNS, 1):
        time.sleep(0.5)
        done = call(transcript, history, session_id)
        if done.get("session_id"):
            session_id = done["session_id"]
        resp = done.get("response", "")
        print(f"Turn {i}: phase={done.get('phase')} tool={done.get('tool_called')} {done.get('latency_ms')}ms")
        print(f"  {resp}\n")
        if i == 4:
            checks = score_t4(resp, done)
            print("Turn 4 checks:", checks)
        history.append({"role": "user", "text": transcript})
        history.append({"role": "assistant", "text": resp})


if __name__ == "__main__":
    main()
