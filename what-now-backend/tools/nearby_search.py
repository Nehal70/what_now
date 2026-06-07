import asyncio
import os
import time

import httpx

from lib.events import emit_event

APIFY_RUN_URL = (
    "https://api.apify.com/v2/acts/"
    "compass~crawler-google-places"
    "/run-sync-get-dataset-items"
)


def _parse_open_now(hours: list) -> bool | None:
    for entry in hours:
        if not isinstance(entry, dict):
            continue
        if entry.get("isOpen") is not None:
            return entry.get("isOpen")
        text = (entry.get("hours") or "").lower()
        if "open 24 hours" in text or text.startswith("open"):
            return True
        if "closed" in text:
            return False
    return None


async def nearby_search(
    query: str,
    lat: float,
    lng: float,
    count: int = 5,
) -> list:
    """
    Search for nearby places using Apify Google Maps scraper.
    Returns list of place dicts.
    """
    apify_key = os.getenv("APIFY_API_KEY")
    print(f"[APIFY] Key present: {bool(apify_key)}")
    if not apify_key:
        print("[NEARBY] No Apify key — skipping")
        return []

    print(f"[APIFY] Firing search: {query} near {lat:.3f},{lng:.3f}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{APIFY_RUN_URL}?token={apify_key}&timeout=30&memory=256",
                json={
                    "searchStringsArray": [query],
                    "lat": lat,
                    "lng": lng,
                    "zoom": 14,
                    "maxCrawledPlacesPerSearch": count,
                    "language": "en",
                    "maxImages": 0,
                    "maxReviews": 0,
                    "includeHistogram": False,
                    "includeOpeningHours": True,
                    "includePeopleAlsoSearch": False,
                },
                timeout=35.0,
            )

            if response.status_code not in (200, 201):
                print(f"[NEARBY] Apify error: {response.status_code}")
                return []

            items = response.json()
            if not isinstance(items, list):
                print("[NEARBY] Apify returned unexpected payload")
                return []

            places = []

            for item in items[:count]:
                dist = item.get("distance")
                if dist:
                    if dist < 1:
                        dist_str = f"{int(dist * 5280)} ft"
                    else:
                        dist_str = f"{dist:.1f} mi"
                else:
                    dist_str = "Nearby"

                hours = item.get("openingHours", [])
                is_open = _parse_open_now(hours)

                places.append(
                    {
                        "name": item.get("title", ""),
                        "address": item.get("address", ""),
                        "phone": item.get("phone", ""),
                        "rating": item.get("totalScore"),
                        "distance": dist_str,
                        "open_now": is_open,
                        "maps_url": item.get("url", ""),
                    }
                )

            print(f"[NEARBY] Found {len(places)} places for: {query}")
            return places

    except Exception as e:
        print(f"[NEARBY] Error: {e}")
        return []


async def emit_nearby(
    query: str,
    lat: float,
    lng: float,
    event_type: str,
    count: int = 5,
):
    """
    Run nearby search and emit SSE event with results.
    Designed to run as background asyncio task.
    """
    print(f"[NEARBY] Searching: {query} near {lat:.3f},{lng:.3f}")

    places = await nearby_search(query, lat, lng, count)

    if places:
        emit_event(
            {
                "type": event_type,
                "data": {
                    "places": places,
                    "query": query,
                },
                "timestamp": int(time.time() * 1000),
            }
        )
        print(f"[APIFY] Emitting {event_type} with {len(places)} places")
    else:
        print(f"[APIFY] No results — not emitting {event_type}")
