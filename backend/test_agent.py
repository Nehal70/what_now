"""Run agent test scenarios without starting the server."""

from dotenv import load_dotenv

load_dotenv()

from agent import run_agent

SCENARIOS = [
    {
        "name": "Scenario 1 — slip and fall, wrist pain",
        "transcript": "I just slipped on a wet floor at a grocery store, my wrist hurts",
        "history": [],
        "expected_tool": "safety_check",
    },
    {
        "name": "Scenario 2 — manager with form",
        "transcript": "I'm okay, the manager just came over and wants me to fill out a form",
        "history": [
            {"role": "user", "text": "I slipped on a wet floor"},
            {"role": "assistant", "text": "Are you safe? Can you move?"},
        ],
        "expected_tool": "scene_guide",
    },
    {
        "name": "Scenario 3 — lawyer in California",
        "transcript": "Should I get a lawyer? This is in California",
        "history": [],
        "expected_tool": "legal_tool",
    },
    {
        "name": "Scenario 4 — insurance claim",
        "transcript": "How do I file an insurance claim for this?",
        "history": [],
        "expected_tool": "insurance_tool",
    },
]


def main():
    for scenario in SCENARIOS:
        print(f"\n{'=' * 60}")
        print(scenario["name"])
        print(f"Expected tool: {scenario['expected_tool']}")
        print("-" * 60)
        try:
            result = run_agent(scenario["transcript"], scenario["history"])
            print(f"tool_called: {result.get('tool_called')}")
            print(f"reasoning: {result.get('reasoning')}")
            print(f"response: {result.get('response')[:500]}...")
            match = result.get("tool_called") == scenario["expected_tool"]
            print(f"Match: {'YES' if match else 'NO (may still be valid)'}")
        except Exception as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
