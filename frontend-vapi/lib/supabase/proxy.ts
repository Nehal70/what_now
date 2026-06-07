import { NextResponse, type NextRequest } from "next/server";

/** Auth disabled for demo — all routes pass through without Supabase session checks. */
export async function updateSession(request: NextRequest) {
  return NextResponse.next({ request });
}
