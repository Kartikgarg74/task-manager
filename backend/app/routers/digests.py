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
from app.services.productivity import device_breakdown

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
    if range == "today":
        from datetime import datetime, timezone

        from app.config import get_settings

        today = datetime.now(timezone.utc).date()
        result["device_breakdown"] = await device_breakdown(db, project.id, today, get_settings().app_timezone)
    return result


@router.get("/overview")
async def overview(
    range: str = "today", db: AsyncSession = Depends(get_db), _user: str = Depends(require_web_user)
):
    """Sheet 06: combined view, all active projects. Minutes sum honestly; efficiency
    is shown per-project, never blended into one fake number."""
    projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()
    per_project = [await digest_service.get_digest(db, p, range) for p in projects]
    total_minutes = sum(
        p.get("minutes_worked", p.get("total_minutes", 0)) for p in per_project
    )
    return {"range": range, "total_minutes": total_minutes, "projects": per_project}
