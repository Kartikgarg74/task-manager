"""Free-tier-compatible replacement for the in-process APScheduler: GitHub
Actions (see .github/workflows/) curls these on a schedule instead of a
background thread firing inside the app. Same effect — the HTTP request
itself wakes a sleeping Render free instance, so "is the process alive at
23:59" stops being a question that matters.

Protected by a shared secret, not a device token or the web JWT — neither
of those fit "a scheduled workflow calling an endpoint" (see auth.py).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, status

from app.config import get_settings
from app.jobs.digest_job import run_digest_generation
from app.jobs.notify_job import run_morning_notification

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_cron_secret(x_cron_secret: str | None) -> None:
    if x_cron_secret != get_settings().internal_cron_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad or missing cron secret")


@router.post("/digest/primary")
async def digest_primary(x_cron_secret: str | None = Header(default=None)):
    """23:59 IST — target_date is today (IST)."""
    _require_cron_secret(x_cron_secret)
    tz = get_settings().app_timezone
    today = datetime.now(ZoneInfo(tz)).date()
    await run_digest_generation(today)
    return {"ran": "digest_primary", "target_date": today.isoformat()}


@router.post("/digest/fallback")
async def digest_fallback(x_cron_secret: str | None = Header(default=None)):
    """06:00 IST — target_date is yesterday (IST), catching up on a missed primary run."""
    _require_cron_secret(x_cron_secret)
    tz = get_settings().app_timezone
    yesterday = datetime.now(ZoneInfo(tz)).date() - timedelta(days=1)
    await run_digest_generation(yesterday)
    return {"ran": "digest_fallback", "target_date": yesterday.isoformat()}


@router.post("/notify")
async def notify(x_cron_secret: str | None = Header(default=None)):
    """09:30 IST."""
    _require_cron_secret(x_cron_secret)
    tz = get_settings().app_timezone
    today = datetime.now(ZoneInfo(tz)).date()
    await run_morning_notification(today)
    return {"ran": "notify", "date": today.isoformat()}
