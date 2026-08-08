"""Covers GET /api/projects — the sidebar's project list."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import require_web_user
from app.database import SessionLocal
from app.main import app
from app.services import board

app.dependency_overrides[require_web_user] = lambda: "test@example.com"


@pytest.mark.asyncio
async def test_list_projects_returns_active_projects_alphabetically():
    async with SessionLocal() as db:
        await board.get_or_create_project(db, "Zebra Project", None)
        await board.get_or_create_project(db, "Alpha Project", None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/projects")

    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names.index("Alpha Project") < names.index("Zebra Project")
