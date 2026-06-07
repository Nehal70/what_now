"use client";

import { useEffect, useState } from "react";

import type { CaseFactor } from "@/lib/dashboard-context";

type CaseStrengthPanelProps = {
  strength: number;
  factors: CaseFactor[];
};

export default function CaseStrengthPanel({
  strength,
  factors,
}: CaseStrengthPanelProps) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const start = display;
    const end = strength;
    if (start === end) return;

    const duration = 600;
    const t0 = performance.now();

    let frame: number;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      setDisplay(Math.round(start + (end - start) * p));
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strength]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <span
        style={{
          fontSize: 10,
          letterSpacing: "0.12em",
          color: "rgba(255,255,255,0.35)",
          textTransform: "uppercase",
        }}
      >
        Case strength
      </span>
      <p
        style={{
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 36,
          fontWeight: 500,
          margin: 0,
          color: strength >= 50 ? "#5fd4a0" : "#ff6b4a",
        }}
      >
        {display}%
      </p>
      <div
        style={{
          height: 4,
          borderRadius: 2,
          backgroundColor: "rgba(255,255,255,0.08)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${display}%`,
            backgroundColor: strength >= 50 ? "#5fd4a0" : "#ff6b4a",
            transition: "width 600ms ease",
          }}
        />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {factors.map((factor) => (
          <span
            key={factor.id}
            className="profile-fade-in"
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 11,
              color:
                factor.status === "done"
                  ? "rgba(95,212,160,0.85)"
                  : factor.status === "warn"
                    ? "rgba(255,107,74,0.9)"
                    : "rgba(255,255,255,0.3)",
            }}
          >
            {factor.status === "done"
              ? "✅"
              : factor.status === "warn"
                ? "⚠️"
                : "○"}{" "}
            {factor.label}
          </span>
        ))}
      </div>
    </div>
  );
}
