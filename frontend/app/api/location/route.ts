import { NextResponse } from "next/server";

import {
  clearUserLocation,
  setUserLocation,
} from "@/lib/location-store";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json()) as {
    lat?: number;
    lng?: number;
  };

  const { lat, lng } = body;

  if (lat == null || lng == null) {
    clearUserLocation(user.id);
    return NextResponse.json({ ok: true });
  }

  if (
    typeof lat !== "number" ||
    typeof lng !== "number" ||
    !Number.isFinite(lat) ||
    !Number.isFinite(lng)
  ) {
    return NextResponse.json({ error: "Invalid coordinates" }, { status: 400 });
  }

  setUserLocation(user.id, { lat, lng });
  return NextResponse.json({ ok: true });
}
