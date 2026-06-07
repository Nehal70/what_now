"use client";

import { TOOL_LABELS } from "@/lib/dashboard-context";
import type { ToolName } from "@/lib/types";

const TOOL_COLORS: Record<Exclude<ToolName, null>, string> = {
  safety_check: "#ff4a4a",
  scene_guide: "#9ed4f5",
  moss_retrieval: "#ff6b4a",
  insurance_tool: "#9b6bff",
  legal_tool: "#5fd4a0",
};

type ToolIndicatorProps = {
  tool: ToolName;
  isLive: boolean;
};

export default function ToolIndicator({ tool, isLive }: ToolIndicatorProps) {
  if (!tool) {
    if (!isLive) return null;
    return (
      <p
        style={{
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 13,
          color: "rgba(255,255,255,0.25)",
          margin: 0,
          height: 56,
          display: "flex",
          alignItems: "center",
        }}
      >
        Listening...
      </p>
    );
  }

  const color = TOOL_COLORS[tool];
  const meta = TOOL_LABELS[tool];

  return (
    <>
      <style jsx>{`
        @keyframes tool-scale-in {
          from {
            transform: scale(0.92);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
      <div
        key={tool}
        style={{
          width: "100%",
          height: 56,
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "0 18px",
          borderRadius: 12,
          backgroundColor: color,
          color: "#000",
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 15,
          fontWeight: 600,
          animation: "tool-scale-in 300ms ease forwards",
          boxShadow: `0 0 20px ${color}55`,
        }}
      >
        <span style={{ fontSize: 20 }}>{meta.icon}</span>
        <span>{meta.label}</span>
      </div>
    </>
  );
}
