"""Final demo script — Jake rear-end / State Farm / Progressive MedPay."""

import json
import subprocess
import time

TURNS = [
    ("START", "__START__"),
    ("1", "My neck really hurts but I can move. I just got rear ended at a red light."),
    ("2", "Yes I'm still here. The other driver is super apologetic, wants to skip the police and just swap info."),
    ("3", "Austin Texas. He keeps saying it's minor."),
    ("4", "Not yet. His insurance is State Farm."),
    ("5→6", "Yeah one person nearby saw the whole thing."),  # user Turn 5 → agent Turn 6 fires
    ("7", "What's this case actually worth? State Farm just texted me $4,000."),
]


def call(transcript: str, history: list[dict], session_id: str | None) -> dict:
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


def main() -> None:
    history: list[dict] = []
    session_id: str | None = None
    print("=== WHAT NOW — FINAL DEMO ===\n")

    for label, transcript in TURNS:
        time.sleep(0.3)
        done = call(transcript, history, session_id)
        session_id = done.get("session_id") or session_id
        phase = done.get("phase")
        tool = done.get("tool_called")
        ms = done.get("latency_ms", 0)
        resp = done.get("response", "")

        print(f"{'Agent' if label == 'START' else f'Turn {label}'} [{phase}, {tool}, {ms}ms]:")
        print(resp)
        if label not in ("START",):
            ctx = done.get("context") or {}
            print(
                f"  → {ctx.get('incident_type')} | {ctx.get('state')} | "
                f"scene={ctx.get('still_at_scene')} | signed={ctx.get('signed_anything')} | "
                f"witness={ctx.get('witnesses')} | carrier={ctx.get('other_carrier')}"
            )
        print()

        if transcript != "__START__":
            history.append({"role": "user", "text": transcript})
            history.append({"role": "assistant", "text": resp})


if __name__ == "__main__":
    main()
