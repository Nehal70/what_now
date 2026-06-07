"use client";

import { useEffect, useState } from "react";

import ImageUploadPanel from "@/components/ImageUploadPanel";
import LiveTranscript from "@/components/LiveTranscript";
import type { ConversationMessage, Session } from "@/lib/types";
import { formatPhoneDisplay } from "@/lib/phone";

type SessionViewProps = {
  session: Session;
  initialMessages: ConversationMessage[];
};

export default function SessionView({
  session,
  initialMessages,
}: SessionViewProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>(initialMessages);
  const isLive = session.status === "active";

  useEffect(() => {
    if (!isLive) {
      return;
    }

    const source = new EventSource(`/api/sessions/${session.id}/events`);

    source.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as {
          type?: string;
          data?: { role?: string; text?: string };
        };

        if (parsed.type !== "transcript") {
          return;
        }

        const role = parsed.data?.role;
        const text = parsed.data?.text;

        if ((role !== "user" && role !== "assistant") || !text) {
          return;
        }

        setMessages((prev) => [...prev, { role, text }]);
      } catch {
        // ignore malformed events
      }
    };

    return () => {
      source.close();
    };
  }, [isLive, session.id]);

  return (
    <div className="session-view">
      <div className="session-view-header">
        <span
          className={`session-status ${isLive ? "session-status-live" : ""}`}
        >
          {isLive ? "Live" : "Completed"}
        </span>
        <h1 className="session-view-title">
          {session.title ?? "Phone call"}
        </h1>
        <p className="session-view-meta">
          {formatPhoneDisplay(session.callerPhone)}
          {session.phase ? ` · ${session.phase}` : ""}
        </p>
      </div>

      <div className="session-transcript-panel">
        <LiveTranscript messages={messages} />
      </div>

      <ImageUploadPanel sessionId={session.id} isLive={isLive} />

      {isLive ? (
        <p className="session-live-hint">
          Transcript updates while you talk on the phone.
        </p>
      ) : null}
    </div>
  );
}
