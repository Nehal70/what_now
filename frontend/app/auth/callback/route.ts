import { type NextRequest, NextResponse } from "next/server";

import { getPostAuthPath } from "@/lib/plan";
import { createClient } from "@/lib/supabase/server";

function redirectAfterAuth(request: NextRequest, origin: string, path: string) {
  const forwardedHost = request.headers.get("x-forwarded-host");
  const isLocalEnv = process.env.NODE_ENV === "development";

  if (isLocalEnv) {
    return NextResponse.redirect(`${origin}${path}`);
  }

  if (forwardedHost) {
    return NextResponse.redirect(`https://${forwardedHost}${path}`);
  }

  return NextResponse.redirect(`${origin}${path}`);
}

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      const path = getPostAuthPath(user?.user_metadata);

      return redirectAfterAuth(request, origin, path);
    }
  }

  const redirectTo = new URL("/login", origin);
  redirectTo.searchParams.set("error", "Invalid+or+expired+link");
  return NextResponse.redirect(redirectTo);
}
