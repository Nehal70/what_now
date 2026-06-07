import { subscribeToSessionEvents } from "@/lib/events";
import { createClient } from "@/lib/supabase/server";
import { getSessionById } from "@/lib/sessions";
import type { SSEEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(request: Request, context: RouteContext) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return new Response("Unauthorized", { status: 401 });
  }

  const { id } = await context.params;
  const session = await getSessionById(id);

  if (!session || session.userId !== user.id) {
    return new Response("Not found", { status: 404 });
  }

  const encoder = new TextEncoder();
  let heartbeat: ReturnType<typeof setInterval> | undefined;
  let unsubscribe: (() => void) | undefined;

  const stream = new ReadableStream({
    start(controller) {
      const send = (payload: SSEEvent | { type: "ping" }) => {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(payload)}\n\n`),
        );
      };

      unsubscribe = subscribeToSessionEvents(id, (event) => {
        send(event);
      });

      heartbeat = setInterval(() => {
        controller.enqueue(encoder.encode(`data: {"type":"ping"}\n\n`));
      }, 15000);
    },
    cancel() {
      if (heartbeat) clearInterval(heartbeat);
      if (unsubscribe) unsubscribe();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
