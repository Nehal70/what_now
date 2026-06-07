"use client";

import { useEffect, useRef, useState } from "react";

import LatencyBadge from "@/components/LatencyBadge";
import LiveTranscript from "@/components/LiveTranscript";
import ReasoningLog from "@/components/ReasoningLog";
import SponsorPanel from "@/components/SponsorPanel";
import ToolIndicator from "@/components/ToolIndicator";
import type { ConversationMessage, ToolName } from "@/lib/types";

const PHASES = ["triage", "gather", "inform", "summarize"] as const;

const TOOL_COLORS: Record<Exclude<ToolName, null>, string> = {
  safety_check: "#ff4a4a",
  scene_guide: "#9ed4f5",
  moss_retrieval: "#ff6b4a",
  insurance_tool: "#9b6bff",
  legal_tool: "#5fd4a0",
};

function latencyColor(ms: number): string {
  if (ms < 500) return "#5fd4a0";
  if (ms < 1000) return "#ff6b4a";
  return "#ff4a4a";
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function formatLogLine(reasoning: string): string {
  const now = new Date();
  const stamp = now.toLocaleTimeString("en-US", { hour12: false });
  return `[${stamp}] ${reasoning}`;
}

export default function DashboardPage() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [currentTool, setCurrentTool] = useState<ToolName>(null);
  const [currentPhase, setCurrentPhase] = useState("");
  const [latency, setLatency] = useState<number | null>(null);
  const [reasoningLogs, setReasoningLogs] = useState<string[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [activeModel, setActiveModel] = useState("…");
  const [imagePrompt, setImagePrompt] = useState<string | null>(null);
  const [receivedImages, setReceivedImages] = useState<
    { id: string; preview_url: string }[]
  >([]);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const liveStartedRef = useRef(false);

  useEffect(() => {
    fetch("/api/model")
      .then((res) => res.json())
      .then((data: { active_model?: string }) => {
        setActiveModel(data.active_model ?? "unknown");
      })
      .catch(() => setActiveModel("unavailable"));
  }, []);

  useEffect(() => {
    if (isLive && !liveStartedRef.current) {
      liveStartedRef.current = true;
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    }
  }, [isLive]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    const source = new EventSource("/api/events");

    source.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as {
          type?: string;
          data?: Record<string, unknown>;
        };

        if (parsed.type === "ping") return;

        switch (parsed.type) {
          case "transcript": {
            const role = parsed.data?.role as "user" | "assistant";
            const text = parsed.data?.text as string;
            if (role && text) {
              setMessages((prev) => [...prev, { role, text }]);
            }
            break;
          }
          case "tool":
            setCurrentTool((parsed.data?.tool_called as ToolName) ?? null);
            break;
          case "phase":
            setCurrentPhase((parsed.data?.phase as string) ?? "");
            break;
          case "reasoning": {
            const reasoning = parsed.data?.reasoning as string;
            if (reasoning) {
              setReasoningLogs((prev) =>
                [...prev, formatLogLine(reasoning)].slice(-20),
              );
            }
            break;
          }
          case "latency":
            setLatency((parsed.data?.latency_ms as number) ?? null);
            break;
          case "call_state":
            if (parsed.data?.state === "thinking") {
              setIsLive(true);
            }
            break;
          case "image_requested":
            setImagePrompt(
              (parsed.data?.prompt as string) ?? "Upload photos in the app",
            );
            break;
          case "image_received": {
            const id = parsed.data?.id as string | undefined;
            const preview_url = parsed.data?.preview_url as string | undefined;
            if (id && preview_url) {
              setReceivedImages((prev) => [...prev, { id, preview_url }]);
            }
            break;
          }
          case "image_processed":
            setImagePrompt(null);
            break;
          default:
            break;
        }
      } catch {
        // ignore malformed events
      }
    };

    return () => {
      source.close();
    };
  }, []);

  const phaseColor =
    currentTool && currentTool in TOOL_COLORS
      ? TOOL_COLORS[currentTool as Exclude<ToolName, null>]
      : "#ff6b4a";

  const currentPhaseIndex = PHASES.indexOf(
    currentPhase as (typeof PHASES)[number],
  );

  return (
    <main
      style={{
        minHeight: "100vh",
        backgroundColor: "#000",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <h1
          style={{
            fontFamily: "var(--font-baskerville), serif",
            fontSize: 28,
            color: "#ff6b4a",
            margin: 0,
          }}
        >
          What Now?
        </h1>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          {currentPhase ? (
            <span
              style={{
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                fontSize: 12,
                padding: "6px 14px",
                borderRadius: 999,
                backgroundColor: phaseColor,
                color: "#000",
                textTransform: "uppercase",
              }}
            >
              {currentPhase}
            </span>
          ) : (
            <span
              style={{
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                fontSize: 12,
                color: "rgba(255,255,255,0.3)",
              }}
            >
              awaiting call
            </span>
          )}
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 11,
              color: "rgba(255,255,255,0.35)",
            }}
          >
            {activeModel}
          </span>
          <LatencyBadge latency={latency} />
          {isLive ? (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                fontSize: 12,
                color: "#5fd4a0",
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: "#5fd4a0",
                  animation: "pulse 1.5s infinite",
                }}
              />
              LIVE
            </span>
          ) : null}
          <span
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 12,
              color: "rgba(255,255,255,0.5)",
            }}
          >
            {formatDuration(callDuration)}
          </span>
        </div>
      </header>

      <style jsx global>{`
        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0.35;
          }
        }
      `}</style>

      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: 1,
          backgroundColor: "rgba(255,255,255,0.06)",
          minHeight: 0,
        }}
      >
        <section
          style={{
            backgroundColor: "#000",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
            }}
          >
            Transcript
          </p>
          <LiveTranscript messages={messages} />
        </section>

        <section
          style={{
            backgroundColor: "#000",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
            }}
          >
            Active Tool
          </p>
          <ToolIndicator tool={currentTool} phase={currentPhase || null} />
          <SponsorPanel tool={currentTool} />
        </section>

        <section
          style={{
            backgroundColor: "#000",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
            }}
          >
            Agent Reasoning
          </p>
          <ReasoningLog logs={reasoningLogs} />
        </section>

        <section
          style={{
            backgroundColor: "#000",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
            }}
          >
            Performance
          </p>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24 }}>
            <div>
              <p
                style={{
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  fontSize: 48,
                  fontWeight: 500,
                  margin: 0,
                  color:
                    latency === null
                      ? "rgba(255,255,255,0.35)"
                      : latencyColor(latency),
                }}
              >
                {latency === null ? "—" : `${latency}ms`}
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                flexWrap: "wrap",
              }}
            >
              {PHASES.map((phase, index) => {
                const isCurrent = phase === currentPhase;
                const isCompleted =
                  currentPhaseIndex >= 0 && index < currentPhaseIndex;

                return (
                  <span key={phase} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        fontFamily: "var(--font-ibm-plex-mono), monospace",
                        fontSize: 12,
                        textTransform: "uppercase",
                        color: isCurrent
                          ? "#ff6b4a"
                          : isCompleted
                            ? "#5fd4a0"
                            : "rgba(255,255,255,0.25)",
                        opacity: isCurrent ? 1 : isCompleted ? 0.7 : 0.4,
                      }}
                    >
                      {phase}
                    </span>
                    {index < PHASES.length - 1 ? (
                      <span style={{ color: "rgba(255,255,255,0.2)" }}>→</span>
                    ) : null}
                  </span>
                );
              })}
            </div>
          </div>
        </section>
      </div>

      {imagePrompt || receivedImages.length > 0 ? (
        <section
          style={{
            padding: "16px 24px 24px",
            borderTop: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <span
            style={{
              fontSize: 10,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "rgba(158,212,245,0.7)",
              fontFamily: "var(--font-ibm-plex-mono), monospace",
            }}
          >
            Scene photos
          </span>
          {imagePrompt ? (
            <p
              style={{
                margin: 0,
                fontSize: 13,
                color: "rgba(255,255,255,0.65)",
              }}
            >
              {imagePrompt}
            </p>
          ) : null}
          {receivedImages.length > 0 ? (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {receivedImages.map((image) => (
                <img
                  key={image.id}
                  src={image.preview_url}
                  alt="Uploaded scene"
                  style={{
                    width: 72,
                    height: 72,
                    objectFit: "cover",
                    borderRadius: 8,
                    border: "1px solid rgba(255,255,255,0.12)",
                  }}
                />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
