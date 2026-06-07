import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const backend = process.env.BACKEND_ENDPOINT;

  if (!backend) {
    return NextResponse.json(
      { active_model: process.env.LLM_MODEL ?? "qwen3.6-flash" },
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
        { active_model: process.env.LLM_MODEL ?? "qwen3.6-flash" },
        { status: 200 },
      );
    }

    const data = (await res.json()) as { active_model?: string };
    const model = data.active_model;
    return NextResponse.json({
      active_model:
        model && model !== "unavailable" ? model : process.env.LLM_MODEL ?? "qwen3.6-flash",
    });
  } catch {
    return NextResponse.json(
      { active_model: process.env.LLM_MODEL ?? "qwen3.6-flash" },
      { status: 200 },
    );
  }
}
