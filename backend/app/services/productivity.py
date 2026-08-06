"""Sheet 05: the efficiency formula, plus the done/tomorrow point queries Sheet 04's
cron uses to build a digest. First-pass weights, not locked — see Sheet 05's figcaption.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Column, Device, Project, Update

COMPLEXITY_WEIGHT = {"small": 1, "medium": 3, "large": 5}
RESOLUTION_CREDIT = {"done": 1.0, "partial": 0.5, "blocked": 0.0}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
UP_NEXT_CAP = 10


def compute_efficiency(rows: list[tuple[str, str, int]]) -> tuple[float, int]:
    """rows: (complexity, resolved, duration_minutes). Returns (efficiency_score, minutes_worked).
    A large card left blocked all day scores 0, not negative — still counted as time spent."""
    minutes_worked = sum(r[2] for r in rows)
    if minutes_worked == 0:
        return 0.0, 0
    weighted = sum(COMPLEXITY_WEIGHT[c] * RESOLUTION_CREDIT[r] for c, r, _ in rows)
    hours = minutes_worked / 60
    return round(weighted / hours, 2), minutes_worked


async def updates_for_day(db: AsyncSession, project_id: uuid.UUID, day: date, tz: str) -> list[Update]:
    """Sheet 04: the date match runs in the app's own timezone, not the DB's default UTC —
    otherwise anything logged between midnight and ~5:30 AM IST lands in the wrong digest."""
    rows = await db.execute(
        select(Update, Card)
        .join(Card, Update.card_id == Card.id)
        .where(Card.project_id == project_id)
    )
    out = []
    for update, _card in rows:
        local_date = update.created_at.astimezone(_zoneinfo(tz)).date()
        if local_date == day:
            out.append(update)
    return out


def _zoneinfo(tz: str):
    from zoneinfo import ZoneInfo

    return ZoneInfo(tz)


async def done_points_for_day(db: AsyncSession, project_id: uuid.UUID, day: date, tz: str) -> list[dict]:
    updates = await updates_for_day(db, project_id, day, tz)
    points = []
    for u in updates:
        card = await db.get(Card, u.card_id)
        points.append({"card": card.title, "summary": u.summary, "impact": u.impact, "resolved": u.resolved})
    return points


async def tomorrow_points(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    """Sheet 04: top 10 non-Blocked by priority + ALL Blocked, uncapped, with days-blocked
    read from cards.blocked_since — not the most recent update, which would misleadingly
    reset on partial progress."""
    rows = (
        await db.execute(
            select(Card, Column)
            .join(Column, Card.column_id == Column.id)
            .where(Card.project_id == project_id, Column.role != "done")
        )
    ).all()

    blocked = [c for c, col in rows if col.role == "blocked"]
    open_others = sorted(
        (c for c, col in rows if col.role != "blocked"),
        key=lambda c: PRIORITY_ORDER.get(c.priority, 1),
    )[:UP_NEXT_CAP]

    now = datetime.now(timezone.utc)
    points = [{"card": c.title, "priority": c.priority} for c in open_others]
    for c in blocked:
        days = (now - c.blocked_since).days if c.blocked_since else 0
        points.append({"card": c.title, "priority": c.priority, "blocked_days": days})
    return points


async def project_efficiency(
    db: AsyncSession, project_id: uuid.UUID, day: date, tz: str
) -> tuple[float, int]:
    updates = await updates_for_day(db, project_id, day, tz)
    rows = []
    for u in updates:
        card = await db.get(Card, u.card_id)
        rows.append((card.complexity, u.resolved, u.duration_minutes))
    return compute_efficiency(rows)


async def device_breakdown(db: AsyncSession, project_id: uuid.UUID, day: date, tz: str) -> list[dict]:
    """Sheet 05: per-device minutes, reconstructed live from updates.device_id — never
    stored redundantly. Null device_id means the web app."""
    updates = await updates_for_day(db, project_id, day, tz)
    totals: dict[str | None, int] = {}
    for u in updates:
        key = str(u.device_id) if u.device_id else None
        totals[key] = totals.get(key, 0) + u.duration_minutes

    out = []
    for device_id, minutes in totals.items():
        label = "web"
        if device_id:
            device = await db.get(Device, uuid.UUID(device_id))
            label = device.label if device else "unknown device"
        out.append({"device": label, "minutes": minutes})
    return out
