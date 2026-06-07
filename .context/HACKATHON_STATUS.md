# What Now? — Hackathon Project Status & Technical Brief

**Updated:** 2026-06-06  
**Audience:** Hackathon teammates (Person 1, Person 2, and anyone joining mid-build)  
**Repo:** `what_now`

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Product vision & demo concept](#2-product-vision--demo-concept)
3. [Team ownership split](#3-team-ownership-split)
4. [Sponsor integrations](#4-sponsor-integrations)
5. [Tech stack (actual vs planned)](#5-tech-stack-actual-vs-planned)
6. [Repository layout](#6-repository-layout)
7. [What is implemented today](#7-what-is-implemented-today)
8. [Pages & user flows (main app)](#8-pages--user-flows-main-app)
9. [API routes & endpoints](#9-api-routes--endpoints)
10. [Authentication system (Supabase)](#10-authentication-system-supabase)
11. [Design system & UI](#11-design-system--ui)
12. [Moss Hacker Starter (LiveKit + Moss reference)](#12-moss-hacker-starter-livekit--moss-reference)
13. [Person 1 ↔ Person 2 integration contract](#13-person-1--person-2-integration-contract)
14. [Planned but not yet built](#14-planned-but-not-yet-built)
15. [Environment variables](#15-environment-variables)
16. [Scripts & local development](#16-scripts--local-development)
17. [Architecture diagrams](#17-architecture-diagrams)
18. [Architecture decisions on record](#18-architecture-decisions-on-record)
19. [Demo stage setup (target)](#19-demo-stage-setup-target)
20. [Known gaps & next steps](#20-known-gaps--next-steps)

---

## 1. Executive summary

**What Now?** is a hackathon project that helps people navigate the aftermath of an emergency (e.g., after calling 911) via a **real phone call** to an AI voice agent. While the caller holds a physical phone, a **live mission-control dashboard** on a projector shows judges what the AI is doing in real time — transcript, tool calls, sponsor activity, reasoning trace, and Moss retrieval latency.

The repo currently contains **two parallel tracks**:

| Track | Location | Status |
|-------|----------|--------|
| **Main hackathon app** | Repo root (`app/`, `lib/`) | Landing page, Supabase auth, plan selection, logged-in dashboard shell |
| **Moss + LiveKit reference starter** | `moss-hacker-starter/` | Full browser-based voice agent with Moss RAG + memory (adaptable for hackathon) |
| **Planning / specs** | `.context/` | Person 1 voice+dashboard spec, architecture ADRs, design variants |

The **core demo path** (SIP phone → LiveKit agent → Person 2 backend → SSE dashboard) is **specified in detail** but **not fully implemented** in the main app yet. The moss-hacker-starter provides a working LiveKit + Moss voice stack that Person 2 can learn from or fork.

---

## 2. Product vision & demo concept

### The hook

> After 911 and the people you love — pick up any phone for calm AI guidance.

### Voice interaction model (critical constraint)

- **All voice happens over a real phone call** via LiveKit SIP.
- **No browser microphone.** Do not use Web Speech API (`SpeechRecognition`, `SpeechSynthesisUtterance`).
- The `/call` page (planned) is a **visual status screen** (orb + call state) for the person on stage — they talk on a physical phone, not into the laptop.

### Conversation phases

The AI walks callers through four beats in order:

```
Safety → Scene → Insurance → Legal
```

### Two screens for the demo

| Screen | Route (planned) | Audience | Purpose |
|--------|-----------------|----------|---------|
| **Call UI** | `/call` | Person on stage (laptop facing them) | Voice orb reflecting call state (idle / listening / thinking / speaking) via SSE |
| **Dashboard** | `/dashboard` | Judges (projector) | Live transcript, tool pills, sponsor logos, Qwen reasoning, Moss latency |

### Landing page (implemented)

The public homepage (`/`) shows:

- Dual headline: **What Now?** / **Now What?**
- Click-to-call phone number (`tel:` link)
- Voice orb (static CSS, idle state)
- How-it-works steps (Dial → Speak → Listen)
- Phase pills preview
- Static dashboard mockup in a bezel frame

---

## 3. Team ownership split

From `.context/PERSON1_README.md`:

### Person 1 owns

- LiveKit voice pipeline (SIP phone number only — no browser mic)
- Live dashboard (projector / mission control)
- API shim bridging voice to Person 2's backend
- Everything judges see and hear on stage

### Person 1 is NOT building

- Qwen logic (Person 2)
- Knowledge base / Unsiloed (Person 2)
- Moss retrieval orchestration (Person 2)
- Tool definitions (Person 2)

### Person 2 owns

- Qwen LLM orchestration (via TrueFoundry gateway)
- Tool implementations: `safety_check`, `scene_guide`, `moss_retrieval`, `insurance_tool`, `legal_tool`
- Knowledge base (Unsiloed) and Moss RAG integration
- Backend response shape consumed by Person 1's shim

---

## 4. Sponsor integrations

| Sponsor | Role in product | Where used |
|---------|-----------------|------------|
| **LiveKit** | SIP telephony, STT, TTS, real-time room management, agent dispatch | Voice pipeline; moss-hacker-starter reference |
| **TrueFoundry** | Gateway wrapping Person 2's Qwen endpoint — observable, governed, logged | Person 2 backend (planned) |
| **Qwen** | LLM reasoning + tool selection | Person 2 backend; dashboard reasoning log |
| **Moss** | Semantic retrieval (RAG) + agentic memory | Person 2 tools; moss-hacker-starter reference |
| **Unsiloed** | Knowledge base for incident/legal/insurance content | Person 2 backend |

### Sponsor → dashboard mapping (planned)

When a tool fires on `/dashboard`:

| Tool | Sponsor(s) light up |
|------|---------------------|
| `moss_retrieval` | Moss + Unsiloed |
| `safety_check`, `scene_guide`, `insurance_tool`, `legal_tool` | Qwen |
| All calls | TrueFoundry + LiveKit (always lit) |

Tool pill colors (planned):

| Tool | Color |
|------|-------|
| `safety_check` | Red |
| `scene_guide` | Blue |
| `moss_retrieval` | Amber |
| `insurance_tool` | Purple |
| `legal_tool` | Green |

---

## 5. Tech stack (actual vs planned)

### Main app (`what_now` root) — **implemented**

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js (App Router) | 16.2.7 |
| UI | React | 19.2.4 |
| Styling | Tailwind CSS v4 (`@tailwindcss/postcss`) | ^4 |
| Language | TypeScript | ^5 |
| Auth | Supabase Auth (magic link / OTP) | `@supabase/ssr` ^0.10.3, `@supabase/supabase-js` ^2.107.0 |
| Fonts | Google Fonts: Libre Baskerville, Instrument Sans, IBM Plex Mono | via `next/font` |
| Lint | ESLint + eslint-config-next | ^9 / 16.2.7 |

### Main app — **planned (Person 1 spec)**

| Layer | Technology |
|-------|------------|
| Voice | LiveKit SIP trunk (real phone number) |
| Voice agent | LiveKit Agents (Python worker in `agent/`) |
| STT | LiveKit transcription (Deepgram plugin) |
| TTS | LiveKit Agents TTS (ElevenLabs or OpenAI plugin) |
| Dashboard realtime | Server-Sent Events (SSE); fallback to Pusher if multi-process |
| Backend shim | `POST /api/respond` |

### Architecture decision (accepted, partially superseded)

ADR `0001-monorepo-next-fastapi.md` chose a monorepo with `apps/web` + `apps/api` (FastAPI). The repo **currently uses a flat Next.js root** instead of `apps/web`, and **FastAPI is not present yet**. Person 2 may still build FastAPI separately or expose an external endpoint.

### Moss Hacker Starter — **implemented reference**

| Layer | Technology |
|-------|------------|
| Voice agent | Python LiveKit Agents (`AgentServer`, `@server.rtc_session`) |
| Package manager (agent) | uv |
| Package manager (frontend) | pnpm 10+ |
| Node | >= 22 |
| STT / LLM / TTS | LiveKit Inference (no separate OpenAI/Deepgram/Cartesia keys) |
| RAG + memory | Moss SDK (`moss>=1.4`) |
| Frontend | Next.js 15.5.18 + LiveKit Components React |
| VAD / turn detection | Silero VAD + Multilingual turn detector |
| Noise cancellation | ai-coustics plugin |

---

## 6. Repository layout

```
what_now/
├── app/                          # Main Next.js App Router
│   ├── page.tsx                  # Home: marketing OR logged-in dashboard
│   ├── layout.tsx                # Root layout, fonts, metadata
│   ├── globals.css               # Tailwind v4 + CSS variables
│   ├── homepage.css              # Landing + dashboard styles
│   ├── home-marketing.tsx        # Public landing page component
│   ├── home-dashboard.tsx        # Logged-in dashboard shell (placeholder)
│   ├── login/                    # Magic-link sign-in
│   ├── choose-plan/              # Post-auth plan selection
│   └── auth/                     # Auth callback routes
├── lib/
│   ├── plan.ts                   # User plan types + routing helpers
│   ├── auth-errors.ts            # Rate-limit + error parsing
│   └── supabase/                 # Supabase client factories + session proxy
├── scripts/
│   └── configure-supabase-auth.mjs  # Patches Supabase Auth URL settings via Management API
├── proxy.ts                      # Next.js middleware: refreshes Supabase session
├── design/
│   └── homepage-variants.html    # 4 homepage design explorations (static HTML)
├── moss-hacker-starter/          # LiveKit + Moss reference implementation
│   ├── agent-py/                 # Python voice agent
│   ├── frontend/                 # Browser voice UI (separate Next.js app)
│   └── package.json              # pnpm orchestrator scripts
├── .context/                     # Project knowledge (this file lives here)
│   ├── PERSON1_README.md         # Person 1 build spec (5-hour plan)
│   ├── architecture.md
│   ├── project.md
│   └── decisions/
├── public/                       # Default Next.js static assets
├── package.json
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs
├── eslint.config.mjs
└── .cursor/mcp.json              # Moss MCP server config (placeholder keys)
```

### Planned layout (Person 1 spec — not yet scaffolded)

```
what_now/
├── agent/agent.py                # LiveKit SIP agent
├── components/                   # VoiceOrb, ToolIndicator, LiveTranscript, etc.
├── lib/events.ts                 # SSE event bus
├── lib/types.ts                  # Shared types
└── app/
    ├── call/page.tsx
    ├── dashboard/page.tsx
    └── api/
        ├── respond/route.ts
        └── events/route.ts
```

---

## 7. What is implemented today

### 7.1 Main Next.js app

| Feature | Status | Notes |
|---------|--------|-------|
| Landing / marketing homepage | ✅ Done | Phone CTA, orb, how-it-works, phases, dashboard preview |
| Supabase magic-link auth | ✅ Done | Email OTP, callback handling, session refresh |
| Plan selection (Free tier) | ✅ Done | Stored in `user_metadata.plan` |
| Logged-in dashboard shell | ✅ Done | Placeholder — "Nothing here yet" |
| Session middleware | ✅ Done | `proxy.ts` refreshes Supabase cookies on every request |
| Supabase auth URL config script | ✅ Done | `npm run configure:supabase` |
| `/call` voice status page | ❌ Not built | Specified in PERSON1_README |
| `/dashboard` live mission control | ❌ Not built | Specified in PERSON1_README |
| SSE event bus (`/api/events`) | ❌ Not built | Specified in PERSON1_README |
| Backend shim (`/api/respond`) | ❌ Not built | Specified in PERSON1_README |
| LiveKit SIP agent (`agent/agent.py`) | ❌ Not built | Specified in PERSON1_README |
| Dashboard components | ❌ Not built | VoiceOrb, ToolIndicator, LiveTranscript, SponsorPanel, ReasoningLog, LatencyBadge |

### 7.2 Authentication & user plans

| Feature | Status |
|---------|--------|
| Magic link sign-in | ✅ |
| PKCE code exchange (`/auth/callback`) | ✅ |
| OTP token verify (`/auth/confirm`) | ✅ |
| Sign out (`POST /auth/signout`) | ✅ |
| Post-auth redirect to `/choose-plan` if no plan | ✅ |
| Free plan selection persists to user metadata | ✅ |
| Rate-limit friendly error messages | ✅ |

### 7.3 Design artifacts

| Artifact | Status |
|----------|--------|
| `design/homepage-variants.html` | ✅ 4 visual variants (Warm Authority, Dual Question, Mission Control, Soft Emergency) |
| Implemented homepage aesthetic | ✅ Variant chosen: dark bg, ember `#ff6b4a` + ice `#9ed4f5`, Baskerville headlines |

### 7.4 Moss Hacker Starter (reference stack)

| Feature | Status |
|---------|--------|
| Python LiveKit voice agent with 3 Moss tools | ✅ |
| Moss index builder (`create_index.py`) | ✅ |
| Knowledge corpus (`knowledge.json`, ~13 Q&A entries) | ✅ |
| Browser frontend with LiveKit session UI | ✅ |
| Token minting + agent dispatch | ✅ |
| Per-user Moss memory via cookie + dispatch metadata | ✅ |
| Live Knowledge Matches panel | ✅ |
| Tests (pytest) + lint (ruff) | ✅ |
| Dockerfile for LiveKit Cloud deploy | ✅ |

### 7.5 Project context docs

| Document | Purpose |
|----------|---------|
| `.context/PERSON1_README.md` | Full Person 1 build plan (5 hours, hour-by-hour) |
| `.context/architecture.md` | Planned Next.js ↔ FastAPI integration |
| `.context/decisions/0001-monorepo-next-fastapi.md` | ADR for monorepo split |
| `.context/project.md` | Stub project goals (needs filling in) |

---

## 8. Pages & user flows (main app)

### Routes

| Route | Auth required | Component | Description |
|-------|---------------|-----------|-------------|
| `/` | No (marketing) / Yes (dashboard) | `HomeMarketing` or `HomeDashboard` | Dual-mode home page |
| `/login` | No | `login/page.tsx` | Magic link email form |
| `/choose-plan` | Yes | `choose-plan/page.tsx` | Select Free plan (only option today) |
| `/call` | — | *Not built* | Voice orb status screen |
| `/dashboard` | — | *Not built* | Judge-facing mission control |

### Public user flow

```
Visitor lands on /
  → sees marketing homepage with phone number + Login link
  → clicks Login → /login
  → enters email → magic link sent
  → clicks link in email → /auth/callback (or /auth/confirm)
  → if no plan: redirect /choose-plan
  → selects Free plan → redirect /
  → sees logged-in dashboard shell
```

### Home page routing logic (`app/page.tsx`)

1. `supabase.auth.getUser()`
2. If no user → render `<HomeMarketing />`
3. If user but no `plan` in metadata → `redirect("/choose-plan")`
4. If user with plan → render `<HomeDashboard email={...} />`

### Marketing homepage sections (`home-marketing.tsx`)

| Section | ID | Content |
|---------|-----|---------|
| Nav | — | Logo, How / Phases / Room anchors, Login link |
| Hero | — | Dual headline, phone number, orb, tagline |
| How it works | `#how` | 3-step grid: Dial, Speak, Listen |
| Phases | `#phases` | Safety → Scene → Insurance → Legal pills |
| Dashboard preview | `#dashboard` | Static mock of `/dashboard` with sample transcript |
| CTA band | — | Phone number repeat |
| Footer | — | "Phone + projector demo" |

### Logged-in dashboard (`home-dashboard.tsx`)

- Shows user email in nav
- Sign out button (`POST /auth/signout`)
- Placeholder message: *"Call flow and live session tools will show up here."*

---

## 9. API routes & endpoints

### Main app (`what_now` root)

#### `GET /auth/callback`

**Purpose:** Exchange Supabase PKCE auth code for session after magic link click.

**Query params:**

| Param | Required | Description |
|-------|----------|-------------|
| `code` | Yes | Supabase auth code |

**Behavior:**

1. `supabase.auth.exchangeCodeForSession(code)`
2. Read user metadata → `getPostAuthPath()` → `/` or `/choose-plan`
3. Redirect (handles `x-forwarded-host` in production)

**Error:** Redirect to `/login?error=Invalid+or+expired+link`

---

#### `GET /auth/confirm`

**Purpose:** Verify email OTP via token hash (alternative auth flow).

**Query params:**

| Param | Required | Description |
|-------|----------|-------------|
| `token_hash` | Yes | OTP token hash |
| `type` | Yes | Email OTP type |

**Behavior:** Same post-auth redirect logic as callback.

---

#### `POST /auth/signout`

**Purpose:** Sign out authenticated user.

**Behavior:**

1. `supabase.auth.signOut()`
2. `revalidatePath("/", "layout")`
3. Redirect to `/` (302)

---

#### Server action: `sendMagicLink` (`app/login/actions.ts`)

**Trigger:** Form POST from `/login`

**Input:** `email` (FormData)

**Behavior:**

1. Validate email contains `@`
2. `supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: `${origin}/auth/callback` } })`
3. Redirect to `/login?sent=1` or error

---

#### Server action: `selectFreePlan` (`app/choose-plan/actions.ts`)

**Trigger:** Form POST from `/choose-plan`

**Behavior:**

1. Require authenticated user
2. `supabase.auth.updateUser({ data: { plan: "free" } })`
3. Redirect to `/`

---

### Planned endpoints (Person 1 spec — **not implemented**)

#### `POST /api/respond`

**Purpose:** Shim between LiveKit agent and Person 2 backend. May also emit SSE events.

**Request body:**

```json
{
  "transcript": "I slipped on a wet floor",
  "conversation_history": [
    { "role": "user", "text": "..." },
    { "role": "assistant", "text": "..." }
  ]
}
```

**Expected response:**

```json
{
  "response": "Do not sign anything they hand you.",
  "tool_called": "scene_guide",
  "reasoning": "User is at scene, manager approaching — scene guidance needed",
  "latency_ms": 340
}
```

**Mock mode:** When `MOCK_MODE=true`, return hardcoded grocery-store slip scenario cycling through tools.

---

#### `GET /api/events` (SSE)

**Purpose:** Stream real-time events to `/call` and `/dashboard`.

**Event shape:**

```json
{
  "type": "transcript | tool | reasoning | latency | call_state",
  "data": {},
  "timestamp": 1717687381000
}
```

**Event types (planned):**

| Type | Used by | Payload |
|------|---------|---------|
| `transcript` | Dashboard, Call UI | `{ role, text, tool_called? }` |
| `tool` | Dashboard | `{ tool_called }` |
| `reasoning` | Dashboard | `{ reasoning }` |
| `latency` | Dashboard | `{ latency_ms }` |
| `call_state` | Call UI | `{ state: "idle" \| "listening" \| "thinking" \| "speaking" }` |

---

### Moss Hacker Starter endpoints

#### `POST /api/token` (`moss-hacker-starter/frontend/`)

**Purpose:** Mint LiveKit room token + dispatch agent with per-user metadata.

**Environment required:** `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `AGENT_NAME`

**Security:** Throws in production unless auth layer added (dev-only by design).

**Request body (optional):**

```json
{
  "room_config": { /* LiveKit RoomConfiguration */ }
}
```

**Response:**

```json
{
  "serverUrl": "wss://….livekit.cloud",
  "roomName": "voice_assistant_room_XXXX",
  "participantName": "user",
  "participantToken": "<JWT>"
}
```

**Side effects:**

- Sets httpOnly cookie `lk_moss_user` (UUID, 1-year max-age) on first visit
- Stamps agent dispatch metadata: `{ "user_id": "<uuid>" }`

---

## 10. Authentication system (Supabase)

### Configuration

| Setting | Value / source |
|---------|----------------|
| Supabase project ref | `jmyqbaeintkjpavtdmur` (from configure script) |
| Public URL env | `NEXT_PUBLIC_SUPABASE_URL` |
| Publishable key env | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` |
| Site URL env | `NEXT_PUBLIC_SITE_URL` (default `http://localhost:3000`) |
| Management token | `SUPABASE_ACCESS_TOKEN` (for configure script only) |

### Client factories

| File | Usage |
|------|-------|
| `lib/supabase/server.ts` | Server Components, Server Actions, Route Handlers |
| `lib/supabase/client.ts` | Browser client (available, not heavily used yet) |
| `lib/supabase/proxy.ts` | Session refresh in middleware |

### Middleware (`proxy.ts`)

- Matcher: all routes except static assets, `_next`, favicon, images
- Calls `updateSession()` → `supabase.auth.getClaims()` to refresh session cookies

### User plan model (`lib/plan.ts`)

```typescript
type UserPlan = "free"
FREE_PLAN = "free"

getPlanFromMetadata(metadata) → "free" | null
getPostAuthPath(metadata) → "/" | "/choose-plan"
```

Plan is stored in Supabase `user.user_metadata.plan`.

### Auth error handling (`lib/auth-errors.ts`)

- Detects Supabase rate-limit messages → friendly "wait N seconds" UI
- Generic errors shown in coral `#ff6b4a` banner

---

## 11. Design system & UI

### Typography (implemented)

| Role | Font | CSS variable |
|------|------|--------------|
| Display / headlines | Libre Baskerville (400, 700, italic) | `--font-baskerville` |
| Body / UI | Instrument Sans (400, 500, 600) | `--font-instrument-sans` |
| Mono / phone / dashboard | IBM Plex Mono (400, 500) | `--font-ibm-plex-mono` |

### Color palette (implemented homepage)

| Token | Hex | Usage |
|-------|-----|-------|
| Ember | `#ff6b4a` | Primary accent, phone number, "What Now?" headline |
| Ice | `#9ed4f5` | Secondary accent, "Now What?" headline, login link |
| Background | `#000000` | Page background |
| Foreground | `#ffffff` | Text |
| Muted text | `rgba(255,255,255,0.46)` | Body copy |
| Live indicator | `#5fd4a0` | Dashboard preview "● LIVE" |
| User transcript | `#6eb5ff` | Dashboard preview caller lines |

### CSS architecture

- `app/globals.css` — Tailwind v4 import + `:root` variables
- `app/homepage.css` — All landing/dashboard styles (`.home` scoped)

### Design explorations (`design/homepage-variants.html`)

Four static mockups for stakeholder review:

| Variant | Aesthetic |
|---------|-----------|
| A — Warm Authority | Instrument Sans, ember gradients |
| B — Dual Question | Large dual headline focus |
| C — Mission Control | Terminal/dashboard forward |
| D — Soft Emergency | Newsreader + softer tones |

The **implemented homepage** follows the ember/ice dual-question direction from these explorations.

---

## 12. Moss Hacker Starter (LiveKit + Moss reference)

Located at `moss-hacker-starter/`. This is a **working reference** for LiveKit Agents + Moss, forked from official LiveKit starter templates. It uses **browser mic** (not SIP) — different from the hackathon demo path, but valuable for Person 2's Moss integration work.

### Agent tools (`agent-py/src/agent.py`)

| Tool | Moss index | Purpose |
|------|------------|---------|
| `search_knowledge` | `knowledge` | RAG over LiveKit docs corpus (`top_k=3`) |
| `remember_fact` | `memory` | Persist user fact with `metadata.user_id` |
| `recall_facts` | `memory` | Query user facts with `$eq` filter on `user_id` |

### LiveKit Inference models (agent)

| Component | Model |
|-----------|-------|
| LLM | `openai/gpt-5.2-chat-latest` |
| STT | `deepgram/nova-3` (multi-language) |
| TTS | `cartesia/sonic-3` (voice UUID `9626c31c-bec5-4cca-baa8-f8ba9e84c8bc`) |
| VAD | Silero (prewarmed) |
| Turn detection | MultilingualModel |
| Noise cancellation | ai-coustics QUAIL_VF_S |

### Agent registration

- Dispatch name: **`agent-py`** (must match frontend `AGENT_NAME`)
- Entry: `@server.rtc_session(agent_name="agent-py")`

### Real-time UI data channel

When agent runs Moss query, it publishes LiveKit data packet:

```json
{
  "type": "moss_context",
  "data": {
    "query": "...",
    "matches": [{ "text": "...", "score": 0.92, "metadata": {} }],
    "time_taken_ms": 134,
    "timestamp": 1717687381.5
  }
}
```

Frontend hook `useMossContextEvents.ts` parses this → `MossResultsPanel` displays **Knowledge Matches** with relevance scores and latency.

### Moss indexes (`create_index.py`)

| Index | Env var | Contents |
|-------|---------|----------|
| `knowledge` | `MOSS_INDEX_NAME` | ~13 docs from `knowledge.json` |
| `memory` | `MOSS_MEMORY_INDEX_NAME` | Seed placeholder doc (`user_id: __seed__`) |

Model: `MOSS_MODEL_ID=moss-minilm` (default)

### Moss Hacker Starter scripts

| Command | Description |
|---------|-------------|
| `pnpm setup` | Install frontend + sync agent + copy `.env.local` |
| `pnpm dev` | Run agent + frontend concurrently |
| `pnpm moss:index` | Build Moss indexes |
| `pnpm agent:py:console` | Terminal smoke test (no browser) |
| `pnpm test` | pytest |
| `pnpm lint` | ruff + next lint |

---

## 13. Person 1 ↔ Person 2 integration contract

Share this with Person 2 immediately.

### Endpoint

```
POST /api/respond
```

(Person 1's Next.js shim — agent may call this or `BACKEND_ENDPOINT` directly; pick one path and stay consistent.)

### Request

```json
{
  "transcript": "I slipped on a wet floor",
  "conversation_history": [
    { "role": "user", "text": "..." },
    { "role": "assistant", "text": "..." }
  ]
}
```

### Response (required fields)

```json
{
  "response": "Do not sign anything they hand you.",
  "tool_called": "scene_guide",
  "reasoning": "User is at scene, manager approaching — scene guidance needed",
  "latency_ms": 340
}
```

### Tool names (must match exactly)

- `safety_check`
- `scene_guide`
- `moss_retrieval`
- `insurance_tool`
- `legal_tool`

### Optional fields

| Field | Dashboard use |
|-------|---------------|
| `reasoning` | Terminal-style reasoning log |
| `latency_ms` | Moss latency badge (green <500ms, amber <1000ms, red ≥1000ms) |

If Person 2 hasn't added optional fields yet, Person 1's UI defaults to null.

### Mock backend

Person 1 can rehearse with `MOCK_MODE=true` — cycles through grocery store slip scenario without Person 2's backend.

---

## 14. Planned but not yet built

Priority order from Person 1's 5-hour plan:

### Hour 1 — SIP phone call

- [ ] LiveKit Cloud SIP inbound trunk
- [ ] Dispatch rule → room `what-now-room`
- [ ] `agent/agent.py` — SIP participant handling, Deepgram STT, TTS, POST to backend
- [ ] Landing page shows real `LIVEKIT_PHONE_NUMBER`

### Hour 2 — Call UI + API shim

- [ ] `POST /api/respond/route.ts`
- [ ] `/call` page with VoiceOrb driven by SSE (no browser mic)

### Hour 3 — Dashboard + SSE bus

- [ ] `lib/events.ts` — in-memory EventEmitter (Pusher fallback if `PUSHER_KEY` set)
- [ ] `GET /api/events/route.ts` — SSE stream
- [ ] `/dashboard` — 2×2 grid: LiveTranscript, ToolIndicator, SponsorPanel, ReasoningLog

### Hour 4 — Wire together

- [ ] `/api/respond` emits SSE events on each turn
- [ ] LatencyBadge component
- [ ] End-to-end: phone call → dashboard updates

### Hour 5 — Polish

- [ ] TTS pacing (~300ms pause before speaking)
- [ ] Dashboard LIVE badge + call timer
- [ ] Mock scenario for rehearsal
- [ ] SSE auto-reconnect (2s on error)
- [ ] Agent heartbeat (20s) to prevent SIP drop

### Person 2 backend (separate track)

- [ ] FastAPI (or external) Qwen orchestration
- [ ] TrueFoundry gateway integration
- [ ] Unsiloed knowledge base
- [ ] Moss retrieval tool
- [ ] Five tool implementations

### Architecture (from ADR, not started)

- [ ] `apps/web` + `apps/api` monorepo split
- [ ] OpenAPI-generated TS types
- [ ] Docker Compose local dev

---

## 15. Environment variables

### Main app (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase anon/publishable key |
| `NEXT_PUBLIC_SITE_URL` | Yes | Site URL for auth redirects (e.g. `http://localhost:3000`) |
| `SUPABASE_ACCESS_TOKEN` | For configure script | Supabase Management API token |
| `NEXT_PUBLIC_PHONE_DISPLAY` | Optional | Display phone (default `(555) 010-0911`) |
| `NEXT_PUBLIC_PHONE_TEL` | Optional | E.164 tel link (default `+15550100911`) |

### Main app — planned (Person 1)

| Variable | Description |
|----------|-------------|
| `LIVEKIT_API_KEY` | LiveKit Cloud API key |
| `LIVEKIT_API_SECRET` | LiveKit Cloud API secret |
| `LIVEKIT_URL` | LiveKit WebSocket URL |
| `LIVEKIT_SIP_TRUNK_ID` | SIP trunk ID |
| `LIVEKIT_PHONE_NUMBER` | Phone number judges call |
| `BACKEND_ENDPOINT` | Person 2 backend URL |
| `BACKEND_API_KEY` | Person 2 API key |
| `TRUEFOUNDRY_ENDPOINT` | TrueFoundry gateway URL |
| `TRUEFOUNDRY_API_KEY` | TrueFoundry API key |
| `MOCK_MODE` | `true` to use hardcoded scenario |
| `PUSHER_KEY` | Optional — use Pusher instead of in-memory SSE |

### Moss Hacker Starter — agent (`agent-py/.env.local`)

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | LiveKit WebSocket URL |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `MOSS_PROJECT_ID` | Moss portal project ID |
| `MOSS_PROJECT_KEY` | Moss portal project key |
| `MOSS_INDEX_NAME` | Default `knowledge` |
| `MOSS_MEMORY_INDEX_NAME` | Default `memory` |
| `MOSS_MODEL_ID` | Default `moss-minilm` |

### Moss Hacker Starter — frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | LiveKit WebSocket URL |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `AGENT_NAME` | Default `agent-py` |

---

## 16. Scripts & local development

### Main app

```bash
# Install
npm install

# Dev server (http://localhost:3000)
npm run dev

# Production build
npm run build
npm start

# Lint
npm run lint

# Configure Supabase auth URLs (needs SUPABASE_ACCESS_TOKEN)
npm run configure:supabase
```

### Moss Hacker Starter

```bash
cd moss-hacker-starter

# First-time setup
pnpm setup

# Write LiveKit creds (use LiveKit CLI — do not hand-type keys)
lk app env -w agent-py
lk app env -w frontend

# Paste Moss creds into agent-py/.env.local manually

# Build Moss indexes
pnpm moss:index

# Run agent + frontend
pnpm dev
# Frontend: http://localhost:3000 (separate from main app!)
```

### MCP tooling (Cursor)

`.cursor/mcp.json` configures Moss MCP server (`@moss-tools/mcp-server`) — set `MOSS_PROJECT_ID` and `MOSS_PROJECT_KEY` for AI-assisted Moss development.

LiveKit Docs MCP is also available in Cursor for SIP/Agents setup.

---

## 17. Architecture diagrams

### Target hackathon demo architecture (planned)

```
┌─────────────────┐     SIP/PSTN      ┌──────────────────────┐
│  Caller's phone │ ────────────────▶ │  LiveKit Cloud       │
└─────────────────┘                   │  • SIP trunk         │
                                      │  • Room: what-now-room│
                                      └──────────┬───────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
         ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
         │ agent/agent.py   │        │ POST /api/respond│        │ GET /api/events  │
         │ STT → backend    │───────▶│ (Next.js shim)   │───────▶│ (SSE stream)     │
         │ ← TTS response   │        └────────┬─────────┘        └────────┬─────────┘
         └──────────────────┘                 │                           │
                                              ▼                           ▼
                                   ┌──────────────────┐        ┌──────────────────┐
                                   │ Person 2 backend │        │ /call + /dashboard│
                                   │ Qwen + Moss +    │        │ (browser clients) │
                                   │ Unsiloed + tools │        └──────────────────┘
                                   │ via TrueFoundry  │
                                   └──────────────────┘
```

### Current main app architecture (implemented)

```
Browser
  │
  ▼
proxy.ts (session refresh)
  │
  ▼
Next.js App Router
  ├── / (marketing or dashboard)
  ├── /login → sendMagicLink → Supabase OTP
  ├── /auth/callback → session
  ├── /choose-plan → updateUser metadata
  └── /auth/signout
        │
        ▼
   Supabase Auth (hosted)
```

### Moss Hacker Starter architecture (implemented reference)

```
Browser (mic) ──WebRTC──▶ LiveKit Cloud ◀── agent-py (Python)
     │                         │
     │ POST /api/token          │ Moss SDK
     │ (lk_moss_user cookie)    ▼
     │                    Moss indexes
     │                    • knowledge (RAG)
     └── moss_context data ──▶ Knowledge Matches panel
         packets
```

---

## 18. Architecture decisions on record

### ADR 0001: Monorepo with Next.js and FastAPI

- **Date:** 2026-06-06
- **Status:** Accepted (partially implemented — flat Next.js root, no FastAPI yet)
- **Decision:** Single monorepo with `apps/web` + `apps/api`; OpenAPI-generated TS types
- **Rationale:** Atomic UI + AI changes; Python ecosystem for AI workloads
- **Rejected:** Two repos (coordination overhead); Next.js API routes only (weaker AI ecosystem)

---

## 19. Demo stage setup (target)

| Physical setup | Screen | URL |
|----------------|--------|-----|
| Laptop facing presenter | Call status orb | `/call` |
| Projector facing judges | Mission control dashboard | `/dashboard` |
| Card on table | Printed phone number | `LIVEKIT_PHONE_NUMBER` |

**Flow:** Presenter walks to mic → gives hook → picks up phone → dials number live → judges watch dashboard light up in real time.

---

## 20. Known gaps & next steps

### Critical path to demo-ready

1. **LiveKit SIP** — configure trunk + phone number in LiveKit Cloud dashboard
2. **`agent/agent.py`** — adapt from moss-hacker-starter or write fresh for SIP (not browser mic)
3. **`POST /api/respond`** — shim + mock mode for rehearsal
4. **SSE bus** — `lib/events.ts` + `/api/events`
5. **`/dashboard`** — four panels + sponsor mapping
6. **`/call`** — VoiceOrb synced to call state
7. **Person 2 backend** — implement tool contract; route through TrueFoundry

### Nice-to-have before judging

- TTS pacing tuning
- Dashboard LIVE badge + call timer
- SSE auto-reconnect
- Agent SIP keepalive heartbeat
- Replace placeholder phone number with real SIP number on landing page

### Documentation debt

- `.context/project.md` — goals/non-goals still stubbed
- Root `README.md` — still default create-next-app boilerplate

---

## Quick reference: file index

| Path | What it does |
|------|--------------|
| `app/page.tsx` | Auth-gated home routing |
| `app/home-marketing.tsx` | Public landing page |
| `app/home-dashboard.tsx` | Logged-in placeholder dashboard |
| `app/login/page.tsx` | Magic link form |
| `app/login/actions.ts` | `sendMagicLink` server action |
| `app/choose-plan/page.tsx` | Free plan selection UI |
| `app/choose-plan/actions.ts` | `selectFreePlan` server action |
| `app/auth/callback/route.ts` | PKCE session exchange |
| `app/auth/confirm/route.ts` | OTP token verification |
| `app/auth/signout/route.ts` | Sign out handler |
| `lib/plan.ts` | Plan type + routing helpers |
| `lib/auth-errors.ts` | Login error formatting |
| `lib/supabase/server.ts` | Server Supabase client |
| `lib/supabase/client.ts` | Browser Supabase client |
| `lib/supabase/proxy.ts` | Middleware session refresh |
| `proxy.ts` | Next.js middleware entry |
| `scripts/configure-supabase-auth.mjs` | Supabase Management API config |
| `design/homepage-variants.html` | Design explorations |
| `.context/PERSON1_README.md` | Person 1 full build spec |
| `moss-hacker-starter/agent-py/src/agent.py` | Reference LiveKit + Moss agent |
| `moss-hacker-starter/frontend/app/api/token/route.ts` | LiveKit token minting |
| `moss-hacker-starter/frontend/hooks/useMossContextEvents.ts` | Moss data packet parser |
| `moss-hacker-starter/frontend/components/app/moss-results-panel.tsx` | Knowledge Matches UI |

---

*Generated from codebase audit on 2026-06-06. Update this file as features ship.*
