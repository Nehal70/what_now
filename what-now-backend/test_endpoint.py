"""Test /chat endpoint with the 4 standard scenarios."""

import httpx

BASE_URL = "http://localhost:8000"

SCENARIOS = [
    {
        "name": "Scenario 1",
        "payload": {
            "transcript": "I just slipped on a wet floor at a grocery store, my wrist hurts",
            "conversation_history": [],
        },
    },
    {
        "name": "Scenario 2",
        "payload": {
            "transcript": "I'm okay, the manager just came over and wants me to fill out a form",
            "conversation_history": [
                {"role": "user", "text": "I slipped on a wet floor"},
                {"role": "assistant", "text": "Are you safe? Can you move?"},
            ],
        },
    },
    {
        "name": "Scenario 3",
        "payload": {
            "transcript": "Should I get a lawyer? This is in California",
            "conversation_history": [],
        },
    },
    {
        "name": "Scenario 4",
        "payload": {
            "transcript": "How do I file an insurance claim for this?",
            "conversation_history": [],
        },
    },
    {
        "name": "__START__ handler",
        "payload": {
            "transcript": "__START__",
            "conversation_history": [],
        },
    },
]


def main():
    for scenario in SCENARIOS:
        print(f"\n{'=' * 60}")
        print(scenario["name"])
        print("-" * 60)
        try:
            response = httpx.post(f"{BASE_URL}/chat", json=scenario["payload"], timeout=120.0)
            print(response.json())
        except Exception as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
