import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const backend = process.env.BACKEND_ENDPOINT;

  if (!backend) {
    return NextResponse.json(
      { active_model: "unknown" },
      { status: 200 },
    );
  }

  try {
    const res = await fetch(`${backend}/model`, {
      headers: { "ngrok-skip-browser-warning": "true" },
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json(
        { active_model: "unavailable" },
        { status: 200 },
      );
    }

    const data = (await res.json()) as { active_model?: string };
    return NextResponse.json({
      active_model: data.active_model ?? "unknown",
    });
  } catch {
    return NextResponse.json({ active_model: "unavailable" }, { status: 200 });
  }
}
