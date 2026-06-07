"""
What Now phone bridge agent.

Listens on SIP phone calls via LiveKit, forwards transcripts to Next.js
/api/respond (which calls Person 2's ngrok backend), and speaks responses
on the phone line.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("what-now-agent")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(Path(__file__).resolve().parent / ".env.local")

NEXTJS_URL = os.getenv("NEXTJS_URL", "http://localhost:3000").rstrip("/")
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "")
AGENT_NAME = os.getenv("AGENT_NAME", "what-now-agent")
START_TOKEN = "__START__"
IMAGE_UPLOAD_TOKEN = "__IMAGE_UPLOAD__"


class WhatNowBridge(Agent):
    def __init__(self, *, session_id: str | None) -> None:
        super().__init__(
            llm=inference.LLM(model="openai/gpt-4o-mini"),
            instructions=(
                "You are the What Now phone assistant. "
                "Keep replies brief and calm for voice."
            ),
        )
        self._session_id = session_id
        self._history: list[dict[str, str]] = []
        self._context: dict = {}
        self._started = False

    async def on_enter(self) -> None:
        if self._started or not self._session_id:
            return
        self._started = True
        await self._respond(START_TOKEN)

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        user_text = (getattr(new_message, "text_content", None) or "").strip()
        if not user_text or not self._session_id:
            return
        await self._respond(user_text)

    async def _respond(self, transcript: str) -> None:
        if not self._session_id:
            await self.session.say(
                "Please register your phone number on the website, then call again."
            )
            return

        payload = {
            "session_id": self._session_id,
            "transcript": transcript,
            "conversation_history": self._history,
            "context": self._context,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{NEXTJS_URL}/api/respond",
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            logger.exception("Backend call failed: %s", exc)
            await self.session.say(
                "Sorry, I'm having trouble reaching the server. Please try again."
            )
            return

        response = (data.get("response") or "").strip()
        if not response:
            return

        if transcript != START_TOKEN:
            self._history.append({"role": "user", "text": transcript})

        self._history.append({"role": "assistant", "text": response})

        if data.get("context"):
            self._context = data["context"]

        await self.session.say(response)

    async def handle_turn_complete(self, payload: dict) -> None:
        if payload.get("type") != "turn_complete":
            return

        transcript = (payload.get("transcript") or "").strip()
        response = (payload.get("response") or "").strip()
        context = payload.get("context") or {}

        if not response:
            return

        if transcript == IMAGE_UPLOAD_TOKEN:
            self._history.append({"role": "user", "text": "Sent photos in the app"})
        elif transcript and transcript != START_TOKEN:
            self._history.append({"role": "user", "text": transcript})

        self._history.append({"role": "assistant", "text": response})
        self._context = context
        await self.session.say(response)


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


async def create_session_from_call(caller_phone: str, room_name: str) -> str | None:
    if not INTERNAL_API_SECRET:
        logger.error("INTERNAL_API_SECRET is not set")
        return None

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{NEXTJS_URL}/api/internal/sessions/from-call",
            json={"caller_phone": caller_phone, "livekit_room": room_name},
            headers={"Authorization": f"Bearer {INTERNAL_API_SECRET}"},
        )

    if res.status_code == 404:
        logger.warning("Phone not registered: %s", caller_phone)
        return None

    res.raise_for_status()
    data = res.json()
    return data.get("session_id")


async def complete_session(session_id: str) -> None:
    if not INTERNAL_API_SECRET:
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.patch(
            f"{NEXTJS_URL}/api/internal/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {INTERNAL_API_SECRET}"},
        )


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}

    participant = await ctx.wait_for_participant()
    session_id: str | None = None

    stt_model = "deepgram/nova-3"
    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        stt_model = "deepgram/nova-2-phonecall"
        caller_phone = participant.attributes.get("sip.phoneNumber", "")
        logger.info("SIP caller joined: %s", caller_phone)
        session_id = await create_session_from_call(caller_phone, ctx.room.name)

        @ctx.room.on("participant_disconnected")
        def _on_disconnect(disconnected: rtc.RemoteParticipant) -> None:
            if (
                session_id
                and disconnected.sid == participant.sid
            ):
                import asyncio

                asyncio.create_task(complete_session(session_id))

    bridge = WhatNowBridge(session_id=session_id)

    session = AgentSession(
        stt=inference.STT(model=stt_model, language="en"),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    @ctx.room.on("data_received")
    def _on_data_received(data: rtc.DataPacket, *_args) -> None:
        try:
            payload = json.loads(data.data.decode("utf-8"))
        except Exception:
            logger.warning("Ignoring non-JSON room data packet")
            return
        asyncio.create_task(bridge.handle_turn_complete(payload))

    await session.start(
        agent=bridge,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
