import Link from "next/link";
import { redirect } from "next/navigation";

import LocationCapture from "@/components/LocationCapture";
import SessionListLive from "@/components/SessionListLive";
import { formatPhoneDisplay } from "@/lib/phone";
import { listSessionsForUser } from "@/lib/sessions";
import { createClient } from "@/lib/supabase/server";

import "./homepage.css";

type HomeDashboardProps = {
  email: string;
  userId: string;
};

export default async function HomeDashboard({
  email,
  userId,
}: HomeDashboardProps) {
  const supabase = await createClient();

  const { data: profile } = await supabase
    .from("profiles")
    .select("phone_e164")
    .eq("user_id", userId)
    .maybeSingle();

  let active = null;
  let past: Awaited<ReturnType<typeof listSessionsForUser>>["past"] = [];

  try {
    const sessions = await listSessionsForUser(userId);
    active = sessions.active;
    past = sessions.past;
  } catch {
    // Service role key may be missing during local setup.
  }

  const dialNumber =
    process.env.NEXT_PUBLIC_PHONE_NUMBER ??
    process.env.LIVEKIT_PHONE_NUMBER ??
    null;

  const registeredPhone = profile?.phone_e164
    ? formatPhoneDisplay(profile.phone_e164)
    : null;

  return (
    <div className="home">
      <LocationCapture />
      <nav className="site-nav" aria-label="Primary">
        <span className="logo">What Now</span>
        <div className="links">
          <span className="nav-user">{email}</span>
          <Link href="/settings/phone" className="nav-auth">
            Phone
          </Link>
          <form action="/auth/signout" method="post">
            <button type="submit" className="nav-auth">
              Sign out
            </button>
          </form>
        </div>
      </nav>

      <main className="user-dashboard">
        <p className="section-kicker">Dashboard</p>
        <h1 className="dashboard-title">Your sessions</h1>
        <p className="dashboard-sub">
          Call from your phone to start a session. Transcripts appear here in
          real time.
        </p>

        <SessionListLive
          userId={userId}
          initialActive={active}
          initialPast={past}
          dialNumber={dialNumber}
          registeredPhone={registeredPhone}
        />
      </main>
    </div>
  );
}
