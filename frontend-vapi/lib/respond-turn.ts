import { emitEvent, emitSessionEvent } from "@/lib/events";
import { fetchFromBackendChatStream, type BackendDone } from "@/lib/backend-chat";
import { scheduleDemoLegalFallback } from "@/lib/demo-nearby";
import {
  appendMessage,
  buildSessionTitle,
  getSessionById,
  updateSessionCallContext,
  updateSessionPhase,
  updateSessionTitle,
} from "@/lib/sessions";
import type {
  CallContext,
  ConversationMessage,
  SessionImagePayload,
  SSEEvent,
  UserLocation,
} from "@/lib/types";
import { IMAGE_UPLOAD_TOKEN, START_TOKEN } from "@/lib/types";

function userFacingTranscript(transcript: string, imageCount?: number): string {
  if (transcript === IMAGE_UPLOAD_TOKEN) {
    const count = imageCount ?? 1;
    return count === 1 ? "📷 Sent 1 photo" : `📷 Sent ${count} photos`;
  }

  return transcript;
}

function buildTurnEvents(
  transcript: string,
  result: BackendDone,
  imageCount?: number,
): SSEEvent[] {
  const events: SSEEvent[] = [];

  if (transcript !== START_TOKEN) {
    events.push({
      type: "transcript",
      data: {
        role: "user",
        text: userFacingTranscript(transcript, imageCount),
      },
      timestamp: Date.now(),
    });
  }

  events.push(
    {
      type: "call_state",
      data: { state: "thinking" },
      timestamp: Date.now(),
    },
    {
      type: "tool",
      data: { tool_called: result.tool_called },
      timestamp: Date.now(),
    },
    {
      type: "reasoning",
      data: { reasoning: result.reasoning },
      timestamp: Date.now(),
    },
    {
      type: "latency",
      data: { latency_ms: result.latency_ms },
      timestamp: Date.now(),
    },
    {
      type: "phase",
      data: { phase: result.phase },
      timestamp: Date.now(),
    },
    {
      type: "transcript",
      data: { role: "assistant", text: result.response },
      timestamp: Date.now(),
    },
    {
      type: "call_state",
      data: { state: "speaking" },
      timestamp: Date.now(),
    },
  );

  if (result.context.awaiting_image) {
    events.push({
      type: "image_requested",
      data: {
        prompt: result.context.image_prompt ?? "Upload photos in the app",
      },
      timestamp: Date.now(),
    });
  }

  return events;
}

function emitTurnEvents(
  sessionId: string | null,
  events: SSEEvent[],
): void {
  for (const event of events) {
    if (sessionId) {
      emitSessionEvent(sessionId, event);
    } else {
      emitEvent(event);
    }
  }
}

async function persistTurn(
  sessionId: string,
  transcript: string,
  result: BackendDone,
  imageCount?: number,
): Promise<void> {
  const session = await getSessionById(sessionId);
  if (!session) {
    throw new Error("Session not found");
  }

  if (transcript !== START_TOKEN) {
    await appendMessage({
      sessionId,
      role: "user",
      text: userFacingTranscript(transcript, imageCount),
    });

    if (
      transcript !== IMAGE_UPLOAD_TOKEN &&
      (!session.title || session.title === "Phone call")
    ) {
      await updateSessionTitle(sessionId, buildSessionTitle(transcript));
    }
  }

  await appendMessage({
    sessionId,
    role: "assistant",
    text: result.response,
  });

  if (result.phase) {
    await updateSessionPhase(sessionId, result.phase);
  }

  await updateSessionCallContext(sessionId, result.context);
}

export type ExecuteTurnInput = {
  sessionId: string | null;
  transcript: string;
  conversation_history: ConversationMessage[];
  context: CallContext;
  location?: UserLocation | null;
  images?: SessionImagePayload[] | null;
  imageCount?: number;
};

export type ExecuteTurnResult = BackendDone;

export async function executeRespondTurn(
  input: ExecuteTurnInput,
): Promise<ExecuteTurnResult> {
  const {
    sessionId,
    transcript,
    conversation_history,
    context,
    location = null,
    images = null,
    imageCount,
  } = input;

  const result = await fetchFromBackendChatStream({
    transcript,
    conversation_history,
    context,
    location,
    images,
    sessionId,
  });

  if (sessionId) {
    await persistTurn(sessionId, transcript, result, imageCount);
  }

  const events = buildTurnEvents(transcript, result, imageCount);
  emitTurnEvents(sessionId, events);

  if (result.tool_called === "legal_tool") {
    scheduleDemoLegalFallback();
  }

  return result;
}
