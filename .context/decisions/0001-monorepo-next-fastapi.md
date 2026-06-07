# 0001. Monorepo with Next.js and FastAPI

Date: 2026-06-06  
Status: accepted

## Context

The product needs a modern React UI and a Python AI backend. Both evolve together during early development.

## Decision

Use a single monorepo with `apps/web` (Next.js) and `apps/api` (FastAPI). Share API contracts via OpenAPI-generated TypeScript types when needed.

## Consequences

**Positive**

- Atomic changes across UI and AI logic
- One PR workflow and simpler local dev
- Clear separation: UI in web, AI orchestration in api

**Negative**

- Separate deploy pipelines per app
- Need discipline to keep FastAPI services from growing into a god-module

## Alternatives considered

- **Two repositories** — rejected for early stage; adds coordination overhead
- **Next.js API routes only** — rejected; Python ecosystem is stronger for AI workloads
