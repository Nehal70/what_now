"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import CaseStrengthPanel from "@/components/CaseStrengthPanel";
import IncidentProfilePanel from "@/components/IncidentProfilePanel";
import LiveTranscript, {
  type TranscriptMessage,
} from "@/components/LiveTranscript";
import NearbyCardsStrip from "@/components/NearbyCardsStrip";
import ReasoningLog from "@/components/ReasoningLog";
import SponsorPanel from "@/components/SponsorPanel";
import ToolIndicator from "@/components/ToolIndicator";
import {
  buildCaseFactors,
  buildProfileItems,
  computeCaseStrength,
  DISPLAY_PHASES,
  mapDisplayPhase,
  mergeContext,
  type IncidentContext,
  type NearbyPlace,
} from "@/lib/dashboard-context";
import {
  markNearbyShown,
  resetNearbyDemoState,
  scheduleDemoLegalFallback,
  scheduleDemoNearbyFallback,
} from "@/lib/demo-nearby";
import { pushDashboardCallLocation } from "@/lib/push-call-location";
import {
  appendReasoning,
  type ReasoningLogEntry,
} from "@/lib/reasoning-log";
import type { ToolName } from "@/lib/types";

const PHASE_COLORS: Record<(typeof DISPLAY_PHASES)[number], string> = {
  triage: "#ff4a4a",
  gather: "#ff6b4a",
  inform: "#9b6bff",
  summarize: "#5fd4a0",
};

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function DashboardPage() {
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [currentTool, setCurrentTool] = useState<ToolName>(null);
  const [rawPhase, setRawPhase] = useState("");
  const [incidentContext, setIncidentContext] = useState<IncidentContext>({});
  const [reasoningLogs, setReasoningLogs] = useState<ReasoningLogEntry[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [activeModel, setActiveModel] = useState("…");
  const [imagePrompt, setImagePrompt] = useState<string | null>(null);
  const [receivedImages, setReceivedImages] = useState<
    { id: string; preview_url: string }[]
  >([]);
  const [nearbyMedical, setNearbyMedical] = useState<NearbyPlace[]>([]);
  const [nearbyLegal, setNearbyLegal] = useState<NearbyPlace[]>([]);
  const [locationStatus, setLocationStatus] = useState<string | null>(null);
  const [sseStatus, setSseStatus] = useState<"connecting" | "connected" | "reconnecting">(
    "connecting",
  );

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const liveStartedRef = useRef(false);
  const locationSentRef = useRef(false);
  const pendingToolRef = useRef<ToolName>(null);

  const displayPhase = mapDisplayPhase(rawPhase, messages.length);
  const caseFactors = useMemo(
    () => buildCaseFactors(incidentContext),
    [incidentContext],
  );
  const caseStrength = useMemo(
    () => computeCaseStrength(caseFactors, incidentContext),
    [caseFactors, incidentContext],
  );
  const profileItems = useMemo(
    () => buildProfileItems(incidentContext),
    [incidentContext],
  );

  const phaseColor = PHASE_COLORS[displayPhase] ?? "#ff6b4a";
  const currentPhaseIndex = DISPLAY_PHASES.indexOf(displayPhase);

  useEffect(() => {
    fetch("/api/model")
      .then((res) => res.json())
      .then((data: { active_model?: string }) => {
        const name = data.active_model;
        setActiveModel(
          name && name !== "unavailable" && name !== "unknown"
            ? name
            : "qwen3.6-flash",
        );
      })
      .catch(() => setActiveModel("qwen3.6-flash"));
  }, []);

  useEffect(() => {
    void pushDashboardCallLocation().then((result) => {
      if (result.ok) {
        setLocationStatus(
          result.source === "ip"
            ? "Location ready (IP)"
            : "Location ready (demo Austin)",
        );
      }
    });
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
    let source: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const handleEvent = (event: MessageEvent<string>) => {
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
            const toolFromEvent = parsed.data?.tool_called as ToolName;
            if (role && text) {
              setMessages((prev) => [
                ...prev,
                {
                  role,
                  text,
                  toolCalled:
                    role === "assistant"
                      ? toolFromEvent ?? pendingToolRef.current ?? undefined
                      : undefined,
                },
              ]);
              if (role === "assistant") {
                pendingToolRef.current = null;
              }
            }
            break;
          }
          case "tool": {
            const tool = (parsed.data?.tool_called as ToolName) ?? null;
            pendingToolRef.current = tool;
            setCurrentTool(tool);
            if (tool === "legal_tool") {
              scheduleDemoLegalFallback();
            }
            break;
          }
          case "context":
            setIncidentContext((prev) =>
              mergeContext(prev, parsed.data as Record<string, unknown>),
            );
            break;
          case "phase":
            setRawPhase((parsed.data?.phase as string) ?? "");
            break;
          case "reasoning": {
            const reasoning = parsed.data?.reasoning as string;
            if (reasoning) {
              setReasoningLogs((prev) => appendReasoning(prev, reasoning));
            }
            break;
          }
          case "call_state": {
            const state = parsed.data?.state as string | undefined;
            if (state === "live" || state === "thinking") {
              setIsLive(true);
              resetNearbyDemoState();
              scheduleDemoNearbyFallback();
              if (!locationSentRef.current) {
                locationSentRef.current = true;
                void pushDashboardCallLocation(
                  parsed.data?.call_id as string | undefined,
                ).then((result) => {
                  if (!result.ok) {
                    setLocationStatus("Location unavailable");
                    return;
                  }
                  setLocationStatus(
                    result.source === "ip"
                      ? "Location sent (IP) · Apify ready"
                      : "Location sent (demo) · Apify ready",
                  );
                });
              }
            }
            if (state === "idle") {
              setIsLive(false);
              liveStartedRef.current = false;
              locationSentRef.current = false;
              setLocationStatus(null);
              setMessages([]);
              setReasoningLogs([]);
              setCurrentTool(null);
              setRawPhase("");
              setIncidentContext({});
              setNearbyMedical([]);
              setNearbyLegal([]);
              pendingToolRef.current = null;
              if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
              }
              setCallDuration(0);
            }
            break;
          }
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
          case "nearby_medical": {
            markNearbyShown("nearby_medical");
            const places = parsed.data?.places as NearbyPlace[] | undefined;
            if (places?.length) {
              setNearbyMedical(
                places.map((p) => ({
                  name: p.name ?? "Unknown",
                  distance: p.distance ?? "",
                  open_now: p.open_now,
                  phone: p.phone,
                  address: p.address,
                })),
              );
            }
            break;
          }
          case "nearby_legal": {
            markNearbyShown("nearby_legal");
            const places = parsed.data?.places as NearbyPlace[] | undefined;
            if (places?.length) {
              setNearbyLegal(
                places.map((p) => ({
                  name: p.name ?? "Unknown",
                  distance: p.distance ?? "",
                  open_now: p.open_now,
                  phone: p.phone,
                  address: p.address,
                })),
              );
            }
            break;
          }
          default:
            break;
        }
      } catch {
        // ignore malformed events
      }
    };

    const connect = () => {
      if (disposed) return;
      setSseStatus((prev) => (prev === "connected" ? "reconnecting" : "connecting"));
      source = new EventSource("/api/events");
      source.onopen = () => setSseStatus("connected");
      source.onmessage = handleEvent;
      source.onerror = () => {
        source?.close();
        if (disposed) return;
        setSseStatus("reconnecting");
        reconnectTimer = setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      source?.close();
    };
  }, []);

  return (
    <main
      style={{
        height: "100vh",
        maxHeight: "100vh",
        overflow: "hidden",
        backgroundColor: "#000",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        padding: "20px 24px 24px",
        boxSizing: "border-box",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 20px",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 12,
          backgroundColor: "rgba(255,255,255,0.02)",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: 16,
          flexShrink: 0,
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

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {rawPhase || isLive ? (
            <span
              key={displayPhase}
              className="phase-pill"
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
              {displayPhase}
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
          <span
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 10,
              color:
                sseStatus === "connected"
                  ? "rgba(95,212,160,0.7)"
                  : "rgba(255,107,74,0.8)",
            }}
          >
            sse {sseStatus}
          </span>
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
              color: "rgba(255,255,255,0.55)",
              padding: "4px 8px",
              borderRadius: 4,
              border: "1px solid rgba(255,255,255,0.12)",
            }}
          >
            {activeModel}
          </span>
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
          {locationStatus ? (
            <span
              style={{
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                fontSize: 11,
                color: locationStatus.includes("ready")
                  ? "rgba(95,212,160,0.85)"
                  : "rgba(255,255,255,0.35)",
              }}
            >
              {locationStatus}
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
        @keyframes profile-fade-in {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes nearby-slide-up {
          from {
            opacity: 0;
            transform: translateY(16px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .profile-fade-in {
          animation: profile-fade-in 400ms ease forwards;
        }
        .nearby-strip-slide-up {
          animation: nearby-slide-up 500ms ease forwards;
        }
        .phase-pill {
          transition: background-color 400ms ease, transform 300ms ease;
        }
      `}</style>

      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: 12,
          padding: 12,
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 12,
          backgroundColor: "rgba(255,255,255,0.04)",
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        <section
          style={{
            backgroundColor: "rgba(0,0,0,0.6)",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            overflow: "hidden",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
              flexShrink: 0,
            }}
          >
            Transcript
          </p>
          <LiveTranscript messages={messages} />
        </section>

        <section
          style={{
            backgroundColor: "rgba(0,0,0,0.6)",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            overflow: "hidden",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
              flexShrink: 0,
            }}
          >
            Active Tool
          </p>
          <ToolIndicator tool={currentTool} isLive={isLive} />
          <SponsorPanel tool={currentTool} />
        </section>

        <section
          style={{
            backgroundColor: "rgba(0,0,0,0.6)",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            overflow: "hidden",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 12,
              textTransform: "uppercase",
              flexShrink: 0,
            }}
          >
            Agent Reasoning
          </p>
          <ReasoningLog logs={reasoningLogs} />
        </section>

        <section
          style={{
            backgroundColor: "rgba(0,0,0,0.6)",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            gap: 20,
            overflowY: "auto",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <p
            style={{
              fontSize: 10,
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: 0,
              textTransform: "uppercase",
            }}
          >
            Case progress
          </p>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {DISPLAY_PHASES.map((phase, index) => {
              const isCurrent = phase === displayPhase;
              const isCompleted =
                currentPhaseIndex >= 0 && index < currentPhaseIndex;

              return (
                <span
                  key={phase}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-ibm-plex-mono), monospace",
                      fontSize: 12,
                      textTransform: "uppercase",
                      color: isCurrent
                        ? phaseColor
                        : isCompleted
                          ? "#5fd4a0"
                          : "rgba(255,255,255,0.25)",
                      opacity: isCurrent ? 1 : isCompleted ? 0.7 : 0.4,
                      transition: "color 400ms ease, opacity 400ms ease",
                    }}
                  >
                    {phase}
                  </span>
                  {index < DISPLAY_PHASES.length - 1 ? (
                    <span style={{ color: "rgba(255,255,255,0.2)" }}>→</span>
                  ) : null}
                </span>
              );
            })}
          </div>

          <CaseStrengthPanel strength={caseStrength} factors={caseFactors} />
          <IncidentProfilePanel items={profileItems} />
        </section>
      </div>

      {(nearbyMedical.length > 0 ||
        nearbyLegal.length > 0 ||
        imagePrompt ||
        receivedImages.length > 0) && (
        <div
          style={{
            marginTop: 12,
            flexShrink: 0,
            maxHeight: "22vh",
            overflowY: "auto",
          }}
        >
          <NearbyCardsStrip medical={nearbyMedical} legal={nearbyLegal} />

          {imagePrompt || receivedImages.length > 0 ? (
        <section
          style={{
            marginTop: nearbyMedical.length > 0 || nearbyLegal.length > 0 ? 12 : 0,
            padding: "16px 20px",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 12,
            backgroundColor: "rgba(255,255,255,0.02)",
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
        </div>
      )}
    </main>
  );
}
