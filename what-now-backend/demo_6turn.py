"""6-turn Whole Foods / Zurich progressive disclosure demo."""

import json
import re
import subprocess
import time

TURNS = [
    "I just slipped at Whole Foods, my wrist really hurts",
    "yeah I can move, manager is here with a form",
    "okay I didn't sign it, one person saw it happen",
    "the Zurich adjuster just called me",
    "okay I said that, what else",
    "what about the footage",
]

EXPECTED = {
    1: ["wrist", "move", "hurt", "slip", "okay", "breathe"],
    2: ["sign", "moment", "minute", "form"],
    3: ["witness", "number", "saw", "nearby", "person", "california"],
    4: ["statement", "writing", "adjuster", "zurich", "hang"],
    5: ["med-pay", "med pay", "25", "000", "25000", "medical", "zurich", "whole foods"],
    6: ["footage", "72", "30", "hour", "preserve", "security", "whole foods"],
}


def call(transcript: str, history: list[dict], session_id: str | None = None) -> dict:
    body: dict = {"transcript": transcript, "conversation_history": history}
    if session_id:
        body["session_id"] = session_id
    proc = subprocess.run(
        [
            "curl", "-s", "-N", "-X", "POST", "http://localhost:8000/chat/stream",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(body),
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("data: ") and '"type": "done"' in line:
            return json.loads(line[6:])
    raise RuntimeError(f"No done event. stdout={proc.stdout[-400:]}")


def score(response: str) -> dict:
    sentences = [s.strip() for s in re.split(r"[.!?]+", response) if s.strip()]
    also_count = len(re.findall(r"\bAlso\b|\balso\b", response))
    list_markers = len(re.findall(r"^\s*[\-\*\d+\.]", response, re.M))
    numbered = len(re.findall(r"\b\d+\.\s", response))
    return {
        "sentences": len(sentences),
        "also_count": also_count,
        "list_markers": list_markers,
        "numbered": numbered,
    }


def main():
    history: list[dict] = []
    session_id: str | None = None
    print("=== WHOLE FOODS / ZURICH 6-TURN DEMO ===\n")
    all_ok = True

    for i, transcript in enumerate(TURNS, 1):
        time.sleep(1)
        done = call(transcript, history, session_id)
        if done.get("session_id"):
            session_id = done["session_id"]
        resp = done.get("response", "")
        s = score(resp)
        phase = done.get("phase")
        tool = done.get("tool_called")
        ms = done.get("latency_ms", 0)

        dump = s["also_count"] >= 2 or s["list_markers"] > 0 or s["numbered"] >= 2 or s["sentences"] > 5
        concise = s["sentences"] <= 4 and not dump
        hits = [k for k in EXPECTED[i] if k in resp.lower()]
        specific = len(hits) > 0

        ok = concise and specific
        if not ok:
            all_ok = False

        print(f"Turn {i}: {resp}")
        print(f"  phase={phase} tool={tool} {ms}ms")
        print(f"  ONE-THING: {'✓' if concise else '✗'}  SPECIFIC: {hits or 'NONE'}")
        print()

        history.append({"role": "user", "text": transcript})
        history.append({"role": "assistant", "text": resp})

    print(f"Demo ready: {'YES' if all_ok else 'NO'}")


if __name__ == "__main__":
    main()
