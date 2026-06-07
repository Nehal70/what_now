"""Request-scoped SSE side-event queue for background tasks."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from typing import Any

_event_queue: ContextVar[asyncio.Queue | None] = ContextVar("event_queue", default=None)


def bind_event_queue(queue: asyncio.Queue) -> None:
    _event_queue.set(queue)


def clear_event_queue() -> None:
    _event_queue.set(None)


def emit_event(event: dict[str, Any]) -> None:
    queue = _event_queue.get()
    if queue is None:
        return
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        print("[EVENTS] Queue full — dropping side event")


async def drain_side_events(
    queue: asyncio.Queue,
    *,
    timeout: float = 35.0,
    poll_interval: float = 0.25,
) -> list[dict[str, Any]]:
    """Collect side events until timeout with no new events."""
    events: list[dict[str, Any]] = []
    idle = 0.0
    while idle < timeout:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=poll_interval)
            events.append(event)
            idle = 0.0
        except asyncio.TimeoutError:
            idle += poll_interval
    return events
