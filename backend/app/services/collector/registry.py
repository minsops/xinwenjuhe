"""Pluggable source collector registry."""

from __future__ import annotations

from typing import Protocol

from app.models.source import Source
from app.schemas.article import RawArticle


class SourceCollector(Protocol):
    """Protocol implemented by all source collectors."""

    async def collect(self, source: Source) -> list[RawArticle]:
        """Collect raw articles from one source."""


class SourceCollectorRegistry:
    """Map feed_type values to collector implementations."""

    def __init__(self) -> None:
        self._registry: dict[str, SourceCollector] = {}

    def register(self, feed_type: str, collector: SourceCollector) -> None:
        self._registry[feed_type] = collector

    def get(self, feed_type: str) -> SourceCollector | None:
        return self._registry.get(feed_type)

    def supported_types(self) -> list[str]:
        return sorted(self._registry)


class RSSCollectorAdapter:
    """Adapter for RSS sources."""

    async def collect(self, source: Source) -> list[RawArticle]:
        from app.services.collector.rss_collector import RSSCollector

        return await RSSCollector().fetch_feed(source)


class APICollectorAdapter:
    """Adapter for JSON API sources."""

    async def collect(self, source: Source) -> list[RawArticle]:
        from app.services.collector.api_collector import APICollector

        return await APICollector().fetch_feed(source)


class ScraperCollectorAdapter:
    """Adapter for configured scraper sources."""

    async def collect(self, source: Source) -> list[RawArticle]:
        from app.services.collector.scraper import WebScraper

        return await WebScraper().scrape_source(source)


_global_registry: SourceCollectorRegistry | None = None


def get_registry() -> SourceCollectorRegistry:
    """Return the process-wide collector registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = SourceCollectorRegistry()
        _register_defaults(_global_registry)
    return _global_registry


def _register_defaults(registry: SourceCollectorRegistry) -> None:
    registry.register("rss", RSSCollectorAdapter())
    registry.register("api", APICollectorAdapter())
    registry.register("scraper", ScraperCollectorAdapter())
