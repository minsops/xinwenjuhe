"""Collection orchestration and persistence for raw article DTOs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.article import Article
from app.models.discovered_source import DiscoveredSource
from app.models.event import Event
from app.models.source import Source
from app.schemas.article import RawArticle
from app.services.collector.api_collector import APICollector
from app.services.collector.google_news import GoogleNewsCollector
from app.services.collector.quality import build_collection_metrics, record_collection_metrics
from app.services.collector.rss_collector import RSSCollector
from app.services.collector.scraper import WebScraper
from app.services.collector.source_registry import update_collection_failure, update_collection_success
from app.services.processor.normalizer import ArticleNormalizer
from app.services.search import ExternalSearchClient
from app.tasks.progress import record_source_alert


class ArticleIngestionService:
    """Collect, normalize, deduplicate, and persist incoming article records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.normalizer = ArticleNormalizer()
        self.rss = RSSCollector()
        self.api = APICollector()
        self.scraper = WebScraper()
        self.google_news = GoogleNewsCollector()

    async def collect_source(self, source: Source, event_id: UUID | None = None) -> dict:
        """Collect one active source and persist new articles."""
        if not source.is_active:
            return {"source_id": str(source.id), "collected": 0, "skipped": 0, "status": "inactive"}

        try:
            raw_articles = await self._fetch_source_articles(source)
            result = await self.persist_articles(raw_articles, fallback_source=source, event_id=event_id)
            await record_collection_metrics(build_collection_metrics(source, raw_articles, result))
            source.last_collected_at = datetime.now(timezone.utc)
            update_collection_success(source)
            await self.db.commit()
            return {"source_id": str(source.id), "status": "ok", **result}
        except Exception as exc:
            await record_collection_metrics(build_collection_metrics(source, [], fulltext_fetch_errors=1))
            deactivated = update_collection_failure(source)
            if deactivated:
                record_source_alert(
                    str(source.id),
                    source.name,
                    "collection_failure_threshold",
                    {"consecutive_failures": source.consecutive_failures, "error": str(exc)},
                )
            await self.db.commit()
            raise

    async def collect_active_sources(self, limit: int | None = None) -> dict:
        """Collect all active RSS and configured scraper sources."""
        stmt = select(Source).where(Source.is_active.is_(True)).order_by(Source.last_collected_at.asc().nullsfirst())
        if limit:
            stmt = stmt.limit(limit)
        sources = (await self.db.execute(stmt)).scalars().all()
        results = []
        semaphore = asyncio.Semaphore(settings.max_concurrent_scrapers)

        async def fetch_one(source: Source) -> dict:
            if not source.is_active:
                return {"source": source, "raw_articles": [], "inactive": True}
            try:
                async with semaphore:
                    raw_articles = await self._fetch_source_articles(source)
                return {"source": source, "raw_articles": raw_articles}
            except Exception as exc:
                return {"source": source, "error": exc}

        # Network collection is concurrent; persistence stays serial to avoid shared-session races.
        fetch_results = await asyncio.gather(*(fetch_one(source) for source in sources))
        for item in fetch_results:
            source = item["source"]
            if item.get("inactive"):
                results.append({"source_id": str(source.id), "collected": 0, "skipped": 0, "status": "inactive"})
                continue
            if item.get("error"):
                exc = item["error"]
                await record_collection_metrics(build_collection_metrics(source, [], fulltext_fetch_errors=1))
                deactivated = update_collection_failure(source)
                if deactivated:
                    record_source_alert(
                        str(source.id),
                        source.name,
                        "collection_failure_threshold",
                        {"consecutive_failures": source.consecutive_failures, "error": str(exc)},
                    )
                await self.db.commit()
                results.append(
                    {
                        "source_id": str(source.id),
                        "status": "failed",
                        "collected": 0,
                        "skipped": 0,
                        "error": str(exc),
                    }
                )
                continue
            try:
                result = await self.persist_articles(item["raw_articles"], fallback_source=source)
                await record_collection_metrics(build_collection_metrics(source, item["raw_articles"], result))
                source.last_collected_at = datetime.now(timezone.utc)
                update_collection_success(source)
                await self.db.commit()
                results.append({"source_id": str(source.id), "status": "ok", **result})
            except Exception as exc:
                await record_collection_metrics(build_collection_metrics(source, item["raw_articles"], fulltext_fetch_errors=1))
                deactivated = update_collection_failure(source)
                if deactivated:
                    record_source_alert(
                        str(source.id),
                        source.name,
                        "collection_failure_threshold",
                        {"consecutive_failures": source.consecutive_failures, "error": str(exc)},
                    )
                await self.db.commit()
                results.append(
                    {
                        "source_id": str(source.id),
                        "status": "failed",
                        "collected": 0,
                        "skipped": 0,
                        "error": str(exc),
                    }
                )
        return {
            "status": "ok",
            "sources": len(sources),
            "collected": sum(item.get("collected", 0) for item in results),
            "skipped": sum(item.get("skipped", 0) for item in results),
            "results": results,
        }

    async def _fetch_source_articles(self, source: Source) -> list[RawArticle]:
        if source.feed_type == "rss":
            return await self.rss.fetch_feed(source)
        if source.feed_type == "api":
            return await self.api.fetch_feed(source)
        if source.feed_type == "scraper":
            return await self.scraper.scrape_source(source)
        return []

    async def collect_google_news_for_event(self, event: Event) -> dict:
        """Search Google News language feeds for an event and persist results."""
        query = event.title_en or event.title
        collected = 0
        skipped = 0
        languages = list(GoogleNewsCollector.REGION_FEEDS.keys())
        semaphore = asyncio.Semaphore(settings.max_concurrent_scrapers)

        async def search_language(language: str) -> dict:
            try:
                async with semaphore:
                    raw_articles = await self.google_news.search_event(query, language)
                return {"language": language, "raw_articles": raw_articles}
            except Exception as exc:
                return {"language": language, "raw_articles": [], "error": str(exc)}

        # Network fetches are independent and slow; DB writes stay serial on this session.
        language_results = await asyncio.gather(*(search_language(language) for language in languages))
        persisted_languages: list[dict] = []
        for item in language_results:
            language = item["language"]
            raw_articles = item["raw_articles"]
            if item.get("error"):
                persisted_languages.append({"language": language, "status": "failed", "error": item["error"], "collected": 0, "skipped": 0})
                continue
            await self.persist_discovered_sources(raw_articles)
            for article in raw_articles:
                article.source_id = await self._source_for_url(article.external_url, language)
            result = await self.persist_articles(raw_articles, event_id=event.id)
            collected += result["collected"]
            skipped += result["skipped"]
            persisted_languages.append({"language": language, "status": "ok", **result})
        await self.refresh_event_stats(event.id)
        await self.db.commit()
        return {"status": "ok", "event_id": str(event.id), "collected": collected, "skipped": skipped, "languages": persisted_languages}

    async def persist_discovered_sources(self, raw_articles: list[RawArticle]) -> int:
        """Persist new source candidates discovered through collected article URLs."""
        candidates = await self.google_news.discover_sources(raw_articles)
        inserted = 0
        for candidate in candidates:
            domain = candidate["domain"]
            existing = await self.db.scalar(
                select(DiscoveredSource).where(DiscoveredSource.domain == domain)
            )
            if existing:
                urls = set(existing.sample_urls or [])
                urls.update(article.external_url for article in raw_articles if domain in article.external_url)
                existing.sample_urls = sorted(urls)[:5]
                continue
            self.db.add(
                DiscoveredSource(
                    domain=domain,
                    language=candidate.get("language"),
                    status=candidate.get("status", "pending_review"),
                    sample_urls=[
                        article.external_url for article in raw_articles if domain in article.external_url
                    ][:5],
                )
            )
            inserted += 1
        await self.db.flush()
        return inserted

    async def persist_articles(
        self,
        raw_articles: list[RawArticle],
        fallback_source: Source | None = None,
        event_id: UUID | None = None,
    ) -> dict:
        """Insert unseen articles by URL while preserving original content."""
        collected = 0
        skipped = 0
        inserted_articles: list[tuple[Article, Source | None]] = []
        for raw in raw_articles:
            raw = self.normalizer.normalize(raw)
            if not raw.content_original:
                skipped += 1
                continue
            source_id = raw.source_id or (fallback_source.id if fallback_source else None)
            if source_id is None:
                source_id = await self._source_for_url(raw.external_url, raw.language)
            exists = await self.db.scalar(select(Article.id).where(Article.external_url == raw.external_url))
            if exists:
                skipped += 1
                continue
            article = Article(
                source_id=source_id,
                external_url=raw.external_url,
                title_original=raw.title_original,
                content_original=raw.content_original,
                language=raw.language,
                published_at=raw.published_at,
                author=raw.author,
                image_url=raw.image_url,
                event_id=event_id,
                article_metadata=raw.metadata,
            )
            self.db.add(article)
            inserted_articles.append((article, fallback_source))
            collected += 1
        await self.db.flush()
        indexer = ExternalSearchClient()
        for article, source in inserted_articles:
            await indexer.index_article(article, source)
        if event_id:
            await self.refresh_event_stats(event_id)
        return {"collected": collected, "skipped": skipped}

    async def refresh_event_stats(self, event_id: UUID) -> None:
        """Update event coverage counters from persisted articles."""
        event = await self.db.get(Event, event_id)
        if not event:
            return
        rows = (
            await self.db.execute(
                select(Article.source_id, Article.language, Source.region, Article.published_at)
                .join(Source, Source.id == Article.source_id)
                .where(Article.event_id == event_id)
            )
        ).all()
        event.article_count = len(rows)
        event.source_count = len({row.source_id for row in rows})
        event.language_count = len({row.language for row in rows})
        event.region_count = len({row.region for row in rows})
        event.regions_involved = sorted({row.region for row in rows})
        event.first_reported_at = min((row.published_at for row in rows if row.published_at), default=None)
        event.last_updated_at = max((row.published_at for row in rows if row.published_at), default=datetime.now(timezone.utc))
        event.heat_score = float(min(100, event.article_count * 8 + event.source_count * 6 + event.region_count * 5))
        await ExternalSearchClient().index_event(event)

    async def _source_for_url(self, url: str, language: str) -> UUID:
        """Map an article URL to an existing or newly discovered source."""
        domain = urlparse(url).netloc.replace("www.", "") or "unknown"
        existing = await self.db.scalar(select(Source).where(Source.feed_url == f"https://{domain}"))
        if existing:
            return existing.id
        source = Source(
            name=domain,
            name_en=domain,
            country="Unknown",
            region="unknown",
            language=language[:10],
            feed_type="google_news",
            feed_url=f"https://{domain}",
            is_active=False,
            transparency_score=0,
            composite_credibility=45,
        )
        self.db.add(source)
        await self.db.flush()
        return source.id
