import { emitEvent, emitSessionEvent } from "@/lib/events";
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
  sessionId: string | null,
): string {
  const payload: Record<string, unknown> = {
    transcript,
    conversation_history,
    context,
  };

  if (sessionId) {
    payload.session_id = sessionId;
  }

  if (transcript === START_TOKEN && location) {
    payload.location = location;
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
      sessionId,
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

  outer: while (true) {
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

        if (
          parsed.type &&
          PASSTHROUGH_SSE_TYPES.has(parsed.type) &&
          parsed.data
        ) {
          onSideEffect({
            type: parsed.type as SSEEvent["type"],
            data: parsed.data,
            timestamp: parsed.timestamp ?? Date.now(),
          });
          continue;
        }

        if (parsed.type === "done") {
          doneResult = {
            response: parsed.response ?? fullResponse,
            tool_called: parsed.tool_called ?? null,
            reasoning: parsed.reasoning ?? "",
            latency_ms: parsed.latency_ms ?? 0,
            phase: parsed.phase ?? "",
            context: parsed.context ?? context,
          };
          break outer;
        }
      } catch {
        // skip malformed SSE lines
      }
    }
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
