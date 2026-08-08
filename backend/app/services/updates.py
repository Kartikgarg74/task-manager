"""Sheet 01 / Sheet 02: log_update, mark_commit_landed.

device_id is never a parameter here — it's passed in by the caller (the MCP
tool handler, resolved from the auth token) or left None for web-originated
writes. See app/mcp_server.py and app/auth.py.
"""

import uuid

from sqlalchemy import select

from app.models import Update


async def list_for_card(db, card_id: uuid.UUID) -> list[Update]:
    result = await db.execute(
        select(Update).where(Update.card_id == card_id).order_by(Update.created_at.desc())
    )
    return list(result.scalars())


async def log_update(
    db,
    card_id: uuid.UUID,
    resolved: str,
    duration_minutes: int,
    summary: str,
    impact: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    commit_hash: str | None = None,
    device_id: uuid.UUID | None = None,
) -> Update:
    update = Update(
        card_id=card_id,
        device_id=device_id,
        resolved=resolved,
        duration_minutes=duration_minutes,
        summary=summary,
        impact=impact,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        commit_hash=commit_hash,
        commit_landed=False,
    )
    db.add(update)
    await db.commit()
    await db.refresh(update)
    return update


async def mark_commit_landed(db, update_id: uuid.UUID) -> Update:
    """Claude calls this opportunistically after checking `git log origin/<branch>`
    for a commit_hash it previously logged — see Sheet 01, recap #10. This does NOT
    trip edited_at (see the trigger's WHEN clause in 0001_initial_schema.py) — that
    field means "corrected after the fact," and a landed-commit flip is a routine
    lifecycle event, not a correction."""
    update = await db.get(Update, update_id)
    if update is None:
        raise ValueError(f"no update {update_id}")
    update.commit_landed = True
    await db.commit()
    await db.refresh(update)
    return update
