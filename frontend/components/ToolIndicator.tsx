"use client";

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
  phase: string | null;
};

export default function ToolIndicator({ tool, phase }: ToolIndicatorProps) {
  if (!tool) return null;

  const color = TOOL_COLORS[tool];

  return (
    <>
      <style jsx>{`
        @keyframes tool-scale-in {
          from {
            transform: scale(0);
          }
          to {
            transform: scale(1);
          }
        }
      `}</style>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          animation: "tool-scale-in 300ms ease forwards",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-ibm-plex-mono), monospace",
            fontSize: 13,
            fontWeight: 500,
            color: "#000",
            backgroundColor: color,
            padding: "8px 16px",
            borderRadius: 999,
            textTransform: "lowercase",
          }}
        >
          {tool}
        </span>
        {phase ? (
          <span
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 11,
              color: "rgba(255,255,255,0.45)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            {phase}
          </span>
        ) : null}
      </div>
    </>
  );
}
