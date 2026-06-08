"""Database-backed event clustering pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.event import Event
from app.config import settings
from app.services.clustering.event_clusterer import EventClusterer
from app.services.collector.ingestion import ArticleIngestionService


class EventClusteringService:
    """Cluster unassigned articles into new events with source-diversity checks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.clusterer = EventClusterer()

    async def cluster_unassigned(self, limit: int = 200) -> dict:
        """Create events from unassigned articles when at least three sources agree."""
        articles = (
            await self.db.execute(
                select(Article)
                .where(Article.event_id.is_(None))
                .order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        if not articles:
            return {"status": "ok", "articles": 0, "events_created": 0}

        for article in articles:
            if not article.embedding:
                await self.clusterer.embed_article(article)

        recent_events = await self._recent_events_with_centers()
        remaining = []
        assigned = 0
        for article in articles:
            event = self._matching_event(article, recent_events)
            if event:
                article.event_id = event.id
                event.center_embedding = self._center([event.center_embedding or [], article.embedding or []])
                assigned += 1
            else:
                remaining.append(article)

        clusters = await self.clusterer.cluster_new_articles(remaining)
        created = 0
        for grouped in clusters.values():
            source_ids = {article.source_id for article in grouped}
            if len(grouped) < 3 or len(source_ids) < 3:
                continue
            event = Event(
                title=self._event_title(grouped),
                title_en=self._event_title(grouped),
                summary=self._event_summary(grouped),
                category="general",
                status="active",
                first_reported_at=min(
                    (article.published_at for article in grouped if article.published_at),
                    default=datetime.now(timezone.utc),
                ),
                last_updated_at=max(
                    (article.published_at for article in grouped if article.published_at),
                    default=datetime.now(timezone.utc),
                ),
                center_embedding=self._center([article.embedding or [] for article in grouped]),
            )
            self.db.add(event)
            await self.db.flush()
            for article in grouped:
                article.event_id = event.id
                assigned += 1
            await ArticleIngestionService(self.db).refresh_event_stats(event.id)
            created += 1

        await self.db.commit()
        return {"status": "ok", "articles": len(articles), "events_created": created, "assigned": assigned}

    async def _recent_events_with_centers(self) -> list[Event]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.cluster_time_window_hours)
        return (
            await self.db.execute(
                select(Event)
                .where(Event.center_embedding.is_not(None), Event.last_updated_at >= cutoff)
                .order_by(Event.last_updated_at.desc().nullslast())
            )
        ).scalars().all()

    def _matching_event(self, article: Article, events: list[Event]) -> Event | None:
        best_event: Event | None = None
        best_score = 0.0
        for event in events:
            score = self.clusterer.cosine(article.embedding or [], event.center_embedding or [])
            if score > best_score:
                best_score = score
                best_event = event
        if best_event and best_score >= settings.cluster_similarity_threshold:
            return best_event
        return None

    @staticmethod
    def _event_title(articles: list[Article]) -> str:
        return max(articles, key=lambda article: len(article.title_original)).title_original[:500]

    @staticmethod
    def _event_summary(articles: list[Article]) -> str:
        titles = "; ".join(article.title_original for article in articles[:3])
        return f"Automatically clustered from {len(articles)} related reports: {titles}"

    @staticmethod
    def _center(vectors: list[list[float]]) -> list[float] | None:
        vectors = [vector for vector in vectors if vector]
        if not vectors:
            return None
        dims = min(len(vector) for vector in vectors)
        return [sum(vector[index] for vector in vectors) / len(vectors) for index in range(dims)]
