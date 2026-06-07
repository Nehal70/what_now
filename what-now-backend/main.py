import asyncio
import hashlib
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import LatencyProfiler, run_agent, run_agent_stream, warmup_llm
from incident_stack import CLEANUP_INTERVAL_SECONDS, cleanup_expired_sessions, get_or_create_stack
from lib.dashboard_context import dashboard_context
from lib.call_location import (
    get_call_location,
    mark_nearby_medical_emitted,
    register_call_location,
)
from lib.events import bind_event_queue, clear_event_queue, emit_event
from tools.demo_guidance import (
    AUSTIN_DEMO_LEGAL,
    AUSTIN_DEMO_MEDICAL,
    FINAL_DEMO_OPENING,
)
from tools.jake_demo import is_jake_demo_mode, jake_demo_stack_id

DEMO_RESPONSE_DELAY_S = 0.55
from tools.nearby_search import emit_nearby, nearby_search

load_dotenv(override=True)

START_RESPONSE = {
    "response": FINAL_DEMO_OPENING,
    "tool_called": None,
    "reasoning": "Initial greeting",
    "latency_ms": 0,
    "phase": "questioning",
    "profile": [{"step": "request_received", "ms": 0}, {"step": "response_complete", "ms": 0}],
}

NEARBY_SIDE_EVENT_TIMEOUT = 35.0
NEXTJS_URL = os.getenv("NEXTJS_URL", "")
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "")

DEMO_MEDICAL_PLACES = [
    {
        "name": "Concentra Urgent Care",
        "address": "342 Kearny St",
        "phone": "(415) 362-8383",
        "rating": 4.7,
        "distance": "0.3 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "Carbon Health",
        "address": "590 California St",
        "phone": "(415) 967-3461",
        "rating": 4.8,
        "distance": "0.4 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "One Medical",
        "address": "1 Embarcadero",
        "phone": "(415) 288-1245",
        "rating": 4.6,
        "distance": "0.6 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "UCSF Urgent Care",
        "address": "400 Parnassus Ave",
        "phone": "(415) 353-2000",
        "rating": 4.5,
        "distance": "1.8 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "SF General ER",
        "address": "995 Potrero Ave",
        "phone": "(415) 206-8000",
        "rating": 4.2,
        "distance": "1.2 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
]

DEMO_LEGAL_PLACES = [
    {
        "name": "Bay Area Injury Law",
        "address": "555 Market St, San Francisco, CA",
        "phone": "(415) 555-0101",
        "rating": 4.9,
        "distance": "0.5 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "SF Personal Injury Group",
        "address": "100 Pine St, San Francisco, CA",
        "phone": "(415) 555-0102",
        "rating": 4.8,
        "distance": "0.7 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "Golden Gate Legal",
        "address": "50 California St, San Francisco, CA",
        "phone": "(415) 555-0103",
        "rating": 4.7,
        "distance": "0.4 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "Pacific Coast Attorneys",
        "address": "201 Mission St, San Francisco, CA",
        "phone": "(415) 555-0104",
        "rating": 4.6,
        "distance": "0.8 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
    {
        "name": "Embarcadero Injury Lawyers",
        "address": "1 Embarcadero Center, San Francisco, CA",
        "phone": "(415) 555-0105",
        "rating": 4.5,
        "distance": "0.6 mi",
        "open_now": True,
        "maps_url": "https://maps.google.com",
    },
]
VAPI_CUSTOM_LLM_BASE = (
    os.getenv("VAPI_CUSTOM_LLM_BASE")
    or os.getenv("PUBLIC_BACKEND_URL")
    or os.getenv("BACKEND_ENDPOINT")
    or ""
).rstrip("/")
VAPI_ASSISTANT_ID = (
    os.getenv("VAPI_ASSISTANT_ID")
    or os.getenv("NEXT_PUBLIC_VAPI_ASSISTANT_ID")
    or ""
)


async def _run_periodic_cleanup() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        cleanup_expired_sessions()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(warmup_llm)

    try:
        from tools.moss_retrieval import run as moss_run

        await asyncio.to_thread(moss_run, "insurance coverage Texas")
        print("[warmup] Moss index warmed")
    except Exception as e:
        print(f"[warmup] Moss warmup failed: {e}")

    cleanup_task = asyncio.create_task(_run_periodic_cleanup())
    yield
    cleanup_task.cancel()


app = FastAPI(title="What Now Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: str
    text: str


class Location(BaseModel):
    lat: float
    lng: float


class VapiLocationRequest(BaseModel):
    lat: float
    lng: float
    call_id: Optional[str] = None


class SessionImage(BaseModel):
    id: str
    url: str
    mime_type: str
    uploaded_at: int


class ChatRequest(BaseModel):
    transcript: str
    conversation_history: list[HistoryMessage] = []
    context: dict = {}
    location: Optional[Location] = None
    session_id: Optional[str] = None
    images: list[SessionImage] | None = None


class ChatResponse(BaseModel):
    response: str
    tool_called: str | None
    reasoning: str | None
    latency_ms: int
    profile: list[dict] | None = None
    session_id: Optional[str] = None
    phase: Optional[str] = None
    context: Optional[dict] = None


def _history_payload(request: ChatRequest) -> list[dict]:
    return [msg.model_dump() for msg in request.conversation_history]


def _images_payload(request: ChatRequest) -> list[dict] | None:
    if not request.images:
        return None
    return [img.model_dump() for img in request.images]


IMAGE_UPLOAD_TOKEN = "__IMAGE_UPLOAD__"


def _user_transcript_label(transcript: str, image_count: int = 0) -> str:
    if transcript == IMAGE_UPLOAD_TOKEN:
        if image_count == 1:
            return "📷 Sent 1 photo"
        return f"📷 Sent {image_count or 1} photos"
    return transcript


def _merged_context(request: ChatRequest, result_context: dict | None = None) -> dict:
    merged = dict(request.context or {})
    if result_context:
        merged.update(result_context)
    return merged


async def _push_dashboard_events(events: list[dict]) -> None:
    if not NEXTJS_URL or not INTERNAL_API_SECRET:
        print("[VAPI] Dashboard push skipped — set NEXTJS_URL + INTERNAL_API_SECRET")
        return
    url = f"{NEXTJS_URL.rstrip('/')}/api/internal/events"
    last_error: Exception | None = None
    try:
        payload = json.dumps({"events": events})
    except (TypeError, ValueError) as exc:
        print(f"[VAPI] Dashboard push skipped — non-serializable events: {exc!r}")
        return
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    content=payload,
                    headers={
                        "Authorization": f"Bearer {INTERNAL_API_SECRET}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code >= 400:
                    print(
                        f"[VAPI] Dashboard push failed: {resp.status_code} {resp.text[:200]}"
                    )
                    return
                print(f"[VAPI] Dashboard push ok ({len(events)} events)")
                return
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
    print(f"[VAPI] Dashboard event push failed after retries: {last_error!r}")


async def _emit_nearby_with_dashboard(
    query: str,
    lat: float,
    lng: float,
    event_type: str,
    count: int = 5,
) -> None:
    """Run Apify search and push results to dashboard (and SSE queue if bound)."""
    print(f"[APIFY] Firing search: {query} @ {lat:.4f},{lng:.4f}")
    places = await nearby_search(query, lat, lng, count)
    if not places:
        print(f"[APIFY] No results — using demo fallback for {event_type}")
        places = DEMO_MEDICAL_PLACES if event_type == "nearby_medical" else DEMO_LEGAL_PLACES

    event = {
        "type": event_type,
        "data": {"places": places, "query": query},
        "timestamp": int(time.time() * 1000),
    }
    print(f"[APIFY] Emitting {event_type} with {len(places)} places")
    emit_event(event)
    await _push_dashboard_events([event])
    print(f"[APIFY] Pushed {event_type} to dashboard ({NEXTJS_URL or 'no NEXTJS_URL'})")


def _trigger_medical_nearby(request: ChatRequest) -> None:
    if not request.location:
        print("[LOCATION] __START__ with no location — skipping nearby")
        return
    print(f"[LOCATION] Received: lat={request.location.lat}, lng={request.location.lng}")
    if not mark_nearby_medical_emitted():
        print("[NEARBY] Medical search already fired — skipping duplicate")
        return
    asyncio.create_task(
        _emit_nearby_with_dashboard(
            query="urgent care open now",
            lat=request.location.lat,
            lng=request.location.lng,
            event_type="nearby_medical",
            count=5,
        )
    )
    print("[NEARBY] Medical search triggered at call start")


def _maybe_trigger_legal_nearby(request: ChatRequest, result: dict) -> None:
    if result.get("tool_called") != "legal_tool" or not request.location:
        return

    ctx = _merged_context(request, result.get("context"))
    if ctx.get("nearby_legal_fired"):
        return

    asyncio.create_task(
        _emit_nearby_with_dashboard(
            query="personal injury attorney free consultation",
            lat=request.location.lat,
            lng=request.location.lng,
            event_type="nearby_legal",
            count=5,
        )
    )
    result_ctx = dict(result.get("context") or {})
    result_ctx["nearby_legal_fired"] = True
    result["context"] = result_ctx
    print("[NEARBY] Legal search triggered")


def _extract_vapi_location(body: dict, call_id: str | None = None) -> tuple[float, float] | None:
    """Read lat/lng from Vapi metadata or dashboard-registered location."""
    sources: list[dict] = [
        body.get("metadata") or {},
        (body.get("call") or {}).get("metadata") or {},
    ]
    assistant = body.get("assistant") or {}
    if isinstance(assistant, dict):
        sources.append(assistant.get("metadata") or {})
    overrides = body.get("assistantOverrides") or {}
    if isinstance(overrides, dict):
        sources.append(overrides.get("metadata") or {})

    for source in sources:
        if not isinstance(source, dict):
            continue
        lat = source.get("lat") if source.get("lat") is not None else source.get("latitude")
        lng = source.get("lng") if source.get("lng") is not None else source.get("longitude")
        if lat is None or lng is None:
            continue
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            continue

    return get_call_location(call_id)


def _trigger_vapi_medical_nearby(call_id: str, lat: float, lng: float) -> None:
    """Once per session — Apify urgent care search."""
    if not mark_nearby_medical_emitted():
        print(f"[NEARBY] Medical already fired — skip for call {call_id}")
        return
    stack = get_or_create_stack(call_id)
    stack.data["nearby_medical_fired"] = True
    print(f"[LOCATION] Received: lat={lat}, lng={lng} (call {call_id})")
    asyncio.create_task(
        _emit_nearby_with_dashboard(
            query="urgent care open now",
            lat=lat,
            lng=lng,
            event_type="nearby_medical",
            count=5,
        )
    )
    print(f"[NEARBY] Vapi medical search triggered for call {call_id}")


def _maybe_trigger_vapi_legal_nearby(
    call_id: str,
    lat: float,
    lng: float,
    result: dict,
) -> None:
    if result.get("tool_called") != "legal_tool":
        return
    stack = get_or_create_stack(call_id)
    if stack.data.get("nearby_legal_fired"):
        return
    stack.data["nearby_legal_fired"] = True
    asyncio.create_task(
        _emit_nearby_with_dashboard(
            query="personal injury attorney free consultation",
            lat=lat,
            lng=lng,
            event_type="nearby_legal",
            count=5,
        )
    )
    ctx = dict(result.get("context") or {})
    ctx["nearby_legal_fired"] = True
    result["context"] = ctx
    print(f"[NEARBY] Vapi legal search triggered for call {call_id}")


async def _yield_side_events(queue: asyncio.Queue):
    idle = 0.0
    while idle < NEARBY_SIDE_EVENT_TIMEOUT:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.25)
            yield event
            idle = 0.0
        except asyncio.TimeoutError:
            idle += 0.25


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _vapi_dashboard_events(
    transcript: str,
    result: dict,
    call_id: str | None = None,
    image_count: int = 0,
) -> list[dict]:
    ts = int(time.time() * 1000)
    live_payload: dict = {"state": "live"}
    if call_id:
        live_payload["call_id"] = call_id
    events = [
        {
            "type": "call_state",
            "data": live_payload,
            "timestamp": ts,
        },
        {
            "type": "transcript",
            "data": {
                "role": "user",
                "text": _user_transcript_label(transcript, image_count),
            },
            "timestamp": ts,
        },
        {
            "type": "call_state",
            "data": {"state": "thinking"},
            "timestamp": ts,
        },
        {
            "type": "tool",
            "data": {"tool_called": result.get("tool_called")},
            "timestamp": ts,
        },
        {
            "type": "reasoning",
            "data": {"reasoning": result.get("reasoning") or ""},
            "timestamp": ts,
        },
        {
            "type": "latency",
            "data": {"latency_ms": result.get("latency_ms", 0)},
            "timestamp": ts,
        },
        {
            "type": "phase",
            "data": {"phase": result.get("phase")},
            "timestamp": ts,
        },
        {
            "type": "context",
            "data": dashboard_context(result.get("context") or {}),
            "timestamp": ts,
        },
        {
            "type": "transcript",
            "data": {
                "role": "assistant",
                "text": result.get("response", ""),
                "tool_called": result.get("tool_called"),
            },
            "timestamp": ts,
        },
        {
            "type": "call_state",
            "data": {"state": "speaking"},
            "timestamp": ts,
        },
    ]
    ctx = result.get("context") or {}
    if ctx.get("awaiting_image") or result.get("emit_image_requested"):
        events.append(
            {
                "type": "image_requested",
                "data": {
                    "prompt": ctx.get("image_prompt")
                    or "Send photo of the damage to your car",
                },
                "timestamp": ts,
            }
        )
    if result.get("emit_image_processed"):
        events.append(
            {
                "type": "image_processed",
                "data": {
                    "summary": "Structural damage confirmed from photo",
                    "image_count": ctx.get("demo_images_received", image_count or 1),
                },
                "timestamp": ts,
            }
        )
    return events


def _message_content(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text") or ""))
        return " ".join(parts)
    return ""


def _parse_vapi_messages(body: dict, request: Request | None = None) -> tuple[str, list[dict], str]:
    call_meta = body.get("call") or {}
    metadata = body.get("metadata") or {}
    message = body.get("message") or {}
    msg_call = (message.get("call") if isinstance(message, dict) else None) or {}

    call_id: str | None = None
    for candidate in (
        call_meta.get("id"),
        body.get("callId"),
        body.get("call_id"),
        metadata.get("callId"),
        metadata.get("call_id"),
        msg_call.get("id") if isinstance(msg_call, dict) else None,
    ):
        if candidate:
            call_id = str(candidate)
            break

    if not call_id and request is not None:
        for header in ("x-vapi-call-id", "x-call-id", "call-id"):
            header_val = request.headers.get(header)
            if header_val:
                call_id = header_val
                break

    messages = body.get("messages") or []
    if not call_id and messages:
        first_user = next((m for m in messages if m.get("role") == "user"), None)
        if first_user:
            seed = _message_content(first_user)
            if seed:
                call_id = f"vapi-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"

    if not call_id:
        call_id = str(uuid.uuid4())

    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        return "", [], call_id

    transcript = _message_content(user_messages[-1])
    history: list[dict] = []
    for msg in messages[:-1]:
        role = msg.get("role")
        if role in ("user", "assistant"):
            history.append({"role": role, "text": _message_content(msg)})

    return transcript, history, call_id


async def _emit_demo_nearby(
    event_type: str,
    lat: float,
    lng: float,
) -> None:
    places = (
        AUSTIN_DEMO_MEDICAL if event_type == "nearby_medical" else AUSTIN_DEMO_LEGAL
    )
    event = {
        "type": event_type,
        "data": {"places": places, "query": "austin-demo"},
        "timestamp": int(time.time() * 1000),
    }
    emit_event(event)
    await _push_dashboard_events([event])
    print(f"[DEMO] Pushed {event_type} ({len(places)} Austin cards)")


async def _schedule_dashboard_events(
    transcript: str,
    result: dict,
    call_id: str,
    coords: tuple[float, float] | None,
    image_count: int = 0,
) -> None:
    splits = result.get("dashboard_splits")
    if splits:
        for idx, part in enumerate(splits):
            delay = float(part.get("dashboard_delay_s") or 0)
            if delay > 0:
                await asyncio.sleep(delay)
            part_result = {**result, **part}
            await _push_dashboard_events(
                _vapi_dashboard_events(
                    transcript if idx == 0 else "",
                    part_result,
                    call_id or None,
                    image_count=image_count if idx == 0 else 0,
                )
            )
    else:
        delay = float(result.get("dashboard_delay_s") or 0)
        if delay > 0:
            await asyncio.sleep(delay)
        await _push_dashboard_events(
            _vapi_dashboard_events(
                transcript, result, call_id or None, image_count=image_count
            )
        )

    if coords and result.get("emit_nearby_medical"):
        await _emit_demo_nearby("nearby_medical", coords[0], coords[1])
    if coords and result.get("emit_nearby_legal"):
        await _emit_demo_nearby("nearby_legal", coords[0], coords[1])


async def _run_vapi_turn(
    transcript: str,
    history: list[dict],
    call_id: str,
    vapi_body: dict | None = None,
) -> dict:
    if not transcript.strip():
        if is_jake_demo_mode(call_id):
            stack = get_or_create_stack(jake_demo_stack_id(call_id))
            if stack.data.get("jake_pending_agent") or stack.data.get("jake_pending_voice"):
                profiler = LatencyProfiler()
                profiler.mark("request_received")
                result = await run_agent(" ", history, profiler, call_id)
                profile = result.get("profile") or profiler.checkpoints
                result["latency_ms"] = profile[-1]["ms"] if profile else 0
                asyncio.create_task(
                    _schedule_dashboard_events(" ", result, call_id, None, 0)
                )
                return result
        return {
            "response": FINAL_DEMO_OPENING,
            "tool_called": None,
            "reasoning": "Agent online — starting triage",
            "latency_ms": 0,
            "phase": "questioning",
        }

    coords = _extract_vapi_location(vapi_body or {}, call_id)
    if coords and not any(
        trigger in transcript.lower()
        for trigger in ("progressive", "medpay", "settlement", "4,000", "4000")
    ):
        _trigger_vapi_medical_nearby(call_id, coords[0], coords[1])

    if transcript.strip() and is_jake_demo_mode(call_id):
        stack = get_or_create_stack(jake_demo_stack_id(call_id))
        if transcript.strip() != stack.data.get("last_jake_committed_transcript"):
            await asyncio.sleep(DEMO_RESPONSE_DELAY_S)

    profiler = LatencyProfiler()
    profiler.mark("request_received")
    images = vapi_body.get("images") if vapi_body else None
    result = await run_agent(transcript, history, profiler, call_id, images=images)

    if coords and result.get("tool_called") == "legal_tool":
        _maybe_trigger_vapi_legal_nearby(call_id, coords[0], coords[1], result)

    profile = result.get("profile") or profiler.checkpoints
    latency_ms = profile[-1]["ms"] if profile else 0
    result["latency_ms"] = latency_ms

    image_count = len(images) if images else 0
    if not result.get("skip_dashboard_push"):
        asyncio.create_task(
            _schedule_dashboard_events(
                transcript, result, call_id, coords, image_count=image_count
            )
        )
    return result


def _openai_completion(content: str, model: str = "what-now") -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


async def _openai_stream(content: str, model: str = "what-now"):
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    yield _sse(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
    )

    chunk_size = 24
    for i in range(0, len(content), chunk_size):
        yield _sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": content[i : i + chunk_size]},
                        "finish_reason": None,
                    }
                ],
            }
        )

    yield _sse(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    yield "data: [DONE]\n\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model")
def model_info():
    return {"active_model": os.getenv("LLM_MODEL", "what-now")}


@app.post("/vapi/location")
async def vapi_location(request: VapiLocationRequest):
    """
    Judge dashboard posts geolocation when a call goes live.
    Fires Apify immediately so cards appear before first utterance.
    """
    register_call_location(request.lat, request.lng, request.call_id)
    print(f"[LOCATION] Dashboard registered {request.lat:.4f},{request.lng:.4f}")
    call_key = request.call_id or "__active__"
    _trigger_vapi_medical_nearby(call_key, request.lat, request.lng)
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    if request.transcript == "__START__":
        print(f"[LOCATION] /chat __START__ location={request.location}")
        if request.location:
            _trigger_medical_nearby(request)
        return ChatResponse(**START_RESPONSE, session_id=session_id)

    profiler = LatencyProfiler()
    profiler.mark("request_received")
    result = await run_agent(
        request.transcript,
        _history_payload(request),
        profiler,
        session_id,
        images=_images_payload(request),
    )

    _maybe_trigger_legal_nearby(request, result)

    profile = result.get("profile") or profiler.checkpoints
    latency_ms = profile[-1]["ms"] if profile else 0

    return ChatResponse(
        response=result["response"],
        tool_called=result.get("tool_called"),
        reasoning=result.get("reasoning"),
        latency_ms=latency_ms,
        profile=profile,
        session_id=session_id,
        phase=result.get("phase"),
        context=result.get("context"),
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    if request.transcript == "__START__":

        async def start_stream():
            queue: asyncio.Queue = asyncio.Queue()
            bind_event_queue(queue)
            try:
                print(f"[LOCATION] /chat/stream __START__ location={request.location}")
                if request.location:
                    _trigger_medical_nearby(request)

                yield _sse({"type": "token", "content": START_RESPONSE["response"]})
                yield _sse({"type": "done", "session_id": session_id, **START_RESPONSE})

                async for side_event in _yield_side_events(queue):
                    yield _sse(side_event)
            finally:
                clear_event_queue()

        return StreamingResponse(start_stream(), media_type="text/event-stream")

    profiler = LatencyProfiler()
    profiler.mark("request_received")
    history = _history_payload(request)

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()
        bind_event_queue(queue)
        try:
            async for event in run_agent_stream(
                request.transcript,
                history,
                profiler,
                session_id,
                images=_images_payload(request),
            ):
                if event.get("type") == "done":
                    event["session_id"] = session_id
                    _maybe_trigger_legal_nearby(request, event)
                yield _sse(event)

            async for side_event in _yield_side_events(queue):
                yield _sse(side_event)
        finally:
            clear_event_queue()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _wants_openai_response(body: dict) -> bool:
    """Browser custom-llm uses OpenAI-shaped bodies; phone/server uses {content}."""
    if body.get("stream"):
        return True
    if body.get("object") == "chat.completion":
        return True
    # OpenAI requests include model; simple Vapi webhook includes call.
    return bool(body.get("model")) and not body.get("call")


async def _vapi_chat_response(body: dict, request: Request | None = None):
    transcript, history, call_id = _parse_vapi_messages(body, request)
    model = body.get("model") or "what-now"
    try:
        result = await _run_vapi_turn(transcript, history, call_id, body)
    except Exception as exc:
        print(f"[VAPI] Turn failed for call {call_id}: {exc!r}")
        result = {
            "response": "I'm still here — tell me a bit more about what happened.",
            "tool_called": None,
            "reasoning": f"Vapi fallback after error: {exc}",
            "phase": "questioning",
            "context": {},
            "latency_ms": 0,
        }
    content = result.get("response") or "I'm here. Are you hurt?"

    if _wants_openai_response(body):
        if body.get("stream"):
            return StreamingResponse(
                _openai_stream(content, model),
                media_type="text/event-stream",
            )
        return _openai_completion(content, model)

    return {"content": content}


def _build_transient_assistant() -> dict:
    if not VAPI_CUSTOM_LLM_BASE:
        raise ValueError("VAPI_CUSTOM_LLM_BASE is not configured")
    return {
        "name": "What Now",
        "firstMessage": "I'm here. How can I help you?",
        "transcriber": {"provider": "deepgram", "model": "nova-2"},
        "voice": {"provider": "openai", "voiceId": "shimmer"},
        "model": {
            "provider": "custom-llm",
            "url": f"{VAPI_CUSTOM_LLM_BASE}/vapi",
            "model": "what-now",
        },
    }


def _assistant_request_response() -> dict:
    """Inbound phone calls: Vapi asks which assistant to use (<7.5s)."""
    if VAPI_CUSTOM_LLM_BASE:
        return {"assistant": _build_transient_assistant()}
    if VAPI_ASSISTANT_ID:
        return {"assistantId": VAPI_ASSISTANT_ID}
    return {"error": "What Now is temporarily unavailable. Please try again."}


async def _handle_vapi_server_side_effects(message: dict) -> None:
    msg_type = message.get("type")
    ts = int(time.time() * 1000)

    if msg_type == "status-update":
        status = message.get("status")
        call = message.get("call") or {}
        call_id = call.get("id") if isinstance(call, dict) else None
        if status in ("in-progress", "answered", "started", "ringing"):
            await _push_dashboard_events(
                [
                    {
                        "type": "call_state",
                        "data": {"state": "live", **({"call_id": call_id} if call_id else {})},
                        "timestamp": ts,
                    }
                ]
            )
        elif status in ("ended", "completed", "failed"):
            await _push_dashboard_events(
                [{"type": "call_state", "data": {"state": "idle"}, "timestamp": ts}]
            )
        return

    if msg_type == "transcript" and message.get("transcriptType") == "final":
        role = message.get("role")
        text = message.get("transcript") or ""
        if role in ("user", "assistant") and text:
            await _push_dashboard_events(
                [
                    {
                        "type": "transcript",
                        "data": {"role": role, "text": text},
                        "timestamp": ts,
                    }
                ]
            )
        return

    if msg_type == "end-of-call-report":
        await _push_dashboard_events(
            [{"type": "call_state", "data": {"state": "idle"}, "timestamp": ts}]
        )


@app.post("/vapi/server")
async def vapi_server(request: Request):
    """
    Vapi Server URL for inbound phone calls.
    Handles assistant-request (required) + dashboard events for status/transcripts.
    Configure in Vapi dashboard → Phone Numbers → Server URL:
      https://<your-ngrok>/vapi/server
    """
    body = await request.json()
    message = body.get("message") or {}

    if message.get("type") == "assistant-request":
        try:
            return _assistant_request_response()
        except ValueError as exc:
            return {"error": str(exc)}

    await _handle_vapi_server_side_effects(message)
    return {}


@app.post("/vapi/chat")
async def vapi_chat(request: Request):
    """Vapi custom LLM: phone returns {content}; browser may expect OpenAI format."""
    body = await request.json()
    return await _vapi_chat_response(body, request)


@app.post("/vapi/chat/completions")
async def vapi_chat_completions(request: Request):
    body = await request.json()
    return await _vapi_chat_response(body, request)


@app.post("/vapi/chat/chat/completions")
async def vapi_chat_completions_legacy(request: Request):
    """Fallback when custom LLM URL incorrectly ends with /vapi/chat."""
    body = await request.json()
    return await _vapi_chat_response(body, request)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
