# Task Manager — project CLAUDE.md

This file holds only what's specific to *this* repo. Everything about how I
work — git behavior, ponytail, the subagent team, commit format — already
applies from `~/.claude/CLAUDE.md`. Don't duplicate it here; if something
here ever contradicts it, the global file wins and this one is wrong.

Full design reasoning (why each decision was made, not just what it is) lives
in `README.md` and the six architecture sheets it links to. This file is the
fast-reference version for working in the code.

---

## What this is

A personal Kanban tool. One MCP server backs it — when a project gets
mentioned in conversation, I read its board, do the work, and log it back:
cards move, updates get written, a daily digest and productivity score come
out the other end automatically. `README.md` has the full picture; this file
is about the code itself.

## Stack

- **Backend**: FastAPI (`backend/`), Python 3.11+, `uv` for dependencies.
  One process serves both the REST API (for the web app) and the MCP server
  (for Claude) — see `backend/app/main.py`. They share one service layer
  (`backend/app/services/`) so there's exactly one implementation of every
  piece of business logic, not two.
- **Frontend**: React + TypeScript + Vite (`frontend/`), React Query for
  data fetching, plain WebSocket for realtime board updates (replaces what
  Supabase's client SDK would have given for free — see the architecture
  sheet for why that trade was made).
- **Database**: Postgres, hosted on Supabase — but only as managed Postgres.
  No Supabase client SDK, no RLS, no Supabase Auth, no Supabase Realtime.
  FastAPI is the only thing that ever talks to it (SQLAlchemy + asyncpg).
- **Migrations**: Alembic. `backend/alembic/versions/0001_initial_schema.py`
  is the schema source of truth — read it before touching `models.py`, they
  must never drift apart.
- **Scheduling**: no in-process scheduler — GitHub Actions (`.github/workflows/`)
  curls three secret-protected endpoints (`app/routers/internal.py`) on a
  schedule instead. Deliberate: it means the backend can run on Render's
  free tier, which sleeps on idle, since the job doesn't depend on the
  process being continuously alive — the trigger request itself wakes it.
- **Email**: Resend, for the 9:30 AM summary only.
- **Hosting**: frontend on Vercel (static build), backend on Render's free
  tier (`backend/render.yaml`, deployed via Render's Blueprint feature).
  Honest tradeoff of free: an open WebSocket drops and takes 30-60s to
  reconnect if the instance had gone to sleep — no data loss, just a lag.

## Layout

```
backend/
  render.yaml      Render Blueprint — free web service, single process
  app/
    main.py          FastAPI app — mounts REST routers + the MCP server on /mcp
    models.py        SQLAlchemy models — must match the Alembic migration exactly
    auth.py          device tokens (MCP) and web JWT (site) — two separate mechanisms
    mcp_server.py    the 8 MCP tools — thin wrappers over services/
    websocket.py     in-memory broadcast; see its own docstring for the scaling ceiling
    services/        shared logic: board, history, updates, digest, productivity
    routers/         REST endpoints, incl. internal.py — the cron trigger endpoints
    jobs/            digest_job.py, notify_job.py — pure functions, called by internal.py
frontend/src/
  api/client.ts    the only place that talks to the backend
  pages/           Board, Today, Productivity, Overview, Devices, Login
.github/workflows/ three scheduled workflows that curl the /internal endpoints
```

The architecture diagram, ER diagram, and every other design sheet live
directly in `README.md` (as Mermaid) — no separate `docs/` folder.

## Running it locally

```bash
# backend
cd backend
uv venv && uv pip install -e ".[dev]"
cp .env.example .env   # fill in DATABASE_URL at minimum
uv run alembic upgrade head
uv run scripts/set_password.py "your password"   # paste hash into .env
uv run scripts/create_device.py "macbook"          # paste token into your MCP config
uv run uvicorn app.main:app --reload

# frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

## The MCP tool surface

Exact signatures — this is what Claude actually calls, matches the Sheet 01
reference table:

| Tool | Shape | Notes |
|---|---|---|
| `get_board(project)` | check | current columns + cards |
| `search_history(keywords, project?)` | check | cross-project by default |
| `get_digest(project?, range)` | check | omit project for the combined view |
| `create_project(name)` | update | idempotent by slug, + default columns |
| `create_card(title, priority)` | update | into Backlog |
| `move_card(card_id, target_role)` | update | `target_role` is a column *role*, not a name |
| `log_update(card_id, resolved, duration_minutes, summary, ...)` | update | `device_id` is never a parameter |
| `mark_commit_landed(update_id)` | update | doesn't trip `edited_at` — see below |

## Non-obvious things worth knowing before touching this code

These are decisions that took several rounds to arrive at — don't
"simplify" them back to the naive version without re-reading why in
`README.md` first.

- **`device_id` is never a tool argument.** It's resolved server-side from
  the caller's auth token (`MCPDeviceAuthMiddleware` in `main.py`). If you
  find yourself adding a `device` parameter to an MCP tool, stop — that's
  the bug this design specifically avoids.
- **Columns are matched by `role`, never by `name`.** `name` is freely
  renameable by the user; every place that means "the Done column" checks
  `role == "done"`.
- **`cards.blocked_since` is trigger-set**, not application code — it
  survives partial-progress updates on a still-blocked card without
  resetting. Don't try to compute "days blocked" from the latest update row.
- **`updates.edited_at`** is trigger-set too, but deliberately excludes
  `commit_landed` — see the trigger's `WHEN` clause. That field means
  "corrected after the fact"; flipping `commit_landed` is a routine
  lifecycle event, not a correction.
- **`digests` rows are locked forever once written.** Never overwrite one.
  If a card's `complexity` changes next month, past `efficiency_score`
  values must not change with it — that's the entire reason `digests`
  exists instead of just computing everything live.
- **The three cron times have a hard order**: 23:59 primary → 06:00
  fallback must finish → 09:30 notify reads what's there. Don't reschedule
  one without checking the others.
- **No dedup logic, anywhere, on purpose.** Two devices creating
  overlapping cards is fine — two cards, two update trails, neither blocks
  the other.
- **The IST timezone match matters.** `updates_for_day()` in
  `productivity.py` converts to `APP_TIMEZONE` before comparing dates — a
  raw `::date` cast in UTC silently misattributes anything logged between
  midnight and ~5:30 AM IST to the wrong day.

## Testing

No test suite exists yet — this is a freshly scaffolded backend/frontend,
not a finished product. Per the global CLAUDE.md, new features get TDD by
default from here on; don't add tests retroactively for code that's about
to change anyway while the schema is still settling.
