"""Sheet 01 / Sheet 03: get_board, create_project, create_card, move_card.

Shared by the MCP tools (app/mcp_server.py) and the REST routers — one
implementation, two entry points, per the tool-reference table on Sheet 01.
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Column, Project

DEFAULT_COLUMNS = [
    ("Backlog", "backlog"),
    ("In Progress", "in_progress"),
    ("Blocked", "blocked"),
    ("Done", "done"),
]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


async def get_project_by_slug(db: AsyncSession, slug: str) -> Project | None:
    result = await db.execute(select(Project).where(Project.slug == slug))
    return result.scalar_one_or_none()


async def get_or_create_project(
    db: AsyncSession, name: str, device_id: uuid.UUID | None
) -> tuple[Project, bool]:
    """Sheet 03: the moment a project is mentioned that doesn't exist, create it —
    default columns included — before any work starts. Returns (project, created)."""
    slug = slugify(name)
    existing = await get_project_by_slug(db, slug)
    if existing is not None:
        return existing, False

    project = Project(name=name, slug=slug, created_via_device_id=device_id)
    db.add(project)
    await db.flush()

    for position, (col_name, role) in enumerate(DEFAULT_COLUMNS):
        db.add(Column(project_id=project.id, name=col_name, role=role, position=position))

    await db.commit()
    await db.refresh(project)
    return project, True


async def get_board(db: AsyncSession, slug: str) -> dict:
    project = await get_project_by_slug(db, slug)
    if project is None:
        return {"project": None, "columns": [], "cards": []}

    columns = (
        (await db.execute(select(Column).where(Column.project_id == project.id).order_by(Column.position)))
        .scalars()
        .all()
    )
    cards = (
        (await db.execute(select(Card).where(Card.project_id == project.id).order_by(Card.position)))
        .scalars()
        .all()
    )
    return {
        "project": {"id": str(project.id), "name": project.name, "slug": project.slug},
        "columns": [{"id": str(c.id), "name": c.name, "role": c.role, "position": c.position} for c in columns],
        "cards": [
            {
                "id": str(c.id),
                "column_id": str(c.column_id),
                "title": c.title,
                "priority": c.priority,
                "complexity": c.complexity,
                "blocked_since": c.blocked_since,
            }
            for c in cards
        ],
    }


async def create_card(
    db: AsyncSession, project_slug: str, title: str, priority: str = "medium"
) -> Card:
    project = await get_project_by_slug(db, project_slug)
    if project is None:
        raise ValueError(f"no project with slug {project_slug!r} — call create_project first")

    backlog = (
        await db.execute(
            select(Column).where(Column.project_id == project.id, Column.role == "backlog")
        )
    ).scalar_one()

    card = Card(project_id=project.id, column_id=backlog.id, title=title, priority=priority)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


async def move_card(db: AsyncSession, card_id: uuid.UUID, target_role: str) -> Card:
    card = await db.get(Card, card_id)
    if card is None:
        raise ValueError(f"no card {card_id}")

    target = (
        await db.execute(
            select(Column).where(Column.project_id == card.project_id, Column.role == target_role)
        )
    ).scalar_one()

    card.column_id = target.id  # trg_cards_blocked_since (Sheet 02) handles blocked_since
    await db.commit()
    await db.refresh(card)
    return card
