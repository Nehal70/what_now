import { getSessionCallContext } from "@/lib/sessions";
import type { CallContext } from "@/lib/types";

/**
 * Supabase sessions.call_context is the source of truth for incident stack state.
 * Agent-in-memory context is merged underneath so DB fields win on conflict.
 */
export function mergeCallContext(
  agentContext: CallContext,
  dbContext: CallContext,
): CallContext {
  return { ...agentContext, ...dbContext };
}

export async function resolveCallContextForTurn(
  sessionId: string | null,
  agentContext: CallContext,
): Promise<CallContext> {
  if (!sessionId) {
    return agentContext;
  }

  try {
    const dbContext = await getSessionCallContext(sessionId);
    return mergeCallContext(agentContext, dbContext);
  } catch {
    return agentContext;
  }
}
