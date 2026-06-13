"""Celery collection tasks for active sources and event-specific searches."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.websocket import publish_event_update
from app.config import settings
from app.models.article import Article
from app.models.event import Event
from app.models.source import Source
from app.services.collector.ingestion import ArticleIngestionService
from app.services.collector.rss_collector import RSSCollector
from app.services.search import ExternalSearchClient
from app.tasks.celery_app import celery
from app.tasks.progress import set_progress
from app.tasks.worker_db import worker_session


MIN_BACKFILL_FULLTEXT_LENGTH = 200


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


@celery.task(
    bind=True,
    name="app.tasks.collect_task.backfill_short_article_fulltext",
    autoretry_for=(),
)
def backfill_short_article_fulltext(self, limit: int = 50) -> dict:
    """Refetch full text for already persisted articles that only have short summaries."""
    return asyncio.run(_backfill_short_article_fulltext(self.request.id, limit))


@celery.task(
    bind=True,
    name="app.tasks.collect_task.backfill_article_fulltext",
    autoretry_for=(),
)
def backfill_article_fulltext(self, article_id: str) -> dict:
    """Refetch full text for one persisted article."""
    return asyncio.run(_backfill_article_fulltext(self.request.id, UUID(article_id)))


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
                event_result = await service.collect_google_news_for_event(event)
                results.append(event_result)
            except Exception as exc:
                event_result = {"event_id": str(event.id), "status": "failed", "error": str(exc)}
                results.append(event_result)
            await _publish_articles_collected(event.id, event_result)
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
    if result.get("status") != "missing_event":
        await _publish_articles_collected(event_id, result)
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


async def _backfill_short_article_fulltext(task_id: str, limit: int) -> dict:
    set_progress(task_id, status="running", step="backfill_short_article_fulltext", limit=limit)
    async with worker_session() as db:
        articles = (
            await db.execute(
                select(Article)
                .options(selectinload(Article.source))
                .where(func.length(Article.content_original) < MIN_BACKFILL_FULLTEXT_LENGTH)
                .order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        stats, affected_event_ids = await _backfill_article_rows(db, articles, task_id)
        await db.commit()

    triggered = _trigger_reanalysis(affected_event_ids)
    result = {
        "status": "ok",
        **stats,
        "events_touched": len(affected_event_ids),
        "pipelines_triggered": triggered,
    }
    await _publish_backfill_complete(affected_event_ids, result)
    set_progress(task_id, status="complete", step="backfill_short_article_fulltext", result=result)
    return result


async def _backfill_article_fulltext(task_id: str, article_id: UUID) -> dict:
    set_progress(task_id, status="running", step="backfill_article_fulltext", article_id=str(article_id))
    async with worker_session() as db:
        article = (
            await db.execute(select(Article).options(selectinload(Article.source)).where(Article.id == article_id))
        ).scalar_one_or_none()
        if not article:
            result = {"status": "missing_article", "article_id": str(article_id)}
            set_progress(task_id, status="complete", step="backfill_article_fulltext", result=result)
            return result
        stats, affected_event_ids = await _backfill_article_rows(db, [article], task_id)
        await db.commit()

    triggered = _trigger_reanalysis(affected_event_ids)
    result = {
        "status": "ok",
        "article_id": str(article_id),
        **stats,
        "events_touched": len(affected_event_ids),
        "pipelines_triggered": triggered,
    }
    await _publish_backfill_complete(affected_event_ids, result)
    set_progress(task_id, status="complete", step="backfill_article_fulltext", result=result)
    return result


async def _backfill_article_rows(
    db: AsyncSession,
    articles: list[Article],
    task_id: str,
) -> tuple[dict[str, int], set[UUID]]:
    fetcher = RSSCollector()
    indexer = ExternalSearchClient()
    updated = 0
    attempted = 0
    failed = 0
    affected_event_ids: set[UUID] = set()
    for article in articles:
        attempted += 1
        try:
            content = await fetcher.fetch_full_content(article.external_url)
        except Exception:
            failed += 1
            continue
        if not _is_better_fulltext(article.content_original, content):
            continue
        article.content_original = content.strip()
        article.content_translated = None
        metadata = dict(article.article_metadata or {})
        metadata["fulltext_backfilled"] = True
        metadata["fulltext_backfill_task_id"] = task_id
        article.article_metadata = metadata
        updated += 1
        if article.event_id:
            affected_event_ids.add(article.event_id)
        await indexer.index_article(article, article.source)
    return {"attempted": attempted, "updated": updated, "failed": failed}, affected_event_ids


def _is_better_fulltext(existing: str | None, candidate: str | None) -> bool:
    current = (existing or "").strip()
    proposed = (candidate or "").strip()
    return len(proposed) >= MIN_BACKFILL_FULLTEXT_LENGTH and len(proposed) > len(current)


def _trigger_reanalysis(event_ids: set[UUID]) -> int:
    triggered = 0
    if not event_ids:
        return triggered
    try:
        from app.tasks.analyze_task import process_event_pipeline
    except Exception:
        return triggered
    for event_id in event_ids:
        try:
            process_event_pipeline.delay(str(event_id))
            triggered += 1
        except Exception:
            continue
    return triggered


async def _publish_backfill_complete(event_ids: set[UUID], result: dict) -> None:
    for event_id in event_ids:
        await publish_event_update({"event_id": str(event_id), "type": "backfill_complete", "payload": result})


async def _publish_articles_collected(event_id: UUID, result: dict) -> None:
    await publish_event_update({"event_id": str(event_id), "type": "articles_collected", "payload": result})
