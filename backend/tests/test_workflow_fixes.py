"""Regression tests for the documented workflow fixes."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest
import uuid

HAS_WORKFLOW_DEPS = bool(
    importlib.util.find_spec("celery")
    and importlib.util.find_spec("redis")
    and importlib.util.find_spec("sqlalchemy")
)

if HAS_WORKFLOW_DEPS:
    from app.models.article import Article
    from app.models.fact_fragment import FactFragment
    from app.services.analyzer.event_analysis_service import EventAnalysisService
    from app.services.analyzer.fact_extractor import FactExtractor
    from app.tasks import analyze_task
    from app.tasks.collect_task import MIN_BACKFILL_FULLTEXT_LENGTH, _is_better_fulltext
    from app.tasks.worker_db import worker_session


TEST_DIR = Path(__file__).resolve().parent
HOST_ROOT = TEST_DIR.parents[1]
CONTAINER_ROOT = TEST_DIR.parent
ROOT = HOST_ROOT if (HOST_ROOT / "backend").exists() else CONTAINER_ROOT
BACKEND_ROOT = ROOT / "backend" if (ROOT / "backend").exists() else ROOT


@unittest.skipUnless(HAS_WORKFLOW_DEPS, "Celery, Redis, and SQLAlchemy are required for workflow tests")
class WorkflowFixesTest(unittest.TestCase):
    """Validate worker, extraction, and pipeline contracts."""

    def test_worker_session_can_be_created_in_consecutive_event_loops(self) -> None:
        async def open_session() -> None:
            async with worker_session():
                pass

        asyncio.run(open_session())
        asyncio.run(open_session())

    def test_tasks_do_not_import_fastapi_session_factory(self) -> None:
        for path in (BACKEND_ROOT / "app/tasks").glob("*.py"):
            self.assertNotIn("AsyncSessionLocal", path.read_text(encoding="utf-8"), path.name)

    def test_autoretry_tasks_have_retry_limits(self) -> None:
        for path in (BACKEND_ROOT / "app/tasks").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "autoretry_for=(Exception,)" in text:
                self.assertIn("max_retries=3", text, path.name)
                self.assertIn("retry_backoff_max=600", text, path.name)

    def test_pipeline_chain_no_longer_runs_full_translation_stage(self) -> None:
        text = (BACKEND_ROOT / "app/tasks/analyze_task.py").read_text(encoding="utf-8")
        process_body = text.split('name="app.tasks.analyze_task.process_event_pipeline"')[1].split("def _event_id_from_payload")[0]

        self.assertIn("deduplicate_articles.s()", process_body)
        self.assertNotIn("translate_articles.s()", process_body)
        self.assertNotIn("group(", process_body)
        self.assertIn("_acquire_pipeline_lock(event_id)", process_body)

    def test_extract_facts_is_incremental(self) -> None:
        text = (BACKEND_ROOT / "app/tasks/analyze_task.py").read_text(encoding="utf-8")
        extract_body = text.split("async def _extract_facts")[1].split("async def _detect_contradictions")[0]

        self.assertIn("already_extracted", extract_body)
        self.assertIn("Article.id.not_in(already_extracted)", extract_body)
        self.assertNotIn("delete(FactFragment).where(FactFragment.event_id", extract_body)
        self.assertNotIn("+ len(fragments)", extract_body)

    def test_short_article_fulltext_backfill_only_accepts_longer_fulltext(self) -> None:
        self.assertFalse(_is_better_fulltext("short summary", "still short"))
        self.assertFalse(_is_better_fulltext("x" * MIN_BACKFILL_FULLTEXT_LENGTH, "y" * MIN_BACKFILL_FULLTEXT_LENGTH))
        self.assertTrue(_is_better_fulltext("short summary", "full article body " * 20))

    def test_fallback_extracts_title_and_only_casualty_context_not_year(self) -> None:
        article = Article(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            external_url="https://example.test/a",
            title_original="事故通报",
            content_original="2026年6月，事故造成12人死亡。",
            language="zh-CN",
        )

        fragments = FactExtractor()._fallback_extract(article)
        number_fragments = [fragment for fragment in fragments if fragment["type"] == "number"]

        self.assertEqual(fragments[0]["type"], "what")
        self.assertIn("事故通报", fragments[0]["content"])
        self.assertEqual(len(number_fragments), 1)
        self.assertEqual(number_fragments[0]["numbers"]["description"], "casualties")
        self.assertEqual(number_fragments[0]["numbers"]["value"], 12)

    def test_fallback_keeps_title_fact_when_no_clear_numbers_exist(self) -> None:
        article = Article(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            external_url="https://example.test/b",
            title_original="2026年6月发布事故调查进展",
            content_original="2026年6月，调查人员公布新的时间线，没有报告伤亡人数。",
            language="zh-CN",
        )

        fragments = FactExtractor()._fallback_extract(article)

        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0]["type"], "what")
        self.assertFalse(fragments[0]["numbers"])

    def test_duplicate_articles_produce_no_fact_fragments(self) -> None:
        event_id = uuid.uuid4()
        duplicate = Article(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            external_url="https://example.test/duplicate",
            title_original="Duplicate",
            content_original="Duplicate body",
            language="en",
            article_metadata={"duplicate_of": str(uuid.uuid4())},
        )
        original = Article(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            external_url="https://example.test/original",
            title_original="Original",
            content_original="Original body",
            language="en",
            article_metadata={"wire_agency": "REUTERS"},
        )

        class FakeExtractor:
            async def extract(self, article: Article) -> list[dict]:
                return [
                    {
                        "type": "what",
                        "content": article.title_original,
                        "content_en": article.title_original,
                        "entities": {},
                        "numbers": {},
                        "source_attribution": "unattributed",
                        "certainty_level": "reportedly",
                    }
                ]

        class FakeEmbedder:
            is_using_fallback = False

            async def embed_text(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0]

        with (
            patch("app.services.analyzer.event_analysis_service.FactExtractor", return_value=FakeExtractor()),
            patch("app.services.analyzer.event_analysis_service.TextEmbedder", return_value=FakeEmbedder()),
        ):
            fragments = asyncio.run(EventAnalysisService(None)._extract_fragments(event_id, [duplicate, original]))

        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0].article_id, original.id)
        self.assertEqual(fragments[0].entities["_via_wire"], "REUTERS")

    def test_deduplicate_updates_existing_fragments_with_wire_marker(self) -> None:
        event_id = uuid.uuid4()
        article = Article(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            external_url="https://example.test/reuters",
            title_original="Wire report",
            content_original="Reuters reported the latest casualty figures from officials.",
            language="en",
            article_metadata={},
        )
        fragment = FactFragment(
            id=uuid.uuid4(),
            event_id=event_id,
            article_id=article.id,
            source_id=article.source_id,
            fragment_type="what",
            content="已有事实碎片",
            content_en="Existing fact fragment",
            entities={"actor": "officials"},
            numbers={},
            source_attribution="unattributed",
            certainty_level="reportedly",
            embedding=[1.0, 0.0, 0.0],
        )

        class FakeResult:
            def __init__(self, rows: list) -> None:
                self.rows = rows

            def scalars(self) -> "FakeResult":
                return self

            def all(self) -> list:
                return self.rows

        class FakeDB:
            def __init__(self) -> None:
                self.select_calls = 0
                self.committed = False

            async def execute(self, query) -> FakeResult:
                self.select_calls += 1
                return FakeResult([article] if self.select_calls == 1 else [fragment])

            async def commit(self) -> None:
                self.committed = True

        class FakeSession:
            def __init__(self, db: FakeDB) -> None:
                self.db = db

            async def __aenter__(self) -> FakeDB:
                return self.db

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        db = FakeDB()
        with patch("app.tasks.analyze_task.worker_session", return_value=FakeSession(db)):
            result = asyncio.run(analyze_task._deduplicate_articles("task-id", {"event_id": str(event_id)}))

        self.assertTrue(db.committed)
        self.assertEqual(result["wire_copies"], 1)
        self.assertEqual(article.article_metadata["wire_agency"], "REUTERS")
        self.assertEqual(fragment.entities["actor"], "officials")
        self.assertEqual(fragment.entities["_via_wire"], "REUTERS")

    def test_fact_extraction_is_concurrent_and_skips_failed_articles(self) -> None:
        event_id = uuid.uuid4()
        articles = [
            Article(
                id=uuid.uuid4(),
                source_id=uuid.uuid4(),
                external_url=f"https://example.test/{index}",
                title_original=f"Article {index}",
                content_original="Article body",
                language="en",
            )
            for index in range(7)
        ]
        articles[-1].title_original = "bad article"

        class FakeExtractor:
            def __init__(self) -> None:
                self.active = 0
                self.max_active = 0

            async def extract(self, article: Article) -> list[dict]:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                try:
                    await asyncio.sleep(0.01)
                    if article.title_original == "bad article":
                        raise RuntimeError("extract failed")
                    return [
                        {
                            "type": "what",
                            "content": article.title_original,
                            "content_en": article.title_original,
                            "entities": {},
                            "numbers": {},
                            "source_attribution": "unattributed",
                            "certainty_level": "reportedly",
                        }
                    ]
                finally:
                    self.active -= 1

        class FakeEmbedder:
            is_using_fallback = False

            async def embed_text(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0]

        fake_extractor = FakeExtractor()
        with (
            patch(
                "app.services.analyzer.event_analysis_service.FactExtractor",
                return_value=fake_extractor,
            ),
            patch(
                "app.services.analyzer.event_analysis_service.TextEmbedder",
                return_value=FakeEmbedder(),
            ),
        ):
            fragments = asyncio.run(
                EventAnalysisService(None)._extract_fragments(event_id, articles)
            )

        self.assertEqual(len(fragments), 6)
        self.assertGreaterEqual(fake_extractor.max_active, 2)
        self.assertLessEqual(fake_extractor.max_active, 5)


if __name__ == "__main__":
    unittest.main()
