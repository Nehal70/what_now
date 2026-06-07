# Architecture

Updated: 2026-06-06

## Overview

Next.js handles UI and optional BFF routes. FastAPI owns AI orchestration (LLM calls, RAG, streaming).

```
Browser → Next.js (apps/web) → FastAPI (apps/api) → LLM / data stores
```

## Planned repo layout

```
what_now/
├── apps/
│   ├── web/          # Next.js
│   └── api/          # FastAPI
├── packages/
│   └── shared/       # OpenAPI-generated types (optional early on)
├── infra/
│   └── docker-compose.yml
└── .context/         # This folder
```

## Integration

| Concern | Approach |
|---------|----------|
| API contract | OpenAPI from FastAPI → generated TS types |
| Auth | Next.js BFF proxies to FastAPI; no LLM keys in `NEXT_PUBLIC_*` |
| Streaming | FastAPI SSE/WebSocket; Next.js may proxy or client connects with short-lived token |
| Local dev | `pnpm dev` (web) + `uvicorn --reload` (api), or docker-compose |

## Deployment (target)

- **Web:** Vercel
- **API:** Fly.io / Railway / Render (long-running, streaming-friendly)

## Related context

- [Project](./project.md)
- [Decisions](./decisions/)
