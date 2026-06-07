"use client";

import type { ToolName } from "@/lib/types";

type Sponsor = "LiveKit" | "TrueFoundry" | "Qwen" | "Moss" | "Unsiloed";

const SPONSOR_COLORS: Record<Sponsor, string> = {
  LiveKit: "#ff4a4a",
  TrueFoundry: "#9b6bff",
  Qwen: "#ff6b4a",
  Moss: "#5fd4a0",
  Unsiloed: "#9ed4f5",
};

const ALL_SPONSORS: Sponsor[] = [
  "LiveKit",
  "TrueFoundry",
  "Qwen",
  "Moss",
  "Unsiloed",
];

const ALWAYS_ACTIVE: Sponsor[] = ["LiveKit", "TrueFoundry"];

const TOOL_SPONSORS: Record<Exclude<ToolName, null>, Sponsor[]> = {
  safety_check: ["Qwen", "LiveKit", "TrueFoundry"],
  scene_guide: ["Qwen", "LiveKit", "TrueFoundry"],
  moss_retrieval: ["Moss", "Unsiloed", "TrueFoundry"],
  insurance_tool: ["Qwen", "Unsiloed", "TrueFoundry"],
  legal_tool: ["Qwen", "Moss", "Unsiloed", "TrueFoundry"],
};

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
        gap: 12,
        marginTop: 20,
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
              border: `1px solid ${isActive ? color : "rgba(255,255,255,0.1)"}`,
              color: isActive ? color : "rgba(255,255,255,0.35)",
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
