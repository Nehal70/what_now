import Link from "next/link";
import { redirect } from "next/navigation";

import PhoneSettingsForm from "@/app/settings/phone/PhoneSettingsForm";
import { formatPhoneDisplay } from "@/lib/phone";
import { createClient } from "@/lib/supabase/server";

import "../../homepage.css";

export default async function PhoneSettingsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("phone_e164")
    .eq("user_id", user.id)
    .maybeSingle();

  const dialNumber =
    process.env.NEXT_PUBLIC_PHONE_NUMBER ??
    process.env.VAPI_PHONE_NUMBER ??
    "";

  return (
    <div className="home">
      <nav className="site-nav" aria-label="Primary">
        <Link href="/" className="logo">
          What Now
        </Link>
        <div className="links">
          <Link href="/">Dashboard</Link>
        </div>
      </nav>

      <main className="user-dashboard">
        <p className="section-kicker">Settings</p>
        <h1 className="dashboard-title">Phone number</h1>
        <p className="dashboard-sub">
          Link the phone you call from. When you dial our number, a session
          appears on your dashboard automatically.
        </p>

        {dialNumber ? (
          <p className="dashboard-sub">
            Call{" "}
            <a href={`tel:${dialNumber}`} className="session-phone-link">
              {formatPhoneDisplay(dialNumber)}
            </a>{" "}
            from this phone after saving.
          </p>
        ) : null}

        {profile?.phone_e164 ? (
          <p className="dashboard-sub">
            Current number:{" "}
            <strong>{formatPhoneDisplay(profile.phone_e164)}</strong>
          </p>
        ) : null}

        <PhoneSettingsForm defaultPhone={profile?.phone_e164 ?? ""} />
      </main>
    </div>
  );
}
