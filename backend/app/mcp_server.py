"""Sheet 01's tool-reference table, implemented. Every write tool resolves
device_id from the request's own auth context (app/auth.py) — it is never a
tool argument, so there's no string for Claude to pass or get wrong.

Hosted remotely (Sheet 01, recap #8) — mounted on the same FastAPI app as the
REST API (app/main.py) via streamable-HTTP, not run as a local/stdio process,
since a phone client needs to reach it too.
"""

import uuid
from contextvars import ContextVar

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.database import SessionLocal
from app.models import Device
from app.services import board, digest as digest_service, history, updates as update_service

# ponytail: the SDK's default DNS-rebinding protection only allows a hardcoded
# local-host allowlist, rejecting every real Host header including production's
# — it guards against a malicious webpage hitting an unauthenticated local MCP
# server, which isn't our threat model: every /mcp request already requires a
# valid device bearer token (app/main.py's MCPDeviceAuthMiddleware), checked
# before this SDK-level layer would even run. Revisit if this ever serves an
# MCP tool without that auth layer in front of it.
mcp = FastMCP(
    "task-manager",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# Set by the ASGI auth middleware (app/main.py) before each MCP tool call, from the
# device resolved out of the bearer token — see app/auth.py.
_current_device: ContextVar[Device | None] = ContextVar("_current_device", default=None)


def set_current_device(device: Device | None) -> None:
    _current_device.set(device)


@mcp.tool()
async def get_board(project: str) -> dict:
    """Current columns + cards for one project."""
    async with SessionLocal() as db:
        return await board.get_board(db, project)


@mcp.tool()
async def search_history(keywords: str, project: str | None = None) -> list[dict]:
    """Cross-project by default — omit `project` to search everywhere."""
    async with SessionLocal() as db:
        return await history.search_history(db, keywords, project)


@mcp.tool()
async def create_project(name: str) -> dict:
    """Creates the project + default columns (Backlog/In Progress/Blocked/Done) if it
    doesn't already exist. Safe to call every time — idempotent by slug."""
    async with SessionLocal() as db:
        device = _current_device.get()
        project, created = await board.get_or_create_project(db, name, device.id if device else None)
        return {"slug": project.slug, "name": project.name, "created": created}


@mcp.tool()
async def create_card(project: str, title: str, priority: str = "medium") -> dict:
    """One small card per discrete change — not one big card for a whole prompt."""
    async with SessionLocal() as db:
        card = await board.create_card(db, project, title, priority)
        return {"id": str(card.id), "title": card.title, "column_id": str(card.column_id)}


@mcp.tool()
async def move_card(card_id: str, target_role: str) -> dict:
    """target_role: backlog | in_progress | blocked | done. Only call 'done' once the
    change is actually verified working — never just because a run finished."""
    async with SessionLocal() as db:
        card = await board.move_card(db, uuid.UUID(card_id), target_role)
        return {"id": str(card.id), "column_id": str(card.column_id)}


@mcp.tool()
async def log_update(
    card_id: str,
    resolved: str,
    duration_minutes: int,
    summary: str,
    impact: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    commit_hash: str | None = None,
) -> dict:
    """resolved: done | partial | blocked. device_id is attached automatically from
    the calling device's auth token — do not pass it, there is no such parameter."""
    async with SessionLocal() as db:
        device = _current_device.get()
        update = await update_service.log_update(
            db,
            uuid.UUID(card_id),
            resolved,
            duration_minutes,
            summary,
            impact,
            input_tokens,
            output_tokens,
            commit_hash,
            device.id if device else None,
        )
        return {"id": str(update.id)}


@mcp.tool()
async def get_digest(project: str | None = None, range: str = "today") -> dict:
    """range: today | week | month. Omit `project` for the combined cross-project view
    (Sheet 06) instead of one project's own."""
    async with SessionLocal() as db:
        if project:
            proj = await board.get_project_by_slug(db, project)
            if proj is None:
                raise ValueError(f"no project {project!r}")
            return await digest_service.get_digest(db, proj, range)

        from sqlalchemy import select

        from app.models import Project

        projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()
        results = [await digest_service.get_digest(db, p, range) for p in projects]
        return {"range": range, "projects": results}


@mcp.tool()
async def mark_commit_landed(update_id: str) -> dict:
    """Call after confirming via `git log origin/<branch>` that a previously-logged
    commit_hash actually made it upstream. Does not affect edited_at."""
    async with SessionLocal() as db:
        update = await update_service.mark_commit_landed(db, uuid.UUID(update_id))
        return {"id": str(update.id), "commit_landed": update.commit_landed}
