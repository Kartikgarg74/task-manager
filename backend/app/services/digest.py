"""Sheet 04 / Sheet 06: generate_digest (the 23:59 + 6am cron body) and get_digest
(the MCP/REST read side — live for today, locked history otherwise).
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Digest, Project
from app.services.productivity import done_points_for_day, project_efficiency, tomorrow_points


async def generate_digest(db: AsyncSession, project: Project, digest_date: date) -> Digest | None:
    """Idempotent: if a digest for (project, digest_date) already exists, this is a
    no-op — what makes the 6am fallback cron safe to fire even on a normal day."""
    existing = (
        await db.execute(
            select(Digest).where(Digest.project_id == project.id, Digest.digest_date == digest_date)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return None

    tz = get_settings().app_timezone
    done = await done_points_for_day(db, project.id, digest_date, tz)
    tomorrow = await tomorrow_points(db, project.id)
    efficiency, minutes = await project_efficiency(db, project.id, digest_date, tz)

    digest = Digest(
        project_id=project.id,
        digest_date=digest_date,
        done_points=done,
        tomorrow_points=tomorrow,
        minutes_worked=minutes,
        efficiency_score=efficiency,
    )
    db.add(digest)
    await db.commit()
    await db.refresh(digest)
    return digest


async def get_digest(
    db: AsyncSession, project: Project, range_: str
) -> dict:
    """range_: 'today' (live, provisional) | 'week' | 'month' (locked digests history)."""
    tz = get_settings().app_timezone
    today = datetime.now(timezone.utc).date()

    if range_ == "today":
        done = await done_points_for_day(db, project.id, today, tz)
        tomorrow = await tomorrow_points(db, project.id)
        efficiency, minutes = await project_efficiency(db, project.id, today, tz)
        return {
            "project": project.slug,
            "range": "today",
            "provisional": True,
            "done_points": done,
            "tomorrow_points": tomorrow,
            "minutes_worked": minutes,
            "efficiency_score": efficiency,
        }

    span = 7 if range_ == "week" else 30
    since = today - timedelta(days=span)
    rows = (
        await db.execute(
            select(Digest)
            .where(Digest.project_id == project.id, Digest.digest_date >= since)
            .order_by(Digest.digest_date)
        )
    ).scalars().all()

    return {
        "project": project.slug,
        "range": range_,
        "provisional": False,
        "days": [
            {"date": r.digest_date.isoformat(), "minutes_worked": r.minutes_worked, "efficiency_score": r.efficiency_score}
            for r in rows
        ],
        "total_minutes": sum(r.minutes_worked for r in rows),
    }
