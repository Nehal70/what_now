"use client";

import type { OrbState } from "@/lib/types";

const STATE_COLORS: Record<OrbState, string> = {
  idle: "rgba(255,255,255,0.15)",
  listening: "#9ed4f5",
  thinking: "#ff6b4a",
  speaking: "#5fd4a0",
};

type VoiceOrbProps = {
  state: OrbState;
};

export default function VoiceOrb({ state }: VoiceOrbProps) {
  const color = STATE_COLORS[state];
  const pulsing = state !== "idle";

  return (
    <>
      <style jsx>{`
        @keyframes orb-pulse {
          0%,
          100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.15);
            opacity: 0.4;
          }
        }
      `}</style>
      <div
        style={{
          position: "relative",
          width: 200,
          height: 200,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: `2px solid ${color}`,
            animation: pulsing ? "orb-pulse 1.5s infinite" : "none",
            transition: "border-color 300ms ease, opacity 300ms ease",
          }}
        />
        <div
          style={{
            width: 140,
            height: 140,
            borderRadius: "50%",
            backgroundColor: color,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background-color 300ms ease",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: state === "idle" ? "rgba(255,255,255,0.6)" : "#000",
            }}
          >
            {state}
          </span>
        </div>
      </div>
    </>
  );
}
