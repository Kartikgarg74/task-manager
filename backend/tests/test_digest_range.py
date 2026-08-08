"""Covers the 'yesterday' digest range added for the Today page's day filter."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import require_web_user
from app.database import SessionLocal
from app.main import app
from app.models import Update
from app.services import board

app.dependency_overrides[require_web_user] = lambda: "test@example.com"


@pytest.mark.asyncio
async def test_yesterday_range_reflects_updates_logged_yesterday():
    async with SessionLocal() as db:
        project, _ = await board.get_or_create_project(db, "Digest Range Test", None)
        card = await board.create_card(db, project.slug, "probe card")

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        db.add(
            Update(
                card_id=card.id,
                resolved="done",
                duration_minutes=15,
                summary="did yesterday's work",
                impact="",
                commit_landed=False,
                created_at=yesterday,
            )
        )
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/projects/{project.slug}/digest?range=yesterday")

    assert resp.status_code == 200
    body = resp.json()
    assert body["provisional"] is False
    assert body["tomorrow_points"] == []
    assert any(p["summary"] == "did yesterday's work" for p in body["done_points"])
    assert body["minutes_worked"] >= 15


@pytest.mark.asyncio
async def test_card_untouched_yesterday_is_absent_from_yesterday_digest():
    async with SessionLocal() as db:
        project, _ = await board.get_or_create_project(db, "Digest Range Empty Test", None)
        card = await board.create_card(db, project.slug, "untouched today")
        db.add(
            Update(
                card_id=card.id,
                resolved="done",
                duration_minutes=10,
                summary="logged today, not yesterday",
                impact="",
                commit_landed=False,
            )
        )
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/projects/{project.slug}/digest?range=yesterday")

    assert resp.status_code == 200
    summaries = [p["summary"] for p in resp.json()["done_points"]]
    assert "logged today, not yesterday" not in summaries
