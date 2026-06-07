import { NextResponse } from "next/server";

import { verifyInternalAuth } from "@/lib/internal-auth";
import { normalizePhoneE164 } from "@/lib/phone";
import {
  createSessionFromCall,
  findUserIdByPhone,
} from "@/lib/sessions";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!verifyInternalAuth(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = (await request.json()) as {
      caller_phone?: string;
      vapi_call_id?: string | null;
      livekit_room?: string | null;
    };

    const callerPhone = normalizePhoneE164(body.caller_phone ?? "");
    if (!callerPhone) {
      return NextResponse.json(
        { error: "invalid_phone", message: "Could not parse caller phone number" },
        { status: 400 },
      );
    }

    const userId = await findUserIdByPhone(callerPhone);
    if (!userId) {
      return NextResponse.json(
        {
          error: "phone_not_registered",
          message:
            "No account linked to this phone number. Register it at /settings/phone",
        },
        { status: 404 },
      );
    }

    const session = await createSessionFromCall({
      userId,
      callerPhone,
      livekitRoom: body.vapi_call_id ?? body.livekit_room ?? null,
    });

    return NextResponse.json({
      session_id: session.id,
      user_id: session.userId,
      status: session.status,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
