import { NextResponse } from "next/server";

import { emitEvent } from "@/lib/events";
import { verifyInternalAuth } from "@/lib/internal-auth";
import { markNearbyShown } from "@/lib/demo-nearby";
import type { SSEEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!verifyInternalAuth(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = (await request.json()) as { events?: SSEEvent[] };
    const events = body.events ?? [];
    for (const event of events) {
      if (event.type === "nearby_medical" || event.type === "nearby_legal") {
        markNearbyShown(event.type);
        console.log("[SSE] Internal event:", event.type, event.data);
      }
      emitEvent(event);
    }
    return NextResponse.json({ ok: true, count: events.length });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
