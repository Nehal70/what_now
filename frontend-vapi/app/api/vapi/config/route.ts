import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function backendBase(): string {
  return (
    process.env.NEXT_PUBLIC_BACKEND_ENDPOINT ??
    process.env.BACKEND_ENDPOINT ??
    ""
  ).replace(/\/$/, "");
}

/** Server-side Vapi config — browser SDK needs the public API key. */
export async function GET() {
  const apiKey =
    process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ??
    process.env.VAPI_PUBLIC_KEY ??
    process.env.NEXT_PUBLIC_VAPI_API_KEY ??
    process.env.VAPI_API_KEY ??
    "";

  const base = backendBase();
  // Vapi appends /chat/completions — base must be .../vapi not .../vapi/chat
  const customLlmUrl = base ? `${base}/vapi` : "";
  const serverUrl = base ? `${base}/vapi/server` : "";

  return NextResponse.json({
    apiKey,
    assistantId: process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID ?? "",
    useInlineAssistant: process.env.VAPI_USE_INLINE_ASSISTANT !== "false",
    customLlmUrl,
    serverUrl,
    phoneNumber:
      process.env.NEXT_PUBLIC_PHONE_NUMBER ??
      process.env.VAPI_PHONE_NUMBER ??
      "",
    debug: process.env.VAPI_DEBUG === "true",
  });
}
