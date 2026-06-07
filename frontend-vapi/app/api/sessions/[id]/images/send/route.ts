import { NextResponse } from "next/server";

import { executeRespondTurn } from "@/lib/respond-turn";
import { requireUserSession } from "@/lib/session-auth";
import {
  getStagedImagesForSession,
  markSessionImagesSent,
  SESSION_IMAGE_LIMITS,
  toBackendImagePayload,
} from "@/lib/session-images";
import {
  getConversationHistoryForSession,
  getSessionCallContext,
} from "@/lib/sessions";
import { IMAGE_UPLOAD_TOKEN } from "@/lib/types";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(request: Request, routeContext: RouteContext) {
  try {
    const { id: sessionId } = await routeContext.params;
    const auth = await requireUserSession(sessionId);

    if (!auth) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    if (auth.session.status !== "active") {
      return NextResponse.json(
        { error: "Session is not active" },
        { status: 400 },
      );
    }

    const body = (await request.json()) as { image_ids?: string[] };
    const imageIds = body.image_ids ?? [];

    if (imageIds.length === 0) {
      return NextResponse.json({ error: "No images selected" }, { status: 400 });
    }

    if (imageIds.length > SESSION_IMAGE_LIMITS.maxPerSend) {
      return NextResponse.json(
        { error: `Maximum ${SESSION_IMAGE_LIMITS.maxPerSend} images per send` },
        { status: 400 },
      );
    }

    const staged = await getStagedImagesForSession(sessionId, imageIds);

    if (staged.length !== imageIds.length) {
      return NextResponse.json(
        { error: "One or more images were not found or already sent" },
        { status: 400 },
      );
    }

    const images = await toBackendImagePayload(staged);
    const conversation_history = await getConversationHistoryForSession(sessionId);
    const context = await getSessionCallContext(sessionId);

    const result = await executeRespondTurn({
      sessionId,
      transcript: IMAGE_UPLOAD_TOKEN,
      conversation_history,
      context,
      images,
      imageCount: staged.length,
    });

    await markSessionImagesSent(staged.map((image) => image.id));

    return NextResponse.json({
      ok: true,
      response: result.response,
      context: result.context,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
