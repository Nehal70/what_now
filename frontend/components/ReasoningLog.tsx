"use client";

import { useEffect, useRef } from "react";

type ReasoningLogProps = {
  logs: string[];
};

export default function ReasoningLog({ logs }: ReasoningLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <>
      <style jsx global>{`
        .reasoning-log-scroll::-webkit-scrollbar {
          display: none;
        }
        .reasoning-log-scroll {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
      <div
        className="reasoning-log-scroll"
        style={{
          flex: 1,
          overflowY: "auto",
          backgroundColor: "#0a0a0a",
          border: "1px solid rgba(95,212,160,0.2)",
          borderRadius: 8,
          padding: 12,
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 12,
          color: "#5fd4a0",
          lineHeight: 1.6,
        }}
      >
        {logs.length === 0 ? (
          <span style={{ color: "rgba(95,212,160,0.4)" }}>
            Waiting for agent reasoning…
          </span>
        ) : (
          logs.map((line, index) => (
            <div key={`${index}-${line.slice(0, 20)}`}>{line}</div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </>
  );
}
