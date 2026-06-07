"use client";

import { useEffect, useRef } from "react";

import type { ConversationMessage } from "@/lib/types";

type LiveTranscriptProps = {
  messages: ConversationMessage[];
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
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </>
  );
}
