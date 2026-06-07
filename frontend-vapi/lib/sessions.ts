import { createAdminClient } from "@/lib/supabase/admin";
import type {
  CallContext,
  ConversationMessage,
  Session,
  SessionMessage,
  SessionStatus,
} from "@/lib/types";

type SessionRow = {
  id: string;
  user_id: string;
  status: SessionStatus;
  caller_phone: string;
  livekit_room: string | null;
  phase: string | null;
  title: string | null;
  started_at: string;
  ended_at: string | null;
  call_context?: CallContext | null;
};

type MessageRow = {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  text: string;
  created_at: string;
};

function mapSession(row: SessionRow): Session {
  return {
    id: row.id,
    userId: row.user_id,
    status: row.status,
    callerPhone: row.caller_phone,
    livekitRoom: row.livekit_room,
    phase: row.phase,
    title: row.title,
    startedAt: row.started_at,
    endedAt: row.ended_at,
  };
}

function mapMessage(row: MessageRow): SessionMessage {
  return {
    id: row.id,
    sessionId: row.session_id,
    role: row.role,
    text: row.text,
    createdAt: row.created_at,
  };
}

export function buildSessionTitle(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return "Phone call";
  }
  return trimmed.length > 60 ? `${trimmed.slice(0, 57)}...` : trimmed;
}

export async function findUserIdByPhone(
  phoneE164: string,
): Promise<string | null> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("profiles")
    .select("user_id")
    .eq("phone_e164", phoneE164)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data?.user_id ?? null;
}

export async function getActiveSessionForUser(
  userId: string,
): Promise<Session | null> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("sessions")
    .select("*")
    .eq("user_id", userId)
    .eq("status", "active")
    .order("started_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data ? mapSession(data as SessionRow) : null;
}

export async function createSessionFromCall(input: {
  userId: string;
  callerPhone: string;
  livekitRoom: string | null;
}): Promise<Session> {
  const admin = createAdminClient();

  const existing = await getActiveSessionForUser(input.userId);
  if (existing) {
    return existing;
  }

  const { data, error } = await admin
    .from("sessions")
    .insert({
      user_id: input.userId,
      caller_phone: input.callerPhone,
      livekit_room: input.livekitRoom,
      status: "active",
      title: "Phone call",
    })
    .select("*")
    .single();

  if (error) {
    throw new Error(error.message);
  }

  return mapSession(data as SessionRow);
}

export async function completeSession(sessionId: string): Promise<Session> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("sessions")
    .update({
      status: "completed",
      ended_at: new Date().toISOString(),
    })
    .eq("id", sessionId)
    .select("*")
    .single();

  if (error) {
    throw new Error(error.message);
  }

  return mapSession(data as SessionRow);
}

export async function getSessionById(sessionId: string): Promise<Session | null> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("sessions")
    .select("*")
    .eq("id", sessionId)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data ? mapSession(data as SessionRow) : null;
}

export async function listSessionsForUser(userId: string): Promise<{
  active: Session | null;
  past: Session[];
}> {
  const admin = createAdminClient();

  const [activeResult, pastResult] = await Promise.all([
    admin
      .from("sessions")
      .select("*")
      .eq("user_id", userId)
      .eq("status", "active")
      .order("started_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
    admin
      .from("sessions")
      .select("*")
      .eq("user_id", userId)
      .eq("status", "completed")
      .order("started_at", { ascending: false })
      .limit(20),
  ]);

  if (activeResult.error) {
    throw new Error(activeResult.error.message);
  }
  if (pastResult.error) {
    throw new Error(pastResult.error.message);
  }

  return {
    active: activeResult.data
      ? mapSession(activeResult.data as SessionRow)
      : null,
    past: (pastResult.data ?? []).map((row) => mapSession(row as SessionRow)),
  };
}

export async function getMessagesForSession(
  sessionId: string,
): Promise<SessionMessage[]> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("messages")
    .select("*")
    .eq("session_id", sessionId)
    .order("created_at", { ascending: true });

  if (error) {
    throw new Error(error.message);
  }

  return (data ?? []).map((row) => mapMessage(row as MessageRow));
}

export async function appendMessage(input: {
  sessionId: string;
  role: "user" | "assistant";
  text: string;
}): Promise<SessionMessage> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("messages")
    .insert({
      session_id: input.sessionId,
      role: input.role,
      text: input.text,
    })
    .select("*")
    .single();

  if (error) {
    throw new Error(error.message);
  }

  return mapMessage(data as MessageRow);
}

export async function updateSessionPhase(
  sessionId: string,
  phase: string,
): Promise<void> {
  const admin = createAdminClient();
  const { error } = await admin
    .from("sessions")
    .update({ phase })
    .eq("id", sessionId);

  if (error) {
    throw new Error(error.message);
  }
}

export async function updateSessionTitle(
  sessionId: string,
  title: string,
): Promise<void> {
  const admin = createAdminClient();
  const { error } = await admin
    .from("sessions")
    .update({ title })
    .eq("id", sessionId);

  if (error) {
    throw new Error(error.message);
  }
}

export async function getSessionCallContext(
  sessionId: string,
): Promise<CallContext> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("sessions")
    .select("call_context")
    .eq("id", sessionId)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  const raw = data?.call_context;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return {};
  }

  return raw as CallContext;
}

export async function updateSessionCallContext(
  sessionId: string,
  context: CallContext,
): Promise<void> {
  const admin = createAdminClient();
  const { error } = await admin
    .from("sessions")
    .update({ call_context: context })
    .eq("id", sessionId);

  if (error) {
    throw new Error(error.message);
  }
}

export async function getConversationHistoryForSession(
  sessionId: string,
): Promise<ConversationMessage[]> {
  const messages = await getMessagesForSession(sessionId);
  return messages.map((message) => ({
    role: message.role,
    text: message.text,
  }));
}
