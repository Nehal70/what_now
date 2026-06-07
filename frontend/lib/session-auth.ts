import { createClient } from "@/lib/supabase/server";
import { getSessionById } from "@/lib/sessions";
import type { Session } from "@/lib/types";

export async function requireUserSession(
  sessionId: string,
): Promise<{ userId: string; session: Session } | null> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return null;
  }

  const session = await getSessionById(sessionId);
  if (!session || session.userId !== user.id) {
    return null;
  }

  return { userId: user.id, session };
}
