"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { normalizePhoneE164 } from "@/lib/phone";
import { createClient } from "@/lib/supabase/server";

export type PhoneSettingsState = {
  error?: string;
  success?: string;
};

export async function savePhoneNumber(
  _prev: PhoneSettingsState,
  formData: FormData,
): Promise<PhoneSettingsState> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const rawPhone = String(formData.get("phone") ?? "");
  const phoneE164 = normalizePhoneE164(rawPhone);

  if (!phoneE164) {
    return {
      error: "Enter a valid phone number (US 10-digit or +1... format).",
    };
  }

  const { data: existing } = await supabase
    .from("profiles")
    .select("user_id")
    .eq("phone_e164", phoneE164)
    .maybeSingle();

  if (existing && existing.user_id !== user.id) {
    return {
      error: "That phone number is already linked to another account.",
    };
  }

  const { error } = await supabase.from("profiles").upsert(
    {
      user_id: user.id,
      phone_e164: phoneE164,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "user_id" },
  );

  if (error) {
    return { error: error.message };
  }

  revalidatePath("/");
  revalidatePath("/settings/phone");

  return {
    success: "Phone number saved. Calls from this number will appear on your dashboard.",
  };
}
