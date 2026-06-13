"""Regression tests for automatic event analysis triggering."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from importlib.util import find_spec
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import uuid

if not find_spec("celery") or not find_spec("sqlalchemy"):
    raise unittest.SkipTest("Celery and SQLAlchemy are required for pipeline triggering tests")

from app.models.article import Article
from app.models.credibility import EventAnalysis
from app.models.event import Event
from app.services.clustering.pipeline import EventClusteringService
from app.tasks import analyze_task


class PipelineTriggeringTest(unittest.TestCase):
    """Validate cluster-trigger, scan-trigger, and lock de-duplication behavior."""

    def test_cluster_unassigned_triggers_pipeline_for_new_event(self) -> None:
        async def run_case() -> tuple[dict, list[str], FakeClusterDB]:
            articles = [_article(index) for index in range(3)]
            db = FakeClusterDB(articles)
            triggered: list[str] = []

            service = EventClusteringService(db)
            service._recent_events_with_centers = _empty_recent_events
            service.clusterer.cluster_new_articles = _single_cluster

            with (
                patch(
                    "app.services.clustering.pipeline.ArticleIngestionService",
                    FakeIngestionService,
                ),
                patch.object(
                    analyze_task.process_event_pipeline,
                    "delay",
                    side_effect=lambda event_id: triggered.append(event_id),
                ),
            ):
                result = await service.cluster_unassigned()
            return result, triggered, db

        result, triggered, db = asyncio.run(run_case())

        self.assertEqual(result["events_created"], 1)
        self.assertEqual(result["pipelines_triggered"], 1)
        self.assertEqual(len(triggered), 1)
        self.assertEqual(triggered[0], str(db.added_events[0].id))

    def test_scan_events_needing_analysis_queues_missing_and_stale_events(self) -> None:
        missing = _event(article_count=3)
        fresh = _event(article_count=10)
        stale = _event(article_count=12)
        rows = [
            (missing, None),
            (fresh, _analysis(fresh.id, article_count_at_analysis=10)),
            (stale, _analysis(stale.id, article_count_at_analysis=10)),
        ]
        queued: list[str] = []

        with (
            patch(
                "app.tasks.analyze_task.worker_session",
                return_value=FakeWorkerSession(FakeScanDB(rows)),
            ),
            patch.object(
                analyze_task.process_event_pipeline,
                "delay",
                side_effect=lambda event_id: SimpleNamespace(
                    id=f"task-{event_id}",
                    event_id=queued.append(event_id),
                ),
            ),
        ):
            result = asyncio.run(analyze_task._scan_events_needing_analysis("scan-task", 20))

        self.assertEqual(result["queued"], 2)
        self.assertEqual(queued, [str(missing.id), str(stale.id)])
        self.assertEqual(result["event_ids"], queued)

    def test_pipeline_lock_skips_duplicate_event_pipeline(self) -> None:
        event_id = str(uuid.uuid4())
        fake_redis = FakeRedis()

        with patch("app.tasks.analyze_task.Redis.from_url", return_value=fake_redis):
            self.assertTrue(analyze_task._acquire_pipeline_lock(event_id))
            self.assertFalse(analyze_task._acquire_pipeline_lock(event_id))

        self.assertEqual(fake_redis.keys, {f"pipeline_lock:{event_id}"})


class FakeResult:
    """Minimal SQLAlchemy result double."""

    def __init__(self, rows: list) -> None:
        self.rows = rows

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list:
        return self.rows


class FakeClusterDB:
    """Session double for clustering without a real database."""

    def __init__(self, articles: list[Article]) -> None:
        self.articles = articles
        self.added_events: list[Event] = []
        self.committed = False

    async def execute(self, query) -> FakeResult:
        return FakeResult(self.articles)

    def add(self, item) -> None:
        if isinstance(item, Event):
            self.added_events.append(item)

    async def flush(self) -> None:
        if self.added_events[-1].id is None:
            self.added_events[-1].id = uuid.uuid4()

    async def commit(self) -> None:
        self.committed = True


class FakeIngestionService:
    """No-op stats refresher for clustering tests."""

    def __init__(self, db) -> None:
        self.db = db

    async def refresh_event_stats(self, event_id: uuid.UUID) -> None:
        return None


class FakeScanDB:
    """Session double returning event-analysis rows."""

    def __init__(self, rows: list[tuple[Event, EventAnalysis | None]]) -> None:
        self.rows = rows

    async def execute(self, query) -> FakeResult:
        return FakeResult(self.rows)


class FakeWorkerSession:
    """Async context manager for worker_session replacement."""

    def __init__(self, db: FakeScanDB) -> None:
        self.db = db

    async def __aenter__(self) -> FakeScanDB:
        return self.db

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeRedis:
    """Redis set(nx=True) double for pipeline lock tests."""

    def __init__(self) -> None:
        self.keys: set[str] = set()

    def set(self, key: str, value: str, nx: bool, ex: int) -> bool:
        if nx and key in self.keys:
            return False
        self.keys.add(key)
        return True


async def _empty_recent_events() -> list[Event]:
    return []


async def _single_cluster(articles: list[Article]) -> dict[int, list[Article]]:
    return {0: articles}


def _article(index: int) -> Article:
    return Article(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        external_url=f"https://example.test/{index}",
        title_original=f"Shared event report {index}",
        content_original="Full article body",
        language="en",
        published_at=datetime(2026, 6, 13, index, tzinfo=timezone.utc),
        embedding=[1.0, 0.0, 0.0],
    )


def _event(article_count: int) -> Event:
    return Event(
        id=uuid.uuid4(),
        title="event",
        title_en="event",
        status="active",
        article_count=article_count,
        heat_score=80,
        last_updated_at=datetime(2026, 6, 13, tzinfo=timezone.utc),
    )


def _analysis(event_id: uuid.UUID, article_count_at_analysis: int) -> EventAnalysis:
    return EventAnalysis(
        id=uuid.uuid4(),
        event_id=event_id,
        summary="summary",
        consensus_facts=[],
        disputed_facts=[],
        blind_spots=[],
        narrative_frames=[],
        article_count_at_analysis=article_count_at_analysis,
    )


if __name__ == "__main__":
    unittest.main()
