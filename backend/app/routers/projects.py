"""Sheet 01: the web app's direct write path — device_id left null (no MCP round
trip), same tables, same broadcast-on-write as the MCP side.
"""

import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_web_user
from app.database import get_db
from app.models import Project
from app.schemas import CreateCardRequest, CreateProjectRequest, LogUpdateRequest, MoveCardRequest
from app.services import board, updates as update_service
from app.websocket import manager

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)):
    projects = (
        await db.execute(select(Project).where(Project.status == "active").order_by(Project.name))
    ).scalars().all()
    return [{"slug": p.slug, "name": p.name} for p in projects]


@router.post("")
async def create_project(
    body: CreateProjectRequest, db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)
):
    project, created = await board.get_or_create_project(db, body.name, None)
    return {"slug": project.slug, "name": project.name, "created": created}


@router.get("/{slug}/board")
async def get_board(slug: str, db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)):
    return await board.get_board(db, slug)


@router.post("/{slug}/cards")
async def create_card(
    slug: str,
    body: CreateCardRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_web_user),
):
    card = await board.create_card(db, slug, body.title, body.priority)
    await manager.broadcast(slug, {"type": "card_created", "card_id": str(card.id)})
    return {"id": str(card.id)}


@router.patch("/{slug}/cards/{card_id}/move")
async def move_card(
    slug: str,
    card_id: str,
    body: MoveCardRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_web_user),
):
    card = await board.move_card(db, uuid.UUID(card_id), body.target_role)
    await manager.broadcast(slug, {"type": "card_moved", "card_id": str(card.id), "column_id": str(card.column_id)})
    return {"id": str(card.id), "column_id": str(card.column_id)}


@router.get("/{slug}/cards/{card_id}/updates")
async def list_card_updates(
    slug: str,
    card_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_web_user),
):
    updates = await update_service.list_for_card(db, uuid.UUID(card_id))
    return [
        {
            "id": str(u.id),
            "resolved": u.resolved,
            "duration_minutes": u.duration_minutes,
            "summary": u.summary,
            "impact": u.impact,
            "commit_hash": u.commit_hash,
            "commit_landed": u.commit_landed,
            "created_at": u.created_at,
            "edited_at": u.edited_at,
        }
        for u in updates
    ]


@router.post("/{slug}/cards/{card_id}/updates")
async def log_update(
    slug: str,
    card_id: str,
    body: LogUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_web_user),
):
    # device_id=None — this is the web app's own direct write path (Sheet 01).
    update = await update_service.log_update(
        db,
        uuid.UUID(card_id),
        body.resolved,
        body.duration_minutes,
        body.summary,
        body.impact,
        body.input_tokens,
        body.output_tokens,
        body.commit_hash,
        device_id=None,
    )
    await manager.broadcast(slug, {"type": "update_logged", "card_id": card_id, "update_id": str(update.id)})
    return {"id": str(update.id)}


@router.websocket("/{slug}/ws")
async def board_ws(websocket: WebSocket, slug: str):
    await manager.connect(slug, websocket)
    try:
        while True:
            await websocket.receive_text()  # client doesn't send anything meaningful; just keeps the socket open
    except WebSocketDisconnect:
        manager.disconnect(slug, websocket)
