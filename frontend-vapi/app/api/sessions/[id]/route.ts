import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { getMessagesForSession, getSessionById } from "@/lib/sessions";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { id } = await context.params;
    const session = await getSessionById(id);

    if (!session || session.userId !== user.id) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    const messages = await getMessagesForSession(id);

    return NextResponse.json({ session, messages });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
