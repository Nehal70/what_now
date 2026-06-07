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
  if (latency === null || latency === 0) {
    return null;
  }

  const color = latencyColor(latency);

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
      {latency}ms
    </span>
  );
}
