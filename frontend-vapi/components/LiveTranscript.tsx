"use client";

import { useEffect, useRef } from "react";

import type { ToolName } from "@/lib/types";

export type TranscriptMessage = {
  role: "user" | "assistant";
  text: string;
  toolCalled?: ToolName;
};

const TOOL_COLORS: Record<Exclude<ToolName, null>, string> = {
  safety_check: "#ff4a4a",
  scene_guide: "#9ed4f5",
  moss_retrieval: "#ff6b4a",
  insurance_tool: "#9b6bff",
  legal_tool: "#5fd4a0",
};

type LiveTranscriptProps = {
  messages: TranscriptMessage[];
};

export default function LiveTranscript({ messages }: LiveTranscriptProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <>
      <style jsx global>{`
        .live-transcript-scroll::-webkit-scrollbar {
          display: none;
        }
        .live-transcript-scroll {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
      <div
        className="live-transcript-scroll"
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          padding: "4px 0",
        }}
      >
        {messages.map((message, index) => {
          const isUser = message.role === "user";
          const tool = message.toolCalled;
          const toolColor =
            tool && tool in TOOL_COLORS
              ? TOOL_COLORS[tool as Exclude<ToolName, null>]
              : "#ff6b4a";

          return (
            <div
              key={`${message.role}-${index}-${message.text.slice(0, 24)}`}
              style={{
                alignSelf: isUser ? "flex-end" : "flex-start",
                maxWidth: "80%",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  fontSize: 10,
                  color: "rgba(255,255,255,0.4)",
                  marginBottom: 4,
                  textAlign: isUser ? "right" : "left",
                }}
              >
                {isUser ? "You" : "What Now?"}
              </p>
              <div
                style={{
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  fontSize: 13,
                  lineHeight: 1.5,
                  padding: "12px 16px",
                  borderRadius: 12,
                  backgroundColor: isUser
                    ? "rgba(158,212,245,0.15)"
                    : "rgba(255,255,255,0.05)",
                  color: isUser ? "#9ed4f5" : "#ffffff",
                }}
              >
                {message.text}
              </div>
              {!isUser && tool ? (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    marginTop: 4,
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-ibm-plex-mono), monospace",
                      fontSize: 10,
                      opacity: 0.6,
                      color: "rgba(255,255,255,0.7)",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    {tool}
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        backgroundColor: toolColor,
                      }}
                    />
                  </span>
                </div>
              ) : null}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </>
  );
}
