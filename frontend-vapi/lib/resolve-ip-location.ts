/** Resolve approximate lat/lng from IP — no browser geolocation permission. */

const DEFAULT_DEMO_LAT = Number(process.env.DEMO_DEFAULT_LAT ?? "30.2672");
const DEFAULT_DEMO_LNG = Number(process.env.DEMO_DEFAULT_LNG ?? "-97.7431");

function isPrivateIp(ip: string): boolean {
  const normalized = ip.trim().toLowerCase();
  if (!normalized || normalized === "::1" || normalized === "127.0.0.1") {
    return true;
  }
  if (normalized.startsWith("192.168.") || normalized.startsWith("10.")) {
    return true;
  }
  if (normalized.startsWith("172.")) {
    const second = Number(normalized.split(".")[1]);
    if (second >= 16 && second <= 31) {
      return true;
    }
  }
  return false;
}

export function clientIpFromRequest(request: Request): string | null {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first) {
      return first;
    }
  }
  const realIp = request.headers.get("x-real-ip");
  return realIp?.trim() || null;
}

export type ResolvedLocation = {
  lat: number;
  lng: number;
  source: "ip" | "demo_default";
  ip?: string;
};

export async function resolveLocationFromIp(
  ip: string | null,
): Promise<ResolvedLocation> {
  if (!ip || isPrivateIp(ip)) {
    return {
      lat: DEFAULT_DEMO_LAT,
      lng: DEFAULT_DEMO_LNG,
      source: "demo_default",
    };
  }

  try {
    const res = await fetch(`https://ipwho.is/${encodeURIComponent(ip)}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) {
      throw new Error(`ipwho.is ${res.status}`);
    }
    const data = (await res.json()) as {
      success?: boolean;
      latitude?: number;
      longitude?: number;
    };
    if (
      data.success &&
      typeof data.latitude === "number" &&
      typeof data.longitude === "number"
    ) {
      return {
        lat: data.latitude,
        lng: data.longitude,
        source: "ip",
        ip,
      };
    }
  } catch {
    // fall through to demo default
  }

  return {
    lat: DEFAULT_DEMO_LAT,
    lng: DEFAULT_DEMO_LNG,
    source: "demo_default",
    ip,
  };
}
