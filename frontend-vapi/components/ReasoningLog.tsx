"use client";

import { useEffect, useRef } from "react";

import {
  levelColor,
  type ReasoningLogEntry,
} from "@/lib/reasoning-log";

type ReasoningLogProps = {
  logs: ReasoningLogEntry[];
};

function formatTool(name: string): string {
  return name.replace(/_/g, " ");
}

export default function ReasoningLog({ logs }: ReasoningLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <>
      <style jsx global>{`
        .reasoning-log-scroll::-webkit-scrollbar {
          width: 4px;
        }
        .reasoning-log-scroll::-webkit-scrollbar-thumb {
          background: rgba(95, 212, 160, 0.25);
          border-radius: 4px;
        }
        .reasoning-log-scroll {
          scrollbar-width: thin;
          scrollbar-color: rgba(95, 212, 160, 0.25) transparent;
        }
      `}</style>
      <div
        className="reasoning-log-scroll"
        style={{
          flex: 1,
          overflowY: "auto",
          backgroundColor: "#050505",
          border: "1px solid rgba(95,212,160,0.18)",
          borderRadius: 8,
          padding: "10px 12px",
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 11,
          lineHeight: 1.55,
        }}
      >
        <div
          style={{
            color: "rgba(255,255,255,0.28)",
            marginBottom: 10,
            paddingBottom: 8,
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <div style={{ color: "#5fd4a0" }}>what-now@agent</div>
          <div>reasoning trace — live</div>
        </div>

        {logs.length === 0 ? (
          <span style={{ color: "rgba(95,212,160,0.35)" }}>
            $ awaiting first agent decision…
          </span>
        ) : (
          logs.map((entry) => (
            <div key={entry.id} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                <span style={{ color: "rgba(255,255,255,0.28)", flexShrink: 0 }}>
                  {entry.time}
                </span>
                <span
                  style={{
                    color: levelColor(entry.level),
                    flexShrink: 0,
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    fontSize: 10,
                  }}
                >
                  {entry.level.padEnd(5, " ")}
                </span>
                <span style={{ color: "rgba(255,255,255,0.88)" }}>
                  {entry.message}
                </span>
              </div>
              {entry.detail ? (
                <div
                  style={{
                    marginTop: 2,
                    paddingLeft: 62,
                    color: "rgba(255,255,255,0.42)",
                    fontSize: 10,
                  }}
                >
                  └ {entry.detail}
                </div>
              ) : null}
              {entry.tools && entry.tools.length > 0 ? (
                <div
                  style={{
                    marginTop: 2,
                    paddingLeft: 62,
                    color: "#5fd4a0",
                    fontSize: 10,
                    opacity: 0.75,
                  }}
                >
                  └ {entry.tools.map(formatTool).join(" · ")}
                </div>
              ) : null}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </>
  );
}
