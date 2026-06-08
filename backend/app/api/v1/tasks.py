"""Task progress routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import ApiError, envelope
from app.tasks.cluster_task import cluster_new_articles
from app.tasks.collect_task import collect_active_sources, collect_hot_events
from app.tasks.credibility_task import refresh_source_credibility
from app.tasks.progress import get_progress, list_dead_letters, list_progress, list_source_alerts, queue_depth

router = APIRouter()


@router.get("")
async def list_task_progress(limit: int = 50):
    """Return recent task history and queue depth."""
    return envelope(
        {
            "history": list_progress(limit=limit),
            "dead_letters": list_dead_letters(limit=limit),
            "source_alerts": list_source_alerts(limit=limit),
            "queue_depth": queue_depth(),
        },
        limit=limit,
    )


@router.get("/dead-letters")
async def list_task_dead_letters(limit: int = 50):
    """Return final Celery failures retained for operator inspection."""
    return envelope({"dead_letters": list_dead_letters(limit=limit)}, limit=limit)


@router.get("/source-alerts")
async def list_collection_source_alerts(limit: int = 50):
    """Return source collection alerts such as automatic deactivation."""
    return envelope({"source_alerts": list_source_alerts(limit=limit)}, limit=limit)


@router.get("/{task_id}")
async def get_task_progress(task_id: str):
    """Return Redis-backed task progress for Celery pipelines."""
    progress = get_progress(task_id)
    if not progress:
        raise ApiError("task_not_found", "Task progress not found", 404)
    return envelope(progress)


@router.post("/collect-active-sources")
async def start_collect_active_sources(limit: int | None = None):
    result = collect_active_sources.delay(limit)
    return envelope({"task_id": result.id, "status": "queued", "task": "collect_active_sources"})


@router.post("/collect-hot-events")
async def start_collect_hot_events(limit: int = 10):
    result = collect_hot_events.delay(limit)
    return envelope({"task_id": result.id, "status": "queued", "task": "collect_hot_events"})


@router.post("/cluster-new-articles")
async def start_cluster_new_articles(limit: int = 200):
    result = cluster_new_articles.delay(limit)
    return envelope({"task_id": result.id, "status": "queued", "task": "cluster_new_articles"})


@router.post("/refresh-credibility")
async def start_refresh_credibility():
    result = refresh_source_credibility.delay()
    return envelope({"task_id": result.id, "status": "queued", "task": "refresh_source_credibility"})
