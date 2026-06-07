import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import LatencyProfiler, run_agent, run_agent_stream, warmup_llm
from incident_stack import CLEANUP_INTERVAL_SECONDS, cleanup_expired_sessions
from lib.events import bind_event_queue, clear_event_queue
from tools.nearby_search import emit_nearby

load_dotenv(override=True)

START_RESPONSE = {
    "response": "I'm here. Are you hurt?",
    "tool_called": None,
    "reasoning": "Initial greeting",
    "latency_ms": 0,
    "phase": "questioning",
    "profile": [{"step": "request_received", "ms": 0}, {"step": "response_complete", "ms": 0}],
}

NEARBY_SIDE_EVENT_TIMEOUT = 35.0


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


class ChatRequest(BaseModel):
    transcript: str
    conversation_history: list[HistoryMessage] = []
    context: dict = {}
    location: Optional[Location] = None
    session_id: Optional[str] = None


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


def _merged_context(request: ChatRequest, result_context: dict | None = None) -> dict:
    merged = dict(request.context or {})
    if result_context:
        merged.update(result_context)
    return merged


def _trigger_medical_nearby(request: ChatRequest) -> None:
    if not request.location:
        return
    asyncio.create_task(
        emit_nearby(
            query="urgent care open now",
            lat=request.location.lat,
            lng=request.location.lng,
            event_type="nearby_medical",
            count=5,
        )
    )
    print(f"[NEARBY] Medical search triggered at call start")


def _maybe_trigger_legal_nearby(request: ChatRequest, result: dict) -> None:
    if result.get("tool_called") != "legal_tool" or not request.location:
        return

    ctx = _merged_context(request, result.get("context"))
    if ctx.get("nearby_legal_fired"):
        return

    asyncio.create_task(
        emit_nearby(
            query="personal injury attorney free consultation slip fall",
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    if request.transcript == "__START__":
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
                request.transcript, history, profiler, session_id
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
