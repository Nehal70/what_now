import type { BackendDone } from "@/lib/backend-chat";
import type { SSEEvent } from "@/lib/types";

export function buildDashboardTurnEvents(
  transcript: string,
  result: BackendDone,
): SSEEvent[] {
  const ts = Date.now();
  const events: SSEEvent[] = [
    {
      type: "call_state",
      data: { state: "thinking" },
      timestamp: ts,
    },
    {
      type: "tool",
      data: { tool_called: result.tool_called },
      timestamp: ts,
    },
    {
      type: "reasoning",
      data: { reasoning: result.reasoning },
      timestamp: ts,
    },
    {
      type: "latency",
      data: { latency_ms: result.latency_ms },
      timestamp: ts,
    },
    {
      type: "phase",
      data: { phase: result.phase },
      timestamp: ts,
    },
    {
      type: "transcript",
      data: { role: "assistant", text: result.response },
      timestamp: ts,
    },
    {
      type: "call_state",
      data: { state: "speaking" },
      timestamp: ts,
    },
  ];

  if (transcript.trim()) {
    events.unshift({
      type: "transcript",
      data: { role: "user", text: transcript },
      timestamp: ts,
    });
  }

  return events;
}
