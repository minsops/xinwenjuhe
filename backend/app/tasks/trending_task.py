"""Celery tasks for automated trending topic discovery."""

from __future__ import annotations

import asyncio

from app.services.clustering.pipeline import EventClusteringService
from app.services.collector.google_news import GoogleNewsCollector
from app.services.collector.ingestion import ArticleIngestionService
from app.services.collector.trending import CrossSourceTitleProvider, TrendingDiscovery, TrendingTopic
from app.tasks.celery_app import celery
from app.tasks.progress import set_progress
from app.tasks.worker_db import worker_session


TRENDING_SEARCH_LANGUAGES = ["en-US", "zh-CN", "ar", "ru", "es", "fr", "de", "ja", "pt-BR", "hi"]


@celery.task(
    bind=True,
    name="app.tasks.trending_task.discover_and_seed_events",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def discover_and_seed_events(self, limit: int = 10) -> dict:
    """Discover trending topics, collect articles, and cluster new events."""
    return asyncio.run(_discover_and_seed_events(self.request.id, limit))


async def _discover_and_seed_events(task_id: str, limit: int = 10) -> dict:
    set_progress(task_id, status="running", step="discover_trending", limit=limit)
    discovery = TrendingDiscovery()
    topics = await discovery.discover(limit=limit)

    async with worker_session() as db:
        db_topics = await CrossSourceTitleProvider().fetch_from_db(db, limit=limit)

    topics = TrendingDiscovery.deduplicate([*topics, *db_topics])[:limit]
    set_progress(task_id, status="running", step="collect_trending_articles", topics_found=len(topics))

    collected = 0
    skipped = 0
    topic_results: list[dict] = []
    google = GoogleNewsCollector()

    async with worker_session() as db:
        ingestion = ArticleIngestionService(db)
        for topic in topics:
            query = _topic_query(topic)
            topic_collected = 0
            topic_skipped = 0
            language_results = []
            for language in TRENDING_SEARCH_LANGUAGES:
                try:
                    raw_articles = await google.search_event(query, language)
                    await ingestion.persist_discovered_sources(raw_articles)
                    for article in raw_articles:
                        article.source_id = await ingestion._source_for_url(article.external_url, language)
                    result = await ingestion.persist_articles(raw_articles)
                    topic_collected += result["collected"]
                    topic_skipped += result["skipped"]
                    language_results.append({"language": language, "status": "ok", **result})
                except Exception as exc:
                    language_results.append(
                        {"language": language, "status": "failed", "collected": 0, "skipped": 0, "error": str(exc)}
                    )
            collected += topic_collected
            skipped += topic_skipped
            topic_results.append(
                {
                    "title": topic.title,
                    "source": topic.source,
                    "score": topic.score,
                    "collected": topic_collected,
                    "skipped": topic_skipped,
                    "languages": language_results,
                }
            )
        await db.commit()

    set_progress(task_id, status="running", step="cluster_discovered_articles", collected=collected)
    async with worker_session() as db:
        cluster_result = await EventClusteringService(db).cluster_unassigned(limit=500)

    result = {
        "status": "ok",
        "topics_discovered": len(topics),
        "articles_collected": collected,
        "articles_skipped": skipped,
        "events_created": cluster_result.get("events_created", 0),
        "pipelines_triggered": cluster_result.get("pipelines_triggered", 0),
        "topics": topic_results,
    }
    set_progress(task_id, status="complete", step="discover_and_seed_events", result=result)
    return result


def _topic_query(topic: TrendingTopic) -> str:
    keywords = [keyword for keyword in topic.keywords if keyword.strip()]
    return " ".join(keywords[:5]) or topic.title
