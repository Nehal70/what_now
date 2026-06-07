"use server";

import { redirect } from "next/navigation";

import { FREE_PLAN } from "@/lib/plan";
import { createClient } from "@/lib/supabase/server";

export async function selectFreePlan() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { error } = await supabase.auth.updateUser({
    data: { plan: FREE_PLAN },
  });

  if (error) {
    redirect(`/choose-plan?error=${encodeURIComponent(error.message)}`);
  }

  redirect("/");
}
