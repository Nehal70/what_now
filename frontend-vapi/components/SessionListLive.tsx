"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import ImageUploadPanel from "@/components/ImageUploadPanel";
import SessionCard from "@/components/SessionCard";
import { createClient } from "@/lib/supabase/client";
import type { Session } from "@/lib/types";

type SessionListLiveProps = {
  userId: string;
  initialActive: Session | null;
  initialPast: Session[];
  dialNumber: string | null;
  registeredPhone: string | null;
};

export default function SessionListLive({
  userId,
  initialActive,
  initialPast,
  dialNumber,
  registeredPhone,
}: SessionListLiveProps) {
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();

    const channel = supabase
      .channel(`sessions:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "sessions",
          filter: `user_id=eq.${userId}`,
        },
        () => {
          router.refresh();
        },
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [router, userId]);

  return (
    <>
      {!registeredPhone ? (
        <div className="dashboard-alert">
          <p>
            Link your phone first so calls show up here.{" "}
            <a href="/settings/phone">Add phone number →</a>
          </p>
        </div>
      ) : null}

      {dialNumber ? (
        <div className="dashboard-call-cta">
          <p className="dashboard-call-label">Call to start a session</p>
          <a href={`tel:${dialNumber}`} className="num dashboard-dial">
            {dialNumber}
          </a>
          <p className="dashboard-call-hint">
            Use your registered phone ({registeredPhone}). Keep this page open
            while you talk.
          </p>
        </div>
      ) : (
        <div className="dashboard-alert">
          <p>
            Set <code>VAPI_PHONE_NUMBER</code> in <code>.env.local</code> to
            show the number to dial.
          </p>
        </div>
      )}

      {initialActive ? (
        <section className="session-section">
          <h2 className="session-section-title">Active now</h2>
          <SessionCard session={initialActive} live />
          <ImageUploadPanel
            sessionId={initialActive.id}
            isLive={initialActive.status === "active"}
          />
        </section>
      ) : null}

      <section className="session-section">
        <h2 className="session-section-title">Past sessions</h2>
        {initialPast.length === 0 ? (
          <div className="dashboard-empty">
            <p>No past sessions yet.</p>
          </div>
        ) : (
          <div className="session-list">
            {initialPast.map((session) => (
              <SessionCard key={session.id} session={session} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
