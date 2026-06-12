"""Celery collection tasks for active sources and event-specific searches."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.models.event import Event
from app.models.source import Source
from app.services.collector.ingestion import ArticleIngestionService
from app.tasks.celery_app import celery
from app.tasks.progress import set_progress
from app.tasks.worker_db import worker_session


@celery.task(
    bind=True,
    name="app.tasks.collect_task.collect_active_sources",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def collect_active_sources(self, limit: int | None = None) -> dict:
    """Collect active RSS/scraper sources and persist new articles."""
    return asyncio.run(_collect_active_sources(self.request.id, limit))


@celery.task(
    bind=True,
    name="app.tasks.collect_task.collect_hot_events",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def collect_hot_events(self, limit: int = 10) -> dict:
    """Collect Google News updates for hot active events."""
    return asyncio.run(_collect_hot_events(self.request.id, limit))


@celery.task(
    bind=True,
    name="app.tasks.collect_task.collect_articles_for_event",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def collect_articles_for_event(self, event_id: str) -> dict:
    """Collect multilingual Google News results for a specific event."""
    return asyncio.run(_collect_articles_for_event(self.request.id, UUID(event_id)))


@celery.task(
    bind=True,
    name="app.tasks.collect_task.collect_single_source",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def collect_single_source(self, source_id: str) -> dict:
    """Collect one source by id."""
    return asyncio.run(_collect_single_source(self.request.id, UUID(source_id)))


async def _collect_active_sources(task_id: str, limit: int | None) -> dict:
    set_progress(task_id, status="running", step="collect_active_sources")
    async with worker_session() as db:
        result = await ArticleIngestionService(db).collect_active_sources(limit=limit)
    set_progress(task_id, status="complete", step="collect_active_sources", result=result)
    return result


async def _collect_hot_events(task_id: str, limit: int) -> dict:
    set_progress(task_id, status="running", step="collect_hot_events")
    if not settings.google_news_enabled:
        result = {"status": "disabled", "events": 0, "collected": 0, "skipped": 0, "results": []}
        set_progress(task_id, status="complete", step="collect_hot_events", result=result)
        return result
    async with worker_session() as db:
        events = (
            await db.execute(
                select(Event)
                .where(Event.status == "active", Event.heat_score >= settings.hot_event_threshold)
                .order_by(Event.heat_score.desc(), Event.last_updated_at.desc().nullslast())
                .limit(limit)
            )
        ).scalars().all()
        service = ArticleIngestionService(db)
        results = []
        for event in events:
            try:
                results.append(await service.collect_google_news_for_event(event))
            except Exception as exc:
                results.append({"event_id": str(event.id), "status": "failed", "error": str(exc)})
        result = {
            "status": "ok",
            "events": len(events),
            "collected": sum(item.get("collected", 0) for item in results),
            "skipped": sum(item.get("skipped", 0) for item in results),
            "results": results,
        }
    set_progress(task_id, status="complete", step="collect_hot_events", result=result)
    return result


async def _collect_articles_for_event(task_id: str, event_id: UUID) -> dict:
    set_progress(task_id, status="running", step="collect_articles_for_event", event_id=str(event_id))
    async with worker_session() as db:
        event = await db.get(Event, event_id)
        if not event:
            result = {"status": "missing_event", "event_id": str(event_id)}
        else:
            result = await ArticleIngestionService(db).collect_google_news_for_event(event)
    set_progress(task_id, status="complete", step="collect_articles_for_event", result=result)
    return result


async def _collect_single_source(task_id: str, source_id: UUID) -> dict:
    set_progress(task_id, status="running", step="collect_single_source", source_id=str(source_id))
    async with worker_session() as db:
        source = await db.scalar(select(Source).where(Source.id == source_id))
        if not source:
            result = {"status": "missing_source", "source_id": str(source_id)}
        else:
            result = await ArticleIngestionService(db).collect_source(source)
    set_progress(task_id, status="complete", step="collect_single_source", result=result)
    return result
