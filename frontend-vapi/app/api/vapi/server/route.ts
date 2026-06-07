import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Proxy Vapi Server URL webhooks (inbound phone assistant-request) to backend. */
export async function POST(request: Request) {
  const backend = process.env.BACKEND_ENDPOINT?.replace(/\/$/, "");
  if (!backend) {
    return NextResponse.json(
      { error: "BACKEND_ENDPOINT is not configured" },
      { status: 500 },
    );
  }

  try {
    const body = await request.text();
    const res = await fetch(`${backend}/vapi/server`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      },
      body,
    });

    const payload = await res.text();
    return new NextResponse(payload, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
