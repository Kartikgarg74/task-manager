"""Covers GET /cards/{id}/updates — the endpoint the card detail panel reads."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import require_web_user
from app.main import app

app.dependency_overrides[require_web_user] = lambda: "test@example.com"


@pytest.mark.asyncio
async def test_list_card_updates_returns_logged_updates():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project = (await client.post("/api/projects", json={"name": "Card Updates Test"})).json()
        card = (
            await client.post(
                f"/api/projects/{project['slug']}/cards", json={"title": "probe card", "priority": "medium"}
            )
        ).json()

        await client.post(
            f"/api/projects/{project['slug']}/cards/{card['id']}/updates",
            json={"resolved": "done", "duration_minutes": 5, "summary": "did the thing", "impact": "it works"},
        )

        resp = await client.get(f"/api/projects/{project['slug']}/cards/{card['id']}/updates")

        assert resp.status_code == 200
        updates = resp.json()
        assert len(updates) == 1
        assert updates[0]["summary"] == "did the thing"
        assert updates[0]["impact"] == "it works"
        assert updates[0]["resolved"] == "done"
        assert updates[0]["commit_landed"] is False


@pytest.mark.asyncio
async def test_list_card_updates_empty_for_untouched_card():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project = (await client.post("/api/projects", json={"name": "Card Updates Empty Test"})).json()
        card = (
            await client.post(
                f"/api/projects/{project['slug']}/cards", json={"title": "untouched card"}
            )
        ).json()

        resp = await client.get(f"/api/projects/{project['slug']}/cards/{card['id']}/updates")

        assert resp.status_code == 200
        assert resp.json() == []
