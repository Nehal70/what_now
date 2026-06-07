import { NextResponse } from "next/server";

import {
  DEMO_LOCATION,
  scheduleDemoNearbyFallback,
} from "@/lib/demo-nearby";
import {
  clientIpFromRequest,
  resolveLocationFromIp,
} from "@/lib/resolve-ip-location";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const backend = process.env.BACKEND_ENDPOINT;
  if (!backend) {
    return NextResponse.json(
      { error: "BACKEND_ENDPOINT is not configured" },
      { status: 500 },
    );
  }

  try {
    const body = (await request.json()) as {
      lat?: number;
      lng?: number;
      call_id?: string;
    };

    let lat = body.lat;
    let lng = body.lng;
    let source: "ip" | "demo_default" | "client" = "client";

    if (
      typeof lat !== "number" ||
      typeof lng !== "number" ||
      !Number.isFinite(lat) ||
      !Number.isFinite(lng)
    ) {
      const ip = clientIpFromRequest(request);
      const resolved = await resolveLocationFromIp(ip);
      lat = resolved.lat;
      lng = resolved.lng;
      source = resolved.source;
    }

    // Never send null — demo SF fallback
    const locationToSend = {
      lat: lat ?? DEMO_LOCATION.lat,
      lng: lng ?? DEMO_LOCATION.lng,
    };

    console.log("[LOCATION] Sending:", locationToSend, { source, call_id: body.call_id });

    const res = await fetch(`${backend.replace(/\/$/, "")}/vapi/location`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      },
      body: JSON.stringify({
        lat: locationToSend.lat,
        lng: locationToSend.lng,
        call_id: body.call_id,
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: text || `Backend returned ${res.status}` },
        { status: res.status },
      );
    }

    scheduleDemoNearbyFallback();

    const backendPayload = await res.json();
    return NextResponse.json({
      ...backendPayload,
      source,
      lat: locationToSend.lat,
      lng: locationToSend.lng,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
