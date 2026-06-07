# What Now — Frontend (Vapi)

Next.js 16 app with **Vapi** for voice (STT, TTS, phone, browser calls). Supabase auth, API shim to the FastAPI backend, image upload, location capture, and judge dashboard.

## Setup

```bash
npm install
```

Create `frontend_vapi/.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_SITE_URL=http://localhost:3000
SUPABASE_SERVICE_ROLE_KEY=
BACKEND_ENDPOINT=http://localhost:8000
INTERNAL_API_SECRET=

# Vapi
VAPI_API_KEY=
NEXT_PUBLIC_VAPI_API_KEY=
NEXT_PUBLIC_VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER=
NEXT_PUBLIC_PHONE_NUMBER=
```

```bash
npm run dev
```

## Vapi assistant

In [Vapi dashboard](https://dashboard.vapi.ai) → Assistants → create **What Now**:

- **First message:** `I'm here. Are you hurt?`
- **Custom LLM URL:** `https://your-ngrok.ngrok-free.app/vapi/chat` (backend)  
  For browser demo with dashboard: `https://your-nextjs-url/api/vapi/chat`
- **Voice:** ElevenLabs Rachel (`21m00Tcm4TlvDq8ikWAM`) or Vapi Shimmer
- **Transcriber:** Deepgram Nova 2

Assign your Vapi phone number to the assistant for stage phone demos.

Set `NEXTJS_URL` and `INTERNAL_API_SECRET` on the backend so phone calls push dashboard events.

## Key routes

| Route | Purpose |
|-------|---------|
| `/call` | Browser voice call via Vapi SDK |
| `/dashboard` | Judge mission control (SSE) |
| `/session/[id]` | Live transcript + image upload |
| `/api/vapi/chat` | Custom LLM proxy → backend + dashboard events |
| `/api/respond` | Fallback text shim → backend stream |
| `/api/events` | SSE event bus for dashboard |

## Test checklist

- [ ] `npm run dev` starts without errors
- [ ] `/call` → Call Now connects via Vapi
- [ ] Dashboard updates on `/dashboard` during call
- [ ] Orb states: idle / listening / speaking
- [ ] Phone: dial Vapi number → agent picks up
