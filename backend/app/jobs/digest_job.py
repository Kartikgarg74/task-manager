"""Sheet 04: the 23:59 primary and 06:00 fallback both call this same function,
each passing its own target_date explicitly (see app/jobs/scheduler.py) rather
than the job trying to infer which run it is from the clock. Idempotent — see
generate_digest's existence check — so the fallback firing on a normal day,
when the primary already succeeded, is a harmless no-op.
"""

from datetime import date

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Project
from app.services.digest import generate_digest


async def run_digest_generation(target_date: date) -> None:
    async with SessionLocal() as db:
        projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()
        for project in projects:
            await generate_digest(db, project, target_date)
