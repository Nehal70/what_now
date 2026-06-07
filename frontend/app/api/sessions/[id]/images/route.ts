import { NextResponse } from "next/server";

import { emitEvent, emitSessionEvent } from "@/lib/events";
import { requireUserSession } from "@/lib/session-auth";
import {
  buildSessionImageStoragePath,
  createPreviewSignedUrl,
  insertStagedSessionImage,
  SESSION_IMAGE_LIMITS,
} from "@/lib/session-images";
import { createAdminClient } from "@/lib/supabase/admin";

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

    const formData = await request.formData();
    const file = formData.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "Missing file" }, { status: 400 });
    }

    if (!SESSION_IMAGE_LIMITS.allowedMimeTypes.has(file.type)) {
      return NextResponse.json({ error: "Unsupported file type" }, { status: 400 });
    }

    if (file.size > SESSION_IMAGE_LIMITS.maxBytes) {
      return NextResponse.json({ error: "File too large (max 5MB)" }, { status: 400 });
    }

    const ext = file.type === "image/png"
      ? "png"
      : file.type === "image/webp"
        ? "webp"
        : "jpg";
    const fileName = `${crypto.randomUUID()}.${ext}`;
    const storagePath = buildSessionImageStoragePath(
      auth.userId,
      sessionId,
      fileName,
    );

    const admin = createAdminClient();
    const buffer = Buffer.from(await file.arrayBuffer());
    const { error: uploadError } = await admin.storage
      .from("session-images")
      .upload(storagePath, buffer, {
        contentType: file.type,
        upsert: false,
      });

    if (uploadError) {
      return NextResponse.json({ error: uploadError.message }, { status: 500 });
    }

    const record = await insertStagedSessionImage({
      sessionId,
      userId: auth.userId,
      storagePath,
      mimeType: file.type,
    });

    const previewUrl = await createPreviewSignedUrl(storagePath);

    const event = {
      type: "image_received" as const,
      data: {
        id: record.id,
        preview_url: previewUrl,
        mime_type: record.mimeType,
      },
      timestamp: Date.now(),
    };

    emitSessionEvent(sessionId, event);
    emitEvent(event);

    return NextResponse.json({
      id: record.id,
      preview_url: previewUrl,
      mime_type: record.mimeType,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
