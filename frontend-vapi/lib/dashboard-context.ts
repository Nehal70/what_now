import type { ToolName } from "@/lib/types";

export type IncidentContext = {
  state?: string | null;
  incident_type?: string | null;
  injuries?: string | null;
  injury_severity?: string | null;
  witnesses?: boolean | null;
  signed_anything?: boolean | null;
  police_report?: boolean | null;
  other_carrier?: string | null;
  still_at_scene?: boolean | null;
  location?: string | null;
  incident_stack?: Record<string, unknown>;
};

export type NearbyPlace = {
  name: string;
  address?: string;
  phone?: string;
  distance: string;
  open_now?: boolean | null;
};

export type CaseFactor = {
  id: string;
  label: string;
  status: "done" | "warn" | "pending";
};

export function mergeContext(
  prev: IncidentContext,
  next: Record<string, unknown> | undefined,
): IncidentContext {
  if (!next) return prev;
  const stack = (next.incident_stack as Record<string, unknown>) ?? {};
  return {
    state: (next.state as string) ?? (stack.state as string) ?? prev.state,
    incident_type:
      (next.incident_type as string) ??
      (stack.incident_type as string) ??
      prev.incident_type,
    injuries:
      (next.injuries as string) ??
      (stack.injuries as string) ??
      prev.injuries,
    injury_severity:
      (next.injury_severity as string) ?? prev.injury_severity,
    witnesses:
      next.witnesses !== undefined
        ? Boolean(next.witnesses)
        : stack.witnesses !== undefined
          ? Boolean(stack.witnesses)
          : prev.witnesses,
    signed_anything:
      next.signed_anything !== undefined
        ? Boolean(next.signed_anything)
        : stack.signed_anything !== undefined
          ? Boolean(stack.signed_anything)
          : prev.signed_anything,
    police_report:
      next.police_report !== undefined
        ? Boolean(next.police_report)
        : stack.police_report !== undefined
          ? Boolean(stack.police_report)
          : prev.police_report,
    other_carrier:
      (next.other_carrier as string) ??
      (stack.other_carrier as string) ??
      prev.other_carrier,
    still_at_scene:
      stack.still_at_scene !== undefined
        ? Boolean(stack.still_at_scene)
        : prev.still_at_scene,
    location: (next.location as string) ?? prev.location,
    incident_stack: { ...prev.incident_stack, ...stack },
  };
}

export function buildCaseFactors(ctx: IncidentContext): CaseFactor[] {
  const factors: CaseFactor[] = [];

  if (ctx.police_report === true) {
    factors.push({ id: "police", label: "Police report", status: "done" });
  } else if (ctx.police_report === false) {
    factors.push({ id: "police", label: "Police report", status: "pending" });
  }

  if (ctx.witnesses === true) {
    factors.push({ id: "witness", label: "Witness present", status: "done" });
  } else if (ctx.witnesses === false) {
    factors.push({ id: "witness", label: "Witness present", status: "pending" });
  }

  if (ctx.signed_anything === false) {
    factors.push({ id: "signed", label: "No forms signed", status: "done" });
  } else if (ctx.signed_anything === true) {
    factors.push({ id: "signed", label: "No forms signed", status: "warn" });
  }

  const injury = ctx.injuries ?? ctx.injury_severity;
  if (injury && injury !== "none") {
    factors.push({
      id: "medical",
      label: "Medical attention needed",
      status: "warn",
    });
  }

  return factors;
}

export function computeCaseStrength(
  factors: CaseFactor[],
  ctx?: IncidentContext,
): number {
  const override = ctx?.incident_stack?.demo_case_strength;
  if (typeof override === "number") {
    return Math.min(100, Math.max(0, override));
  }
  if (factors.length === 0) return 0;
  let score = 0;
  for (const f of factors) {
    if (f.status === "done") score += 25;
    else if (f.status === "warn") score += 10;
  }
  return Math.min(100, score);
}

export type ProfileItem = { id: string; icon: string; label: string };

export function buildProfileItems(ctx: IncidentContext): ProfileItem[] {
  const items: ProfileItem[] = [];

  if (ctx.state) {
    items.push({
      id: "state",
      icon: "📍",
      label: ctx.state.includes(",") ? ctx.state : `${ctx.state}`,
    });
  }

  const incident = formatIncidentType(ctx.incident_type);
  if (incident) {
    items.push({ id: "incident", icon: "🚗", label: incident });
  }

  const injury = formatInjury(ctx.injuries ?? ctx.injury_severity);
  if (injury) {
    items.push({ id: "injury", icon: "🤕", label: injury });
  }

  if (ctx.witnesses === true) {
    items.push({ id: "witness", icon: "👁️", label: "Witness present" });
  }

  if (ctx.other_carrier) {
    items.push({
      id: "carrier",
      icon: "🏢",
      label: ctx.other_carrier,
    });
  }

  return items;
}

function formatIncidentType(raw?: string | null): string | null {
  if (!raw) return null;
  const map: Record<string, string> = {
    car_accident: "Car accident",
    slip_fall: "Slip and fall",
    hit_run: "Hit and run",
    dog_bite: "Dog bite",
    workplace: "Workplace injury",
    "car accident": "Car accident",
    "slip and fall": "Slip and fall",
  };
  return map[raw] ?? raw.replace(/_/g, " ");
}

function formatInjury(raw?: string | null): string | null {
  if (!raw || raw === "none") return null;
  const map: Record<string, string> = {
    moderate: "Neck injury",
    serious: "Serious injury",
    minor: "Minor injury",
    mild: "Minor injury",
  };
  return map[raw] ?? `${raw} injury`;
}

export const TOOL_LABELS: Record<
  Exclude<ToolName, null>,
  { icon: string; label: string }
> = {
  safety_check: { icon: "🛡️", label: "Safety Triage" },
  scene_guide: { icon: "📸", label: "Scene Guidance" },
  moss_retrieval: { icon: "🔍", label: "Retrieving Law..." },
  insurance_tool: { icon: "📋", label: "Insurance Lookup" },
  legal_tool: { icon: "⚖️", label: "Legal Research" },
};

export const DISPLAY_PHASES = [
  "triage",
  "gather",
  "inform",
  "summarize",
] as const;

export function mapDisplayPhase(
  phase: string,
  messageCount: number,
): (typeof DISPLAY_PHASES)[number] {
  if (phase === "guiding") {
    return messageCount > 8 ? "summarize" : "inform";
  }
  if (phase === "questioning") {
    return messageCount <= 2 ? "triage" : "gather";
  }
  if (
    phase === "triage" ||
    phase === "gather" ||
    phase === "inform" ||
    phase === "summarize"
  ) {
    return phase;
  }
  return "triage";
}
