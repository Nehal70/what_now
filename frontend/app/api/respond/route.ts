import { NextResponse } from "next/server";

import { getUserLocation } from "@/lib/location-store";
import { executeRespondTurn } from "@/lib/respond-turn";
import { getSessionById } from "@/lib/sessions";
import type { CallContext, ConversationMessage } from "@/lib/types";
import { START_TOKEN } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      session_id?: string;
      transcript?: string;
      conversation_history?: ConversationMessage[];
      context?: CallContext;
    };

    const sessionId = body.session_id ?? null;
    const transcript = body.transcript ?? "";
    const conversation_history = body.conversation_history ?? [];
    const context = body.context ?? {};

    let session = null;
    if (sessionId) {
      session = await getSessionById(sessionId);
      if (!session) {
        return NextResponse.json({ error: "Session not found" }, { status: 404 });
      }
    }

    let location = null;
    if (transcript === START_TOKEN && session) {
      location = getUserLocation(session.userId);
    }

    const result = await executeRespondTurn({
      sessionId,
      transcript,
      conversation_history,
      context,
      location,
    });

    return NextResponse.json({
      response: result.response,
      tool_called: result.tool_called,
      reasoning: result.reasoning,
      latency_ms: result.latency_ms,
      phase: result.phase,
      context: result.context,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
