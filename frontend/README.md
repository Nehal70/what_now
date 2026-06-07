# What Now — Frontend

Next.js 16 app: Supabase auth, phone sessions, API shim to Person 2's backend, image upload, location capture, and judge dashboard.

## Setup

```bash
npm install
```

Create `frontend/.env.local` with at least:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_SITE_URL=http://localhost:3000
SUPABASE_SERVICE_ROLE_KEY=
BACKEND_ENDPOINT=http://localhost:8000
INTERNAL_API_SECRET=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
LIVEKIT_PHONE_NUMBER=
NEXT_PUBLIC_PHONE_NUMBER=
AGENT_NAME=what-now-agent
NEXTJS_URL=http://localhost:3000
```

```bash
npm run dev
```

Apply Supabase migrations in `supabase/migrations/` via the Supabase SQL editor or CLI.

## Key routes

| Route | Purpose |
|-------|---------|
| `/` | Logged-in session dashboard or marketing home |
| `/dashboard` | Judge mission control (SSE) |
| `/session/[id]` | Live transcript + image upload |
| `/api/respond` | Shim → `BACKEND_ENDPOINT/chat/stream` |
| `/api/sessions/{id}/images` | Stage photo uploads |
| `/api/sessions/{id}/images/send` | Send photos to backend (`__IMAGE_UPLOAD__`) |

## Phone agent

See [`agent/README.md`](agent/README.md).
