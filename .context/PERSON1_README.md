# What Now? — Person 1: Voice, Phone & Dashboard

## What you own

- The LiveKit voice pipeline (real phone number via SIP only — no browser microphone)  
- The live dashboard (the big screen judges watch during the demo)  
- The API shim that bridges voice to Person 2's backend  
- Everything the judges see and hear

## What you are NOT building

- Qwen logic (Person 2\)  
- Knowledge base / Unsiloed (Person 2\)  
- Moss retrieval (Person 2\)  
- Tool definitions (Person 2\)

---

## Voice interaction model

**All voice happens over a phone call.** The caller dials a real phone number (LiveKit SIP). A LiveKit agent handles STT, calls Person 2's backend, and speaks the response via TTS on the phone line.

**Do not use the Web Speech API** (`SpeechRecognition`, `SpeechSynthesisUtterance`) or browser microphone capture. The `/call` page is a visual status screen (orb + call state) for the person on stage — they talk on a physical phone, not into the laptop.

**LiveKit implementation:** agents must use the **LiveKit Docs MCP server** (`docs_search` → `get_pages`) for all LiveKit setup and code — SIP, Agents, plugins, telephony. Do not guess APIs from memory.

---

## The two screens you are building

### Screen 1 — The Call UI

A minimal status page (`/call`). Shows the voice orb (idle / listening / thinking / speaking) reflecting the **active phone call** via SSE — not browser audio. Clean, emotional, simple. This is what the "injured person" on stage glances at while they hold the phone.

### Screen 2 — The Dashboard (the wow factor)

A separate page (`/dashboard`) shown on the projector behind you. Judges watch this while the call happens. It shows in real time:

- Live transcript (user in blue, AI in white)  
- Which tool just fired (big animated pill)  
- Which sponsor is active right now (sponsor logos lighting up)  
- Qwen's reasoning trace ("thinking: wet floor mentioned → scene\_guide")  
- Moss retrieval latency in ms  
- Conversation phase (Safety → Scene → Insurance → Legal)

---

## Stack

| Layer | Tech |
| :---- | :---- |
| Framework | Next.js 14 App Router |
| Voice | LiveKit SIP trunk — real phone number only |
| Voice agent | LiveKit Agents (Python or JS worker) |
| STT | LiveKit transcription (Deepgram plugin) |
| TTS | LiveKit Agents TTS plugin (ElevenLabs or OpenAI) |
| Dashboard realtime | Server-Sent Events (SSE) or Pusher |
| Styling | Tailwind CSS |
| Language | TypeScript |

---

## Repo structure — tell Cursor to scaffold this exactly

what-now/

├── app/

│   ├── page.tsx                  \# Landing — shows phone number + "Call Now"

│   ├── call/page.tsx             \# Call status UI (Screen 1\) — orb via SSE, no browser mic

│   ├── dashboard/page.tsx        \# Live dashboard (Screen 2\)

│   └── api/

│       ├── respond/route.ts          \# Shim: transcript → Person 2 → response

│       └── events/route.ts           \# SSE stream for dashboard + call UI updates

├── agent/

│   └── agent.py                  \# LiveKit agent — SIP call STT/TTS + backend calls

├── components/

│   ├── VoiceOrb.tsx              \# Animated orb (idle/listening/thinking/speaking)

│   ├── ToolIndicator.tsx         \# Pill showing current tool

│   ├── LiveTranscript.tsx        \# Scrolling conversation

│   ├── SponsorPanel.tsx          \# Sponsor logos lighting up

│   ├── ReasoningLog.tsx          \# Qwen's thinking trace

│   └── LatencyBadge.tsx          \# Moss retrieval time in ms

├── lib/

│   ├── events.ts                 \# SSE emitter (shared event bus)

│   └── types.ts                  \# Shared TypeScript types

└── .env.local

---

## Environment variables

\# LiveKit cloud

LIVEKIT\_API\_KEY=

LIVEKIT\_API\_SECRET=

LIVEKIT\_URL=wss://your-project.livekit.cloud

\# LiveKit SIP (for phone number)

LIVEKIT\_SIP\_TRUNK\_ID=

LIVEKIT\_PHONE\_NUMBER=          \# the actual phone number judges will call

\# Person 2's backend (they give you this)

BACKEND\_ENDPOINT=https://person2-backend/chat

BACKEND\_API\_KEY=

\# TrueFoundry gateway (wraps Person 2's endpoint)

TRUEFOUNDRY\_ENDPOINT=

TRUEFOUNDRY\_API\_KEY=

---

## Build order — your 5 hours

### Hour 1 — Project setup \+ SIP phone call working

**Install:**

npx create-next-app@latest what-now \--typescript \--tailwind \--app

cd what-now

npm install livekit-server-sdk

pip install livekit-agents livekit-plugins-deepgram livekit-plugins-openai

**Tell Cursor:**

"Create a LiveKit room agent in `agent/agent.py` using the `livekit-agents` Python SDK. The agent joins room `what-now-room`, handles SIP participants, transcribes speech via the Deepgram STT plugin, POSTs each transcript to `BACKEND_ENDPOINT` with conversation history, and speaks the response via the OpenAI or ElevenLabs TTS plugin."

"Create a landing page at `/` that displays `LIVEKIT_PHONE_NUMBER` prominently with a 'Call Now' instruction — the user dials this number on a physical phone."

**LiveKit SIP setup steps (do manually in dashboard):**

1. Go to LiveKit Cloud → SIP  
2. Create Inbound Trunk  
3. Get the phone number assigned  
4. Set dispatch rule: any call to this number → joins room `what-now-room`  
5. Test by calling the number — the agent should pick up and respond

**Exit condition:** You call the phone number from a physical phone and the AI picks up and responds.

---

### Hour 2 — Call status UI \+ API shim

**Tell Cursor:**

"Create `/api/respond/route.ts` as the shim Person 2's backend is called through (the agent may call this or `BACKEND_ENDPOINT` directly — pick one path and stay consistent). Return `{ response, tool_called, reasoning, latency_ms }`."

"Create `/call` as a status-only page: VoiceOrb reflects call state (idle/listening/thinking/speaking) driven by SSE from `/api/events` — no browser microphone, no Web Speech API."

**Exit condition:** During a phone call, `/call` orb updates to match call state; backend shim returns mock responses.

---

### Hour 3 — Dashboard skeleton \+ SSE event bus

The dashboard needs a real-time data feed from the backend. Use Server-Sent Events — dead simple, no websocket setup.

**Tell Cursor:**

"Create a shared in-memory event emitter in `lib/events.ts` using Node.js EventEmitter. Create an SSE API route at `/api/events` that streams events to connected clients. Events have shape `{ type: string, data: any, timestamp: number }`."

"Create a dashboard page at `/dashboard` that connects to `/api/events` via `EventSource`, and renders four panels: LiveTranscript, ToolIndicator, SponsorPanel, ReasoningLog. Use Tailwind for layout — dark background, 2x2 grid of panels."

**The four dashboard panels — tell Cursor to build each:**

**Panel 1 — Live Transcript**

"LiveTranscript component: scrolling list of messages, user messages right-aligned in blue, AI messages left-aligned in white/gray. Auto-scrolls to bottom on new message. Shows small tool badge under each AI message if tool\_called is set."

**Panel 2 — Tool Indicator**

"ToolIndicator component: shows a large animated pill for the current active tool. Tools are: safety\_check (red), scene\_guide (blue), moss\_retrieval (amber), insurance\_tool (purple), legal\_tool (green). When a new tool fires, animate in with a scale \+ fade transition. Show the previous tool grayed out above it."

**Panel 3 — Sponsor Panel**

"SponsorPanel component: show 5 sponsor name badges — LiveKit, TrueFoundry, Qwen, Moss, Unsiloed. Each is gray by default. When a tool fires, light up the relevant sponsor(s) in their brand color with a glow effect. Mapping: moss\_retrieval → Moss \+ Unsiloed both light up. safety\_check/scene\_guide/insurance\_tool/legal\_tool → Qwen lights up. All calls → TrueFoundry \+ LiveKit always lit."

**Panel 4 — Reasoning Log**

"ReasoningLog component: terminal-style scrolling log. Monospace font, dark background, green text. Each entry is a timestamped line. Entries come from the SSE stream with type `reasoning`. Example: `[14:23:01] user mentioned wet floor → calling scene_guide`. Show last 20 lines."

**Exit condition:** Open `/dashboard`, trigger mock events, see all 4 panels update live.

---

### Hour 4 — Wire everything together

**Tell Cursor:**

"Modify `/api/respond/route.ts` so that after getting a response from the backend, it emits SSE events to the event bus: one event of type `transcript` with the user message, one of type `transcript` with the AI response, one of type `tool` with the tool\_called value, and one of type `reasoning` with any reasoning field from the backend response. The agent should trigger these events on each phone turn."

**Integration contract — share this with Person 2 immediately:**

Request shape you send them:

{

  "transcript": "I slipped on a wet floor",

  "conversation\_history": \[

    { "role": "user", "text": "..." },

    { "role": "assistant", "text": "..." }

  \]

}

Response shape you expect back:

{

  "response": "Do not sign anything they hand you.",

  "tool\_called": "scene\_guide",

  "reasoning": "User is at scene, manager approaching — scene guidance needed",

  "latency\_ms": 340

}

The `reasoning` field powers your terminal log. The `latency_ms` field shows Moss speed. If Person 2 hasn't added these yet, default to null — your UI handles it.

**Tell Cursor:**

"Add a LatencyBadge component to the dashboard that shows the last Moss retrieval time in ms. Green if under 500ms, amber if under 1000ms, red if over. Pull from SSE events of type `latency`."

**Exit condition:** Make a phone call → transcript appears on dashboard → tool lights up → sponsor glows → reasoning log updates.

---

### Hour 5 — Polish \+ demo prep

**Voice feel (phone TTS via agent):**

"Tell Cursor: tune the LiveKit agent TTS plugin — calm voice, natural pacing, ~300ms pause before the AI starts speaking so it doesn't feel instant/robotic."

**Dashboard visual polish:**

"Tell Cursor: add a pulsing red dot \+ 'LIVE' badge to the dashboard header. Add a call timer showing how long the current phone call has been active. Make the overall layout feel like a mission control screen — dark, clean, high contrast."

**Mock backend for rehearsal:**

"Tell Cursor: create a mock version of `/api/respond` that cycles through a pre-written grocery store slip scenario: safety\_check → scene\_guide → scene\_guide → legal\_tool → insurance\_tool. Each response includes reasoning and latency\_ms fields. Use this for rehearsing the demo without needing Person 2's backend."

**Exit condition:** Demo runs clean 3 times. Phone call works. Dashboard updates perfectly. You know the scenario cold.

---

## The demo setup on stage

Your laptop screen (facing you):    /call page — orb reflecting the live phone call

Projector (facing judges):          /dashboard — full mission control view

Phone on table:                     the actual phone number printed on a card

Walk to the mic, say the hook, pick up the phone, call the number live. Judges watch the dashboard light up in real time.

---

## Mock backend (use while Person 2 builds)

Tell Cursor:

"In `/api/respond/route.ts`, add a `MOCK_MODE=true` env flag. When true, skip the real backend call and return the next item in a hardcoded scenario array. The scenario covers a grocery store slip: first response is safety triage, second is scene guidance, third is incident report advice, fourth is legal rights, fifth is insurance filing. Each item has response, tool\_called, reasoning, and latency\_ms fields."

---

## Common issues — tell Cursor to handle these

**SSE connection drops:** Add auto-reconnect logic in the dashboard and `/call` `EventSource` — on `onerror`, wait 2 seconds and reconnect.

**LiveKit SIP call drops after 30s:** Set keepalive on the agent participant. Tell Cursor to add a heartbeat ping every 20 seconds.

**Dashboard not updating on phone calls:** The SSE bus is in-memory — if the agent and the Next.js server are separate processes, use Redis pub/sub or Pusher instead. Tell Cursor: "Replace the in-memory EventEmitter in `lib/events.ts` with a Pusher client if `PUSHER_KEY` env var is present, otherwise fall back to in-memory."

**Agent and UI out of sync:** Ensure the agent POSTs to `/api/respond` (or emits events directly) on every phone turn so `/call` and `/dashboard` stay in sync.

---

## What to tell Person 2 on day 1

1. Your shim lives at `POST /api/respond`  
2. Exact request/response shape (JSON above)  
3. They MUST include `tool_called` as a string matching exactly: `safety_check`, `scene_guide`, `moss_retrieval`, `insurance_tool`, `legal_tool`  
4. Optional but important for dashboard: `reasoning` (string) and `latency_ms` (number)  
5. If their backend isn't ready, you have mock mode — don't block on them

---

## Sponsor callouts for submission writeup

- **LiveKit:** Entire voice infrastructure — SIP phone number, STT, TTS, real-time room management  
- **TrueFoundry:** All calls to Qwen are routed through TrueFoundry gateway — observable, governed, logged
