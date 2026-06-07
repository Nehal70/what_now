"use client";

import type { ToolName } from "@/lib/types";

type Sponsor = "Livekit" | "TrueFoundry" | "Qwen" | "Moss" | "Unsiloed";

const SPONSOR_COLORS: Record<Sponsor, string> = {
  Livekit: "#22d3ee",
  TrueFoundry: "#9b6bff",
  Qwen: "#ff6b4a",
  Moss: "#5fd4a0",
  Unsiloed: "#9ed4f5",
};

const ALL_SPONSORS: Sponsor[] = [
  "Livekit",
  "TrueFoundry",
  "Qwen",
  "Moss",
  "Unsiloed",
];

const ALWAYS_ACTIVE: Sponsor[] = [
  "Livekit",
  "TrueFoundry",
  "Qwen",
  "Moss",
  "Unsiloed",
];

const TOOL_SPONSORS: Record<Exclude<ToolName, null>, Sponsor[]> = {
  safety_check: ["Qwen", "Livekit", "TrueFoundry"],
  scene_guide: ["Qwen", "Livekit", "TrueFoundry"],
  moss_retrieval: ["Moss", "Unsiloed", "TrueFoundry"],
  insurance_tool: ["Qwen", "Unsiloed", "TrueFoundry"],
  legal_tool: ["Qwen", "Moss", "Unsiloed", "TrueFoundry"],
};

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

type SponsorPanelProps = {
  tool: ToolName;
};

export default function SponsorPanel({ tool }: SponsorPanelProps) {
  const active = new Set<Sponsor>(ALWAYS_ACTIVE);
  if (tool) {
    for (const sponsor of TOOL_SPONSORS[tool]) {
      active.add(sponsor);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 8,
        marginTop: 12,
        width: "100%",
      }}
    >
      {ALL_SPONSORS.map((sponsor) => {
        const isActive = active.has(sponsor);
        const color = SPONSOR_COLORS[sponsor];

        return (
          <span
            key={sponsor}
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 12,
              fontWeight: 500,
              padding: "6px 12px",
              borderRadius: 6,
              flexShrink: 0,
              border: isActive
                ? `1px solid ${color}`
                : "1px solid rgba(255,255,255,0.08)",
              color: isActive ? "#ffffff" : "rgba(255,255,255,0.35)",
              backgroundColor: isActive ? hexToRgba(color, 0.12) : "transparent",
              opacity: isActive ? 1 : 0.25,
              filter: isActive ? "none" : "grayscale(1)",
              boxShadow: isActive ? `0 0 12px ${color}` : "none",
              transition: "all 400ms ease",
            }}
          >
            {sponsor}
          </span>
        );
      })}
    </div>
  );
}
