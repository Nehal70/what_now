/** Register call location via server IP lookup — no browser permission prompt. */

export type LocationPushResult = {
  ok: boolean;
  source?: "ip" | "demo_default";
};

export async function pushDashboardCallLocation(
  callId?: string | null,
): Promise<LocationPushResult> {
  try {
    const res = await fetch("/api/vapi/location", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(callId ? { call_id: callId } : {}),
    });
    if (!res.ok) {
      return { ok: false };
    }
    const data = (await res.json()) as { source?: "ip" | "demo_default" };
    return { ok: true, source: data.source };
  } catch {
    return { ok: false };
  }
}
