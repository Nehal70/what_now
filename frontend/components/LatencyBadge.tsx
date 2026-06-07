"use client";

type LatencyBadgeProps = {
  latency: number | null;
};

function latencyColor(ms: number): string {
  if (ms < 500) return "#5fd4a0";
  if (ms < 1000) return "#ff6b4a";
  return "#ff4a4a";
}

export default function LatencyBadge({ latency }: LatencyBadgeProps) {
  const label = latency === null ? "—" : `${latency}ms`;
  const color =
    latency === null ? "rgba(255,255,255,0.35)" : latencyColor(latency);

  return (
    <span
      style={{
        fontFamily: "var(--font-ibm-plex-mono), monospace",
        fontSize: 12,
        fontWeight: 500,
        padding: "4px 10px",
        borderRadius: 6,
        border: `1px solid ${color}`,
        color,
      }}
    >
      {label}
    </span>
  );
}
