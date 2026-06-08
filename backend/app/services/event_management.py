"""Transactional event management operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.article import Article
from app.models.event import Event
from app.services.collector.ingestion import ArticleIngestionService


class EventManagementService:
    """Merge, split, and recalculate event clusters."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def merge_events(self, target_event_id: UUID, source_event_id: UUID) -> Event:
        """Move source event articles into target event and archive the source event."""
        if target_event_id == source_event_id:
            raise ApiError("invalid_merge", "Cannot merge an event into itself", 422)
        target = await self.db.get(Event, target_event_id)
        source = await self.db.get(Event, source_event_id)
        if not target or not source:
            raise ApiError("event_not_found", "One or more events were not found", 404)

        articles = (
            await self.db.execute(select(Article).where(Article.event_id == source_event_id))
        ).scalars().all()
        for article in articles:
            article.event_id = target_event_id
        source.status = "archived"
        source.summary = f"Merged into event {target_event_id}"
        await self.db.flush()
        ingestion = ArticleIngestionService(self.db)
        await ingestion.refresh_event_stats(target_event_id)
        await ingestion.refresh_event_stats(source_event_id)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def split_event(self, event_id: UUID, article_ids: list[UUID], title: str | None = None) -> Event:
        """Move selected articles from one event into a newly created event."""
        source = await self.db.get(Event, event_id)
        if not source:
            raise ApiError("event_not_found", "Event not found", 404)
        if not article_ids:
            raise ApiError("empty_split", "At least one article is required to split an event", 422)
        articles = (
            await self.db.execute(
                select(Article).where(Article.event_id == event_id, Article.id.in_(article_ids))
            )
        ).scalars().all()
        if len(articles) != len(set(article_ids)):
            raise ApiError("article_not_found", "One or more articles are not in the source event", 404)

        new_event = Event(
            title=title or self._title_from_articles(articles),
            title_en=title or self._title_from_articles(articles),
            summary=f"Split from event {event_id}",
            category=source.category,
            region_primary=source.region_primary,
            status="active",
        )
        self.db.add(new_event)
        await self.db.flush()
        for article in articles:
            article.event_id = new_event.id
        ingestion = ArticleIngestionService(self.db)
        await ingestion.refresh_event_stats(event_id)
        await ingestion.refresh_event_stats(new_event.id)
        await self.db.commit()
        await self.db.refresh(new_event)
        return new_event

    @staticmethod
    def _title_from_articles(articles: list[Article]) -> str:
        return max(articles, key=lambda article: len(article.title_original)).title_original[:500]

