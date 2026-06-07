"use client";

import Vapi from "@vapi-ai/web";
import { useCallback, useEffect, useRef, useState } from "react";

import DemoImageUploadBar from "@/components/DemoImageUploadBar";
import VoiceOrb from "@/components/VoiceOrb";
import type { CallContext, ConversationMessage, OrbState } from "@/lib/types";

const PHOTO_REQUEST_RE =
  /photo of the damage|send me a photo|send.*photo|upload.*photo/i;

type VapiConfig = {
  apiKey: string;
  assistantId: string;
  useInlineAssistant: boolean;
  customLlmUrl: string;
  debug?: boolean;
};

function formatVapiError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "object" && error !== null) {
    const record = error as Record<string, unknown>;
    const nested = record.error as Record<string, unknown> | undefined;
    const message =
      (typeof nested?.message === "string" && nested.message) ||
      (typeof record.message === "string" && record.message) ||
      (typeof record.type === "string" && record.type);
    if (message) {
      return String(message);
    }
    try {
      return JSON.stringify(error);
    } catch {
      return "Unknown Vapi error";
    }
  }
  return String(error);
}

function pushDashboardEvents(
  events: Array<{
    type: string;
    data: Record<string, unknown>;
    timestamp?: number;
  }>,
) {
  void fetch("/api/vapi/dashboard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      events: events.map((event) => ({
        ...event,
        timestamp: event.timestamp ?? Date.now(),
      })),
    }),
  });
}

function isPhotoRequest(text: string): boolean {
  return PHOTO_REQUEST_RE.test(text);
}

function buildInlineAssistant(customLlmUrl: string) {
  return {
    name: "What Now",
    firstMessage: "I'm here. Are you hurt?",
    transcriber: {
      provider: "deepgram",
      model: "nova-2",
    },
    voice: {
      provider: "openai",
      voiceId: "shimmer",
    },
    model: {
      provider: "custom-llm",
      url: customLlmUrl,
      model: "what-now",
    },
  } as Parameters<Vapi["start"]>[0];
}

export default function CallPage() {
  const vapiRef = useRef<Vapi | null>(null);
  const configRef = useRef<VapiConfig | null>(null);
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState<ConversationMessage[]>([]);
  const [callContext, setCallContext] = useState<CallContext>({});
  const [configError, setConfigError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [debugInfo, setDebugInfo] = useState<string | null>(null);
  const [llmUrl, setLlmUrl] = useState("");
  const [awaitingImage, setAwaitingImage] = useState(false);

  const markAwaitingImage = useCallback(() => {
    setAwaitingImage(true);
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

        if (parsed.type === "image_requested") {
          markAwaitingImage();
        }

        if (parsed.type === "image_processed") {
          setAwaitingImage(false);
        }

        if (parsed.type === "transcript") {
          const role = parsed.data?.role as string | undefined;
          const text = parsed.data?.text as string | undefined;
          if (role === "assistant" && text && isPhotoRequest(text)) {
            markAwaitingImage();
          }
        }

        if (parsed.type === "context") {
          const ctx = parsed.data as CallContext;
          if (ctx?.awaiting_image) {
            markAwaitingImage();
          } else if (ctx && "awaiting_image" in ctx && ctx.awaiting_image === false) {
            setAwaitingImage(false);
          }
          setCallContext((prev) => ({ ...prev, ...ctx }));
        }
      } catch {
        // ignore malformed SSE
      }
    };

    return () => {
      source.close();
    };
  }, [markAwaitingImage]);

  useEffect(() => {
    let cancelled = false;

    async function initVapi() {
      try {
        const res = await fetch("/api/vapi/config");
        if (!res.ok) {
          throw new Error(`Config request failed (${res.status})`);
        }

        const config = (await res.json()) as VapiConfig;
        if (cancelled) return;

        if (!config.apiKey) {
          setConfigError(
            "Vapi key missing. Add NEXT_PUBLIC_VAPI_API_KEY (public key) to .env.local, save, and restart npm run dev.",
          );
          setLoading(false);
          return;
        }

        if (!config.customLlmUrl) {
          setConfigError(
            "Backend URL missing. Set NEXT_PUBLIC_BACKEND_ENDPOINT in .env.local to your ngrok URL.",
          );
          setLoading(false);
          return;
        }

        configRef.current = config;
        setLlmUrl(config.customLlmUrl);
        if (config.debug) {
          setDebugInfo(`LLM: ${config.customLlmUrl}`);
        }
        const vapi = new Vapi(config.apiKey);
        vapiRef.current = vapi;

        vapi.on("call-start", () => {
          setConfigError(null);
          setIsConnected(true);
          setOrbState("listening");
          setStarting(false);
          pushDashboardEvents([
            { type: "call_state", data: { state: "live" } },
          ]);
        });

        vapi.on("call-end", () => {
          setIsConnected(false);
          setOrbState("idle");
          setStarting(false);
          pushDashboardEvents([
            { type: "call_state", data: { state: "idle" } },
          ]);
        });

        vapi.on("call-start-failed", (payload: unknown) => {
          setStarting(false);
          setIsConnected(false);
          setOrbState("idle");
          setConfigError(formatVapiError(payload));
        });

        vapi.on("call-start-progress", (progress: Record<string, unknown>) => {
          if (config.debug) {
            const stage = progress.stage as string | undefined;
            const status = progress.status as string | undefined;
            if (stage && status) {
              setDebugInfo(`${stage}: ${status}`);
            }
          }
          if (progress.status === "failed") {
            setConfigError(formatVapiError(progress));
          }
        });

        vapi.on("speech-start", () => {
          setOrbState("speaking");
        });

        vapi.on("speech-end", () => {
          setOrbState("listening");
        });

        vapi.on("message", (message: Record<string, unknown>) => {
          if (message.type !== "transcript") {
            return;
          }

          const role = message.role as "user" | "assistant" | undefined;
          const text = (message.transcript as string) ?? "";
          if (!role || !text) {
            return;
          }

          setTranscript((prev) => [...prev, { role, text }]);

          if (role === "assistant" && isPhotoRequest(text)) {
            markAwaitingImage();
          }
        });

        vapi.on("error", (error: unknown) => {
          console.error("Vapi error:", error);
          setStarting(false);
          setOrbState("idle");
          setIsConnected(false);
          const msg = formatVapiError(error);
          setConfigError(
            msg.includes("network")
              ? `${msg} — use your Vapi PUBLIC key (not private), allow mic access, and check Vapi credits.`
              : msg,
          );
        });

        setLoading(false);
      } catch (error) {
        if (!cancelled) {
          setConfigError(
            error instanceof Error ? error.message : "Failed to load Vapi config",
          );
          setLoading(false);
        }
      }
    }

    void initVapi();

    return () => {
      cancelled = true;
      vapiRef.current?.stop();
      vapiRef.current?.removeAllListeners();
      vapiRef.current = null;
    };
  }, [markAwaitingImage]);

  const startCall = async () => {
    const vapi = vapiRef.current;
    const config = configRef.current;
    if (!vapi || !config) {
      return;
    }

    setConfigError(null);
    setStarting(true);

    const customLlmUrl = config.customLlmUrl.replace(/\/$/, "");
    const assistant = buildInlineAssistant(customLlmUrl);

    const coords = await new Promise<{ lat: number; lng: number } | null>((resolve) => {
      if (typeof navigator === "undefined" || !navigator.geolocation) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          resolve({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 },
      );
    });

    const assistantOverrides = coords
      ? { metadata: { lat: coords.lat, lng: coords.lng } }
      : undefined;

    try {
      if (config.assistantId && !config.useInlineAssistant) {
        await vapi.start(config.assistantId, {
          model: assistant.model,
          ...assistantOverrides,
        });
        return;
      }

      await vapi.start(assistant, assistantOverrides);
    } catch (error) {
      setStarting(false);
      setConfigError(formatVapiError(error));
    }
  };

  const endCall = () => {
    vapiRef.current?.stop();
    setIsConnected(false);
    setOrbState("idle");
    setStarting(false);
  };

  return (
    <>
      <DemoImageUploadBar
        visible={awaitingImage}
        onSent={() => setAwaitingImage(false)}
      />

      <div
        className="flex min-h-screen flex-col items-center justify-center gap-8 bg-black p-6 text-white"
        style={{ paddingTop: awaitingImage ? 140 : 24 }}
      >
        <h1
          className="text-4xl font-bold text-[#ff6b4a]"
          style={{ fontFamily: "Libre Baskerville, serif" }}
        >
          What Now?
        </h1>

        {loading ? (
          <p className="text-sm text-white/50">Loading…</p>
        ) : !isConnected ? (
          <>
            {configError ? (
              <p className="max-w-md text-center text-sm text-red-400">{configError}</p>
            ) : null}
            <button
              type="button"
              onClick={() => void startCall()}
              disabled={Boolean(configError && !starting) || starting}
              className="h-48 w-48 rounded-full bg-[#ff6b4a] text-xl font-semibold text-white shadow-2xl transition-all hover:bg-[#ff5530] active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {starting ? "Connecting…" : "Call Now"}
            </button>
            <p className="max-w-sm text-center text-xs text-white/40">
              Vapi = voice only. LLM: {llmUrl || "…"}/chat/completions
            </p>
            {debugInfo ? (
              <p className="max-w-md text-center font-mono text-[10px] text-white/30">
                {debugInfo}
              </p>
            ) : null}
          </>
        ) : (
          <>
            <VoiceOrb state={orbState} />

            {transcript.length > 0 && (
              <div className="max-w-md space-y-2 text-sm text-white/70">
                {transcript.slice(-4).map((line, index) => (
                  <p key={`${line.role}-${index}`}>
                    <span className="uppercase text-white/40">{line.role}:</span>{" "}
                    {line.text}
                  </p>
                ))}
              </div>
            )}

            <button
              type="button"
              onClick={endCall}
              className="rounded-full border border-white/20 px-6 py-3 text-sm text-white/60"
            >
              End Call
            </button>
          </>
        )}
      </div>
    </>
  );
}
