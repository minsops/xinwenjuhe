"""Celery clustering tasks."""

from __future__ import annotations

import asyncio

from app.db import AsyncSessionLocal
from app.services.clustering.pipeline import EventClusteringService
from app.tasks.celery_app import celery
from app.tasks.progress import set_progress


@celery.task(
    bind=True,
    name="app.tasks.cluster_task.cluster_new_articles",
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def cluster_new_articles(self, limit: int = 200) -> dict:
    """Cluster newly collected articles."""
    return asyncio.run(_cluster_new_articles(self.request.id, limit))


async def _cluster_new_articles(task_id: str, limit: int) -> dict:
    set_progress(task_id, status="running", step="cluster_new_articles")
    async with AsyncSessionLocal() as db:
        result = await EventClusteringService(db).cluster_unassigned(limit=limit)
    set_progress(task_id, status="complete", step="cluster_new_articles", result=result)
    return result
