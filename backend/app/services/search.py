"""Database-backed search with optional external search-engine replacement point."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.article import Article
from app.models.event import Event
from app.models.source import Source
from app.schemas.article import ArticleRead
from app.schemas.event import EventRead


class SearchService:
    """Search articles and events through Meilisearch with database fallback."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.external = ExternalSearchClient()

    async def search(
        self,
        query: str,
        lang: str | None = None,
        region: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
    ) -> dict:
        external = await self.external.search(query, lang=lang, region=region, limit=limit)
        if external:
            return external
        events = await self._search_events(query, region, date_from, date_to, limit)
        articles = await self._search_articles(query, lang, region, date_from, date_to, limit)
        return {
            "events": [EventRead.model_validate(event).model_dump(mode="json") for event in events],
            "articles": [ArticleRead.model_validate(article).model_dump(mode="json") for article in articles],
        }

    async def _search_events(
        self,
        query: str,
        region: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
    ) -> list[Event]:
        stmt: Select = select(Event).where(
            or_(Event.title.ilike(f"%{query}%"), Event.summary.ilike(f"%{query}%"))
        )
        if region:
            stmt = stmt.where(or_(Event.region_primary == region, Event.regions_involved.any(region)))
        if date_from:
            stmt = stmt.where(Event.last_updated_at >= date_from)
        if date_to:
            stmt = stmt.where(Event.last_updated_at <= date_to)
        return (
            await self.db.execute(stmt.order_by(Event.heat_score.desc(), Event.last_updated_at.desc()).limit(limit))
        ).scalars().all()

    async def _search_articles(
        self,
        query: str,
        lang: str | None,
        region: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
    ) -> list[Article]:
        stmt: Select = select(Article).options(selectinload(Article.source)).where(
            or_(Article.title_original.ilike(f"%{query}%"), Article.content_original.ilike(f"%{query}%"))
        )
        if lang:
            stmt = stmt.where(Article.language == lang)
        if region:
            stmt = stmt.join(Source, Source.id == Article.source_id).where(Source.region == region)
        if date_from:
            stmt = stmt.where(Article.published_at >= date_from)
        if date_to:
            stmt = stmt.where(Article.published_at <= date_to)
        return (
            await self.db.execute(
                stmt.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc()).limit(limit)
            )
        ).scalars().all()


class ExternalSearchClient:
    """Tiny Meilisearch adapter that fails closed to the database search path."""

    def __init__(self) -> None:
        self.base_url = settings.search_engine_url.rstrip("/") if settings.search_engine_url else None
        self.api_key = settings.search_engine_api_key

    async def search(self, query: str, lang: str | None = None, region: str | None = None, limit: int = 50) -> dict | None:
        if not self.base_url:
            return None
        try:
            events, articles = await asyncio_gather_dict(
                self._search_index("events", query, limit),
                self._search_index("articles", query, limit),
            )
        except Exception:
            return None
        if lang:
            articles = [article for article in articles if article.get("language") == lang]
        if region:
            events = [event for event in events if region in {event.get("region_primary"), *(event.get("regions_involved") or [])}]
            articles = [article for article in articles if article.get("source_region") == region]
        if not events and not articles:
            return None
        return {"events": events[:limit], "articles": articles[:limit]}

    async def index_article(self, article: Article, source: Source | None = None) -> None:
        if not self.base_url:
            return
        document = {
            "id": str(article.id),
            "source_id": str(article.source_id),
            "source_region": source.region if source else None,
            "external_url": article.external_url,
            "title_original": article.title_original,
            "title_translated": article.title_translated,
            "content_original": article.content_original[:20000],
            "content_translated": article.content_translated,
            "language": article.language,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "event_id": str(article.event_id) if article.event_id else None,
        }
        await self._add_documents("articles", [document])

    async def index_event(self, event: Event) -> None:
        if not self.base_url:
            return
        document = {
            "id": str(event.id),
            "title": event.title,
            "title_en": event.title_en,
            "summary": event.summary,
            "region_primary": event.region_primary,
            "regions_involved": event.regions_involved or [],
            "heat_score": event.heat_score,
            "last_updated_at": event.last_updated_at.isoformat() if event.last_updated_at else None,
        }
        await self._add_documents("events", [document])

    async def _search_index(self, index: str, query: str, limit: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{self.base_url}/indexes/{index}/search",
                headers=self._headers(),
                json={"q": query, "limit": limit},
            )
            response.raise_for_status()
            return response.json().get("hits", [])

    async def _add_documents(self, index: str, documents: list[dict[str, Any]]) -> None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"{self.base_url}/indexes/{index}/documents",
                    headers=self._headers(),
                    json=documents,
                )
                response.raise_for_status()
        except Exception:
            return

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


async def asyncio_gather_dict(events_coro, articles_coro) -> tuple[list[dict], list[dict]]:
    import asyncio

    events, articles = await asyncio.gather(events_coro, articles_coro)
    return events, articles
