import { EventEmitter } from "events";

import type { SSEEvent } from "./types";

const emitter = new EventEmitter();
emitter.setMaxListeners(100);

const GLOBAL_EVENT = "sse";
const sessionEventName = (sessionId: string) => `sse:${sessionId}`;

export function emitEvent(event: SSEEvent): void {
  emitter.emit(GLOBAL_EVENT, event);
}

export function subscribeToEvents(
  callback: (event: SSEEvent) => void,
): () => void {
  emitter.on(GLOBAL_EVENT, callback);
  return () => {
    emitter.off(GLOBAL_EVENT, callback);
  };
}

export function emitSessionEvent(sessionId: string, event: SSEEvent): void {
  emitter.emit(sessionEventName(sessionId), event);
  emitter.emit(GLOBAL_EVENT, event);
}

export function subscribeToSessionEvents(
  sessionId: string,
  callback: (event: SSEEvent) => void,
): () => void {
  const name = sessionEventName(sessionId);
  emitter.on(name, callback);
  return () => {
    emitter.off(name, callback);
  };
}
