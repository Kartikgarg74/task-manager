"""Sheet 04/05/06: per-project digest+productivity reads, and the combined
cross-project Overview — same query the 9:30 AM email uses, rendered as a page.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_web_user
from app.database import get_db
from app.models import Project
from app.services import board, digest as digest_service
from app.services.productivity import combined_efficiency, device_breakdown, resolve_range

router = APIRouter(prefix="/api", tags=["digests"])


@router.get("/projects/{slug}/digest")
async def project_digest(
    slug: str,
    range: str = "today",
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_web_user),
):
    project = await board.get_project_by_slug(db, slug)
    if project is None:
        raise HTTPException(404, "no such project")
    result = await digest_service.get_digest(db, project, range)
    if range in ("today", "yesterday"):
        from datetime import datetime, timedelta, timezone

        from app.config import get_settings

        today = datetime.now(timezone.utc).date()
        day = today if range == "today" else today - timedelta(days=1)
        result["device_breakdown"] = await device_breakdown(db, project.id, day, get_settings().app_timezone)
    return result


@router.get("/overview")
async def overview(
    range: str = "today", db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)
):
    """Sheet 06: combined view, all active projects. Minutes sum honestly. The combined
    efficiency score is computed once over every project's pooled raw updates — not
    averaged from each project's own score, which would distort toward whichever
    project logged fewer hours."""
    from datetime import datetime, timezone

    from app.config import get_settings

    projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()
    per_project = [await digest_service.get_digest(db, p, range) for p in projects]
    total_minutes = sum(
        p.get("minutes_worked", p.get("total_minutes", 0)) for p in per_project
    )

    today = datetime.now(timezone.utc).date()
    start, end = resolve_range(range, today)
    combined_score, _ = await combined_efficiency(
        db, [p.id for p in projects], start, end, get_settings().app_timezone
    )

    return {
        "range": range,
        "total_minutes": total_minutes,
        "combined_efficiency_score": combined_score,
        "projects": per_project,
    }
