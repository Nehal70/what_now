import { subscribeToEvents } from "@/lib/events";
import type { SSEEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
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

      unsubscribe = subscribeToEvents((event) => {
        send(event);
      });

      heartbeat = setInterval(() => {
        send({ type: "ping" });
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
