"""Short-lived call location from the judge dashboard (browser geolocation)."""

from __future__ import annotations

import time

TTL_SECONDS = 600

# call_id -> {lat, lng, ts}; "__active__" = latest dashboard ping
_store: dict[str, dict[str, float]] = {}
_nearby_medical_emitted = False


def register_call_location(lat: float, lng: float, call_id: str | None = None) -> None:
    entry = {"lat": lat, "lng": lng, "ts": time.time()}
    _store["__active__"] = entry
    if call_id:
        _store[str(call_id)] = entry


def get_call_location(call_id: str | None = None) -> tuple[float, float] | None:
    now = time.time()
    for key in (call_id, "__active__"):
        if not key:
            continue
        entry = _store.get(str(key))
        if not entry:
            continue
        if now - entry["ts"] > TTL_SECONDS:
            _store.pop(str(key), None)
            continue
        return entry["lat"], entry["lng"]
    return None


def mark_nearby_medical_emitted() -> bool:
    """Return True if this is the first emit (caller should fire Apify)."""
    global _nearby_medical_emitted
    if _nearby_medical_emitted:
        return False
    _nearby_medical_emitted = True
    return True


def reset_nearby_medical_emitted() -> None:
    global _nearby_medical_emitted
    _nearby_medical_emitted = False
