"""Sheet 01: search_history(keywords, project?) — cross-project by default.

"Have I hit this before" is more useful searched everywhere than trapped in
one project, so `project_slug` narrows rather than being required.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Project, Update


async def search_history(db: AsyncSession, keywords: str, project_slug: str | None = None) -> list[dict]:
    pattern = f"%{keywords}%"
    query = (
        select(Update, Card, Project)
        .join(Card, Update.card_id == Card.id)
        .join(Project, Card.project_id == Project.id)
        .where(or_(Update.summary.ilike(pattern), Update.impact.ilike(pattern), Card.title.ilike(pattern)))
        .order_by(Update.created_at.desc())
        .limit(25)
    )
    if project_slug:
        query = query.where(Project.slug == project_slug)

    rows = await db.execute(query)
    return [
        {
            "project": project.slug,
            "card": card.title,
            "summary": update.summary,
            "impact": update.impact,
            "resolved": update.resolved,
            "commit_hash": update.commit_hash,
            "commit_landed": update.commit_landed,
            "created_at": update.created_at,
        }
        for update, card, project in rows
    ]
