import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { listSessionsForUser } from "@/lib/sessions";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { active, past } = await listSessionsForUser(user.id);
    return NextResponse.json({ active, past });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
