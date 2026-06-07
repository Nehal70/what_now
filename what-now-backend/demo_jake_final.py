"""Final demo script — Jake rear-end / Austin TX / State Farm / Progressive."""

import json
import subprocess
import time

TURNS = [
    ("START", "__START__"),
    (
        "1",
        "I just got rear ended at a red light. My neck really hurts.",
    ),
    (
        "2",
        "Yeah I can move. I'm still here. The other driver is being super friendly, wants to skip the police.",
    ),
    (
        "3",
        "I'm in Austin Texas. He keeps saying it's minor.",
    ),
    (
        "4",
        "Not yet. Police just arrived and filed a report. His insurance is State Farm.",
    ),
    (
        "5",
        "My neck is getting worse. I'm worried about the medical bills — will my insurance cover this?",
    ),
    (
        "6",
        "State Farm just texted me a $4,000 settlement offer. Should I take it?",
    ),
]

EXPECTED = {
    1: "neck pain after a rear-end",
    2: "police report",
    3: "sign anything",
    4: "State Farm will call you within the hour",
    5: "MedPay",
    6: "Don't take it",
}


def call(transcript: str, history: list[dict], session_id: str | None) -> dict:
    body: dict = {"transcript": transcript, "conversation_history": history}
    if session_id:
        body["session_id"] = session_id
    if transcript == "__START__":
        body["location"] = {"lat": 30.2672, "lng": -97.7431}
    proc = subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            "http://localhost:8000/chat",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(body),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return json.loads(proc.stdout)


def main() -> None:
    history: list[dict] = []
    session_id: str | None = None
    print("=== WHAT NOW — FINAL DEMO SCRIPT ===\n")
    all_ok = True

    for label, transcript in TURNS:
        time.sleep(0.2)
        done = call(transcript, history, session_id)
        session_id = done.get("session_id") or session_id
        phase = done.get("phase")
        tool = done.get("tool_called")
        ms = done.get("latency_ms", 0)
        resp = done.get("response", "")

        ok = True
        if label in EXPECTED:
            ok = EXPECTED[label] in resp
            if not ok:
                all_ok = False

        print(f"{'Agent' if label == 'START' else f'Turn {label}'} [{phase}, {tool}, {ms}ms] {'✓' if ok else '✗'}:")
        print(resp)
        if label not in ("START",):
            ctx = done.get("context") or {}
            print(
                f"  → {ctx.get('incident_type')} | {ctx.get('state')} | "
                f"injuries={ctx.get('injuries')} | scene={ctx.get('still_at_scene')} | "
                f"carrier={ctx.get('other_carrier')} | tools={ctx.get('tools_fired')}"
            )
        print()

        if transcript != "__START__":
            history.append({"role": "user", "text": transcript})
            history.append({"role": "assistant", "text": resp})
        else:
            history.append({"role": "assistant", "text": resp})

    print(f"DEMO SCRIPT MATCH: {'YES' if all_ok else 'NO'}")


if __name__ == "__main__":
    main()
