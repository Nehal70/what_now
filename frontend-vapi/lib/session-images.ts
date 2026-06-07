import { createAdminClient } from "@/lib/supabase/admin";
import type { SessionImagePayload, SessionImageRecord } from "@/lib/types";

const BUCKET = "session-images";
const SIGNED_URL_TTL_SEC = 3600;

type SessionImageRow = {
  id: string;
  session_id: string;
  user_id: string;
  storage_path: string;
  mime_type: string;
  status: "staged" | "sent";
  created_at: string;
  sent_at: string | null;
};

function mapRow(row: SessionImageRow): SessionImageRecord {
  return {
    id: row.id,
    sessionId: row.session_id,
    userId: row.user_id,
    storagePath: row.storage_path,
    mimeType: row.mime_type,
    status: row.status,
    createdAt: row.created_at,
    sentAt: row.sent_at,
  };
}

export async function insertStagedSessionImage(input: {
  sessionId: string;
  userId: string;
  storagePath: string;
  mimeType: string;
}): Promise<SessionImageRecord> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("session_images")
    .insert({
      session_id: input.sessionId,
      user_id: input.userId,
      storage_path: input.storagePath,
      mime_type: input.mimeType,
      status: "staged",
    })
    .select("*")
    .single();

  if (error) {
    throw new Error(error.message);
  }

  return mapRow(data as SessionImageRow);
}

export async function getStagedImagesForSession(
  sessionId: string,
  imageIds: string[],
): Promise<SessionImageRecord[]> {
  if (imageIds.length === 0) {
    return [];
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("session_images")
    .select("*")
    .eq("session_id", sessionId)
    .eq("status", "staged")
    .in("id", imageIds);

  if (error) {
    throw new Error(error.message);
  }

  return (data ?? []).map((row) => mapRow(row as SessionImageRow));
}

export async function markSessionImagesSent(
  imageIds: string[],
): Promise<void> {
  if (imageIds.length === 0) {
    return;
  }

  const admin = createAdminClient();
  const { error } = await admin
    .from("session_images")
    .update({
      status: "sent",
      sent_at: new Date().toISOString(),
    })
    .in("id", imageIds);

  if (error) {
    throw new Error(error.message);
  }
}

export async function createSignedUrl(storagePath: string): Promise<string> {
  const admin = createAdminClient();
  const { data, error } = await admin.storage
    .from(BUCKET)
    .createSignedUrl(storagePath, SIGNED_URL_TTL_SEC);

  if (error || !data?.signedUrl) {
    throw new Error(error?.message ?? "Failed to create signed URL");
  }

  return data.signedUrl;
}

export async function createPreviewSignedUrl(
  storagePath: string,
): Promise<string> {
  return createSignedUrl(storagePath);
}

export async function toBackendImagePayload(
  images: SessionImageRecord[],
): Promise<SessionImagePayload[]> {
  const payloads = await Promise.all(
    images.map(async (image) => ({
      id: image.id,
      url: await createSignedUrl(image.storagePath),
      mime_type: image.mimeType,
      uploaded_at: new Date(image.createdAt).getTime(),
    })),
  );

  return payloads;
}

export function buildSessionImageStoragePath(
  userId: string,
  sessionId: string,
  fileName: string,
): string {
  return `${userId}/${sessionId}/${fileName}`;
}

export const SESSION_IMAGE_LIMITS = {
  maxPerSend: 3,
  maxBytes: 5 * 1024 * 1024,
  allowedMimeTypes: new Set([
    "image/jpeg",
    "image/png",
    "image/webp",
  ]),
};
