import { NextResponse } from "next/server";

import { emitEvent } from "@/lib/events";
import type { SSEEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

/** Push dashboard events from the browser call page (same-origin). */
export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { events?: SSEEvent[] };
    const events = body.events ?? [];
    for (const event of events) {
      emitEvent(event);
    }
    return NextResponse.json({ ok: true, count: events.length });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
