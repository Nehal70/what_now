"use client";

import type { NearbyPlace } from "@/lib/dashboard-context";

type NearbyCardsStripProps = {
  medical: NearbyPlace[];
  legal: NearbyPlace[];
};

function PlaceCard({
  place,
  tint,
}: {
  place: NearbyPlace;
  tint: "ember" | "ice";
}) {
  const border =
    tint === "ember"
      ? "rgba(255,107,74,0.35)"
      : "rgba(158,212,245,0.35)";
  const bg =
    tint === "ember"
      ? "rgba(255,107,74,0.08)"
      : "rgba(158,212,245,0.08)";

  return (
    <div
      style={{
        flex: "0 0 auto",
        minWidth: 200,
        padding: "12px 14px",
        borderRadius: 10,
        border: `1px solid ${border}`,
        backgroundColor: bg,
        fontFamily: "var(--font-ibm-plex-mono), monospace",
        fontSize: 12,
        color: "rgba(255,255,255,0.85)",
      }}
    >
      <div style={{ fontWeight: 500, marginBottom: 4 }}>{place.name}</div>
      <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 11 }}>
        {place.distance}
        {place.open_now === true ? " · OPEN" : ""}
        {place.phone ? ` · ☎ ${place.phone}` : " · ☎"}
      </div>
    </div>
  );
}

export default function NearbyCardsStrip({
  medical,
  legal,
}: NearbyCardsStripProps) {
  if (medical.length === 0 && legal.length === 0) return null;

  return (
    <section
      className="nearby-strip-slide-up"
      style={{
        overflow: "hidden",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 12,
        backgroundColor: "rgba(255,255,255,0.02)",
      }}
    >
      {medical.length > 0 ? (
        <div style={{ padding: "16px 20px 12px" }}>
          <span
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "#ff6b4a",
              fontFamily: "var(--font-ibm-plex-mono), monospace",
            }}
          >
            Urgent care near you
          </span>
          <div
            style={{
              display: "flex",
              gap: 10,
              marginTop: 10,
              overflowX: "auto",
              paddingBottom: 4,
            }}
          >
            {medical.slice(0, 5).map((place) => (
              <PlaceCard
                key={`${place.name}-${place.distance}`}
                place={place}
                tint="ember"
              />
            ))}
          </div>
        </div>
      ) : null}

      {legal.length > 0 ? (
        <div
          style={{
            padding: medical.length > 0 ? "0 20px 20px" : "16px 20px 20px",
          }}
        >
          <span
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "#9ed4f5",
              fontFamily: "var(--font-ibm-plex-mono), monospace",
            }}
          >
            Attorneys near you
          </span>
          <div
            style={{
              display: "flex",
              gap: 10,
              marginTop: 10,
              overflowX: "auto",
              paddingBottom: 4,
            }}
          >
            {legal.slice(0, 5).map((place) => (
              <PlaceCard
                key={`${place.name}-${place.distance}`}
                place={place}
                tint="ice"
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
