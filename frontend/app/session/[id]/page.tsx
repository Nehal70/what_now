import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import SessionView from "@/components/SessionView";
import {
  getMessagesForSession,
  getSessionById,
} from "@/lib/sessions";
import { createClient } from "@/lib/supabase/server";
import type { ConversationMessage } from "@/lib/types";

import "../../homepage.css";

type SessionPageProps = {
  params: Promise<{ id: string }>;
};

export default async function SessionPage({ params }: SessionPageProps) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { id } = await params;
  const session = await getSessionById(id);

  if (!session || session.userId !== user.id) {
    notFound();
  }

  let messages: ConversationMessage[] = [];

  try {
    const rows = await getMessagesForSession(id);
    messages = rows.map((row) => ({
      role: row.role,
      text: row.text,
    }));
  } catch {
    // Service role may be missing during setup.
  }

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

      <main className="user-dashboard session-page">
        <SessionView session={session} initialMessages={messages} />
      </main>
    </div>
  );
}
