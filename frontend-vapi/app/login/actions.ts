"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { formatAuthRedirectError } from "@/lib/auth-errors";
import { createClient } from "@/lib/supabase/server";

export async function sendMagicLink(formData: FormData) {
  const email = formData.get("email");

  if (typeof email !== "string" || !email.includes("@")) {
    redirect("/login?error=Enter+a+valid+email");
  }

  const supabase = await createClient();
  const headerList = await headers();
  const origin =
    headerList.get("origin") ??
    process.env.NEXT_PUBLIC_SITE_URL ??
    "http://localhost:3000";

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${origin}/auth/callback`,
    },
  });

  if (error) {
    redirect(
      `/login?error=${encodeURIComponent(formatAuthRedirectError(error.message))}`,
    );
  }

  redirect("/login?sent=1");
}
