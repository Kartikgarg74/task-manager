"""Sheet 04/06: three cron triggers with a hard order — 23:59 primary must run,
then 06:00 fallback must finish, before 09:30 notify reads what's there. All
three anchored to APP_TIMEZONE (Asia/Kolkata), not server-local time, since
this runs wherever the host happens to be (Railway/Render, not Vercel — see
the architecture sheet).
"""

from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.jobs.digest_job import run_digest_generation
from app.jobs.notify_job import run_morning_notification

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    tz = get_settings().app_timezone

    async def primary_digest() -> None:
        from datetime import datetime

        from zoneinfo import ZoneInfo

        today = datetime.now(ZoneInfo(tz)).date()
        await run_digest_generation(today)

    async def fallback_digest() -> None:
        from datetime import datetime

        from zoneinfo import ZoneInfo

        yesterday = datetime.now(ZoneInfo(tz)).date() - timedelta(days=1)
        await run_digest_generation(yesterday)

    async def notify() -> None:
        from datetime import datetime

        from zoneinfo import ZoneInfo

        today = datetime.now(ZoneInfo(tz)).date()
        await run_morning_notification(today)

    scheduler.add_job(primary_digest, CronTrigger(hour=23, minute=59, timezone=tz), id="digest_primary")
    scheduler.add_job(fallback_digest, CronTrigger(hour=6, minute=0, timezone=tz), id="digest_fallback")
    scheduler.add_job(notify, CronTrigger(hour=9, minute=30, timezone=tz), id="notify")
    scheduler.start()
