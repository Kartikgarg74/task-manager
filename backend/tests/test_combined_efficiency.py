"""Covers combined_efficiency — must pool raw updates and run the formula once,
not average each project's own pre-computed score (that distorts toward whichever
project logged fewer hours; see the comment on services/productivity.py).

Calls the service function directly with explicit project_ids rather than hitting
/api/overview, which pools every active project in the database -- other tests'
projects would otherwise leak into the pool and make this non-deterministic.
"""

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.database import SessionLocal
from app.models import Update
from app.services import board
from app.services.productivity import combined_efficiency


@pytest.mark.asyncio
async def test_combined_efficiency_pools_raw_updates_not_scores():
    suffix = uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        # small card, 120 min, done -> weight 1, hours 2 -> per-project eff would be 0.5
        project_a, _ = await board.get_or_create_project(db, f"Combined Eff A {suffix}", None)
        card_a = await board.create_card(db, project_a.slug, "small slow card")
        card_a.complexity = "small"
        db.add(Update(card_id=card_a.id, resolved="done", duration_minutes=120, summary="a", impact=""))

        # large card, 60 min, done -> weight 5, hours 1 -> per-project eff would be 5.0
        project_b, _ = await board.get_or_create_project(db, f"Combined Eff B {suffix}", None)
        card_b = await board.create_card(db, project_b.slug, "large fast card")
        card_b.complexity = "large"
        db.add(Update(card_id=card_b.id, resolved="done", duration_minutes=60, summary="b", impact=""))

        await db.commit()

        today = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).date()
        score, minutes = await combined_efficiency(
            db, [project_a.id, project_b.id], today, today, "Asia/Kolkata"
        )

    # naive average of 0.5 and 5.0 would be 2.75 -- pooled is (1 + 5) / (2 + 1) = 2.0
    assert score == 2.0
    assert minutes == 180
