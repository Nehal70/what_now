# Local context

Markdown files in this folder capture project knowledge for humans and AI assistants. Keep entries short, dated, and factual.

## Layout

| Path | Purpose |
|------|---------|
| `project.md` | What we're building, goals, constraints |
| `architecture.md` | Stack, repo layout, integration patterns |
| `decisions/` | Architecture Decision Records (ADRs) |
| `notes/` | Topic notes, research, scratchpad |
| `local/` | **Gitignored** — personal or machine-specific notes |

## Conventions

1. **One topic per file** — split when a file grows past ~200 lines.
2. **Date significant updates** — add `Updated: YYYY-MM-DD` under the title.
3. **Link related files** — e.g. `See decisions/0001-monorepo.md`.
4. **Prefer updates over new duplicates** — edit existing context instead of spawning `project-v2.md`.
5. **Decisions get ADRs** — use `decisions/NNNN-short-slug.md` for choices that are hard to reverse.

## ADR template

Copy `decisions/_template.md` when recording a new decision.

## Private notes

Put anything you do not want in git under `local/`. That directory is gitignored.
