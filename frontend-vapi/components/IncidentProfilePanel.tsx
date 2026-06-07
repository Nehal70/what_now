"use client";

import type { ProfileItem } from "@/lib/dashboard-context";

type IncidentProfilePanelProps = {
  items: ProfileItem[];
};

export default function IncidentProfilePanel({
  items,
}: IncidentProfilePanelProps) {
  if (items.length === 0) return null;

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
        Incident profile
      </span>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((item) => (
          <span
            key={item.id}
            className="profile-fade-in"
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 12,
              color: "rgba(255,255,255,0.75)",
            }}
          >
            {item.icon} {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}
