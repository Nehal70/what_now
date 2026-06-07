import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";

import { getPostAuthPath } from "@/lib/plan";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;

  if (token_hash && type) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({
      type,
      token_hash,
    });

    if (!error) {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      const path = getPostAuthPath(user?.user_metadata);

      return NextResponse.redirect(new URL(path, origin));
    }
  }

  const redirectTo = request.nextUrl.clone();

  redirectTo.pathname = "/login";
  redirectTo.searchParams.set("error", "Invalid+or+expired+link");
  return NextResponse.redirect(redirectTo);
}
