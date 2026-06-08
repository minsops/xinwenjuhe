"""Celery tasks for scheduled source credibility refresh."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.source import Source
from app.services.analyzer.credibility_scorer import CredibilityScorer
from app.tasks.celery_app import celery
from app.tasks.progress import set_progress


@celery.task(
    bind=True,
    name="app.tasks.credibility_task.refresh_source_credibility",
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def refresh_source_credibility(self) -> dict:
    """Refresh credibility scores for all sources."""
    return asyncio.run(_refresh_source_credibility(self.request.id))


async def _refresh_source_credibility(task_id: str) -> dict:
    set_progress(task_id, status="running", step="refresh_source_credibility")
    async with AsyncSessionLocal() as db:
        sources = (await db.execute(select(Source))).scalars().all()
        scorer = CredibilityScorer()
        for source in sources:
            await scorer.update_source_scores(source)
        await db.commit()
    result = {"status": "ok", "updated": len(sources)}
    set_progress(task_id, status="complete", step="refresh_source_credibility", result=result)
    return result
