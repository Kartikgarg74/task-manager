"""Sheet 06: 9:30 AM — reads what the 23:59/06:00 crons already locked in, combines
every active project into one email. Always sends, even on an idle day (a missing
email is ambiguous; a "0 minutes" email isn't) — and names any project whose digest
is missing entirely instead of silently omitting it.
"""

from datetime import date, timedelta

import resend
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Digest, Notification, Project


async def run_morning_notification(today: date) -> None:
    async with SessionLocal() as db:
        already_sent = (
            await db.execute(select(Notification).where(Notification.notification_date == today))
        ).scalar_one_or_none()
        if already_sent is not None:
            return  # Sheet 06: idempotency guard, same pattern as the digest's own check

        yesterday = today - timedelta(days=1)
        projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()

        lines = []
        total_minutes = 0
        for project in projects:
            digest = (
                await db.execute(
                    select(Digest).where(Digest.project_id == project.id, Digest.digest_date == yesterday)
                )
            ).scalar_one_or_none()
            if digest is None:
                lines.append(f"- {project.name}: no digest for yesterday — check the cron")
                continue
            total_minutes += digest.minutes_worked
            lines.append(
                f"- {project.name}: {digest.minutes_worked} min, efficiency {digest.efficiency_score} — "
                f"{len(digest.done_points)} done, {len(digest.tomorrow_points)} up next"
            )

        body = f"Yesterday: {total_minutes} minutes across {len(projects)} project(s).\n\n" + "\n".join(lines)
        sent = _send_email(subject=f"Task Manager — {yesterday.isoformat()}", body=body)

        # Only consume today's idempotency slot if an email was actually attempted.
        # Writing this row unconditionally meant "no key configured yet" permanently
        # burned that day's send — the key could be added later the same day and
        # nothing would go out until tomorrow, with no way to tell from the outside.
        if sent:
            db.add(Notification(notification_date=today))
            await db.commit()


def _send_email(subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.resend_api_key:
        return False  # local dev without email configured — job still runs, just doesn't send
    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            # Resend's shared sandbox sender — works with zero setup, no domain
            # verification needed. Swap for your own once you verify a domain
            # with Resend, via NOTIFY_FROM_EMAIL.
            "from": settings.notify_from_email,
            "to": settings.notify_email,
            "subject": subject,
            "text": body,
        }
    )
    return True
