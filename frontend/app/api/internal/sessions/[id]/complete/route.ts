import { NextResponse } from "next/server";

import { verifyInternalAuth } from "@/lib/internal-auth";
import { completeSession } from "@/lib/sessions";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function PATCH(request: Request, context: RouteContext) {
  if (!verifyInternalAuth(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { id } = await context.params;
    const session = await completeSession(id);

    return NextResponse.json({
      session_id: session.id,
      status: session.status,
      ended_at: session.endedAt,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
