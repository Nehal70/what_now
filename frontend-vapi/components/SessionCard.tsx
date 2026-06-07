"use client";

import Link from "next/link";

import type { Session } from "@/lib/types";
import { formatPhoneDisplay } from "@/lib/phone";

type SessionCardProps = {
  session: Session;
  live?: boolean;
};

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function SessionCard({ session, live = false }: SessionCardProps) {
  return (
    <Link href={`/session/${session.id}`} className="session-card">
      <div className="session-card-header">
        <span className={`session-status ${live ? "session-status-live" : ""}`}>
          {live ? "Live call" : "Past session"}
        </span>
        <span className="session-when">{formatWhen(session.startedAt)}</span>
      </div>
      <h2 className="session-card-title">
        {session.title ?? "Phone call"}
      </h2>
      <p className="session-card-meta">
        From {formatPhoneDisplay(session.callerPhone)}
        {session.phase ? ` · ${session.phase}` : ""}
      </p>
    </Link>
  );
}
