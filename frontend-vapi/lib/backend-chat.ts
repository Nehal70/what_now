import { emitEvent, emitSessionEvent } from "@/lib/events";
import { DEMO_LOCATION, markNearbyShown } from "@/lib/demo-nearby";
import type {
  CallContext,
  ConversationMessage,
  SessionImagePayload,
  SSEEvent,
  ToolName,
  UserLocation,
} from "@/lib/types";
import { IMAGE_UPLOAD_TOKEN, START_TOKEN } from "@/lib/types";

export type BackendDone = {
  response: string;
  tool_called: ToolName;
  reasoning: string;
  latency_ms: number;
  phase: string;
  context: CallContext;
};

type StreamSideEffect = (event: SSEEvent) => void;

function buildBackendBody(
  transcript: string,
  conversation_history: ConversationMessage[],
  context: CallContext,
  location: UserLocation | null,
  images: SessionImagePayload[] | null,
): string {
  const payload: Record<string, unknown> = {
    transcript,
    conversation_history,
    context,
  };

  if (transcript === START_TOKEN) {
    payload.location = location ?? DEMO_LOCATION;
  }

  if (transcript === IMAGE_UPLOAD_TOKEN && images && images.length > 0) {
    payload.images = images;
  }

  return JSON.stringify(payload);
}

const PASSTHROUGH_SSE_TYPES = new Set([
  "image_requested",
  "image_processed",
  "nearby_medical",
  "nearby_legal",
]);

function handlePassthroughEvent(
  parsed: {
    type?: string;
    data?: unknown;
    timestamp?: number;
  },
  onSideEffect: StreamSideEffect,
): void {
  if (
    !parsed.type ||
    !PASSTHROUGH_SSE_TYPES.has(parsed.type) ||
    !parsed.data
  ) {
    return;
  }

  console.log("[SSE] Event received:", parsed.type, parsed.data);
  markNearbyShown(parsed.type as "nearby_medical" | "nearby_legal");
  onSideEffect({
    type: parsed.type as SSEEvent["type"],
    data: parsed.data,
    timestamp: parsed.timestamp ?? Date.now(),
  });
}

function parseSseLines(
  lines: string[],
  onSideEffect: StreamSideEffect,
): void {
  for (const line of lines) {
    if (!line.startsWith("data: ")) continue;
    const raw = line.slice(6).trim();
    if (!raw) continue;

    try {
      const parsed = JSON.parse(raw) as {
        type?: string;
        data?: unknown;
        timestamp?: number;
      };
      handlePassthroughEvent(parsed, onSideEffect);
    } catch {
      // skip malformed SSE lines
    }
  }
}

/** Keep reading after `done` so Apify side events still reach the dashboard. */
async function drainRemainingStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  initialBuffer: string,
  onSideEffect: StreamSideEffect,
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = initialBuffer;

  try {
    while (true) {
      const { done: streamDone, value } = await reader.read();
      if (streamDone) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      parseSseLines(lines, onSideEffect);
    }

    if (buffer.trim()) {
      parseSseLines([buffer], onSideEffect);
    }
  } catch {
    // stream may close when Apify timeout elapses
  }
}

export async function fetchFromBackendChatStream(input: {
  transcript: string;
  conversation_history: ConversationMessage[];
  context: CallContext;
  location?: UserLocation | null;
  images?: SessionImagePayload[] | null;
  sessionId?: string | null;
}): Promise<BackendDone> {
  const backend = process.env.BACKEND_ENDPOINT;
  if (!backend) {
    throw new Error("BACKEND_ENDPOINT is not configured");
  }

  const {
    transcript,
    conversation_history,
    context,
    location = null,
    images = null,
    sessionId = null,
  } = input;

  const onSideEffect: StreamSideEffect = (event) => {
    if (sessionId) {
      emitSessionEvent(sessionId, event);
    }
    emitEvent(event);
  };

  const res = await fetch(`${backend}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true",
    },
    body: buildBackendBody(
      transcript,
      conversation_history,
      context,
      location,
      images,
    ),
  });

  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Backend response has no body");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let fullResponse = "";
  let doneResult: BackendDone | null = null;

  while (true) {
    const { done: streamDone, value } = await reader.read();
    if (streamDone) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;

      try {
        const parsed = JSON.parse(raw) as {
          type?: string;
          content?: string;
          data?: unknown;
          response?: string;
          tool_called?: ToolName;
          reasoning?: string;
          latency_ms?: number;
          phase?: string;
          context?: CallContext;
          timestamp?: number;
        };

        if (parsed.type === "token" && parsed.content) {
          fullResponse += parsed.content;
          continue;
        }

        handlePassthroughEvent(parsed, onSideEffect);

        if (parsed.type === "done") {
          doneResult = {
            response: parsed.response ?? fullResponse,
            tool_called: parsed.tool_called ?? null,
            reasoning: parsed.reasoning ?? "",
            latency_ms: parsed.latency_ms ?? 0,
            phase: parsed.phase ?? "",
            context: parsed.context ?? context,
          };
          void drainRemainingStream(reader, buffer, onSideEffect);
          break;
        }
      } catch {
        // skip malformed SSE lines
      }
    }

    if (doneResult) break;
  }

  if (doneResult) {
    return doneResult;
  }

  return {
    response: fullResponse,
    tool_called: null,
    reasoning: "",
    latency_ms: 0,
    phase: "",
    context,
  };
}
