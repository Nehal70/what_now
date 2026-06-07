# What Now?

Monorepo for the What Now hackathon demo — AI voice guidance after an emergency.

| Directory | Owner | Description |
|-----------|-------|-------------|
| [`backend/`](backend/) | Person 2 | FastAPI + Qwen agent, tools, knowledge base, `/chat/stream` SSE |
| [`frontend/`](frontend/) | Person 1 | Next.js app, API shim, Supabase auth/sessions, LiveKit phone bridge |

## Quick start

### Backend (Person 2)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
uvicorn main:app --reload --port 8000
```

Set `BACKEND_ENDPOINT=http://localhost:8000` in `frontend/.env.local` for local dev (or your partner's ngrok URL).

### Frontend + phone agent (Person 1)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # or copy your existing .env.local
npm run dev
```

In a second terminal:

```bash
cd frontend/agent
pip install -r requirements.txt
python agent.py dev
```

Open [http://localhost:3000](http://localhost:3000), register your phone at `/settings/phone`, dial the LiveKit number, keep the dashboard open.

### Judge dashboard

[http://localhost:3000/dashboard](http://localhost:3000/dashboard) — mission control during the demo.

## Architecture

```text
Phone (SIP) → frontend/agent (LiveKit) → frontend /api/respond → backend /chat/stream
Browser (/)  → GPS, image upload, session UI
/dashboard   → SSE mission control for judges
```

## Docs

- [`frontend/README.md`](frontend/README.md) — Next.js app details
- [`frontend/agent/README.md`](frontend/agent/README.md) — LiveKit SIP setup
- [`.context/`](.context/) — hackathon specs and integration guides
