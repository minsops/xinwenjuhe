"""Regression tests for the documented workflow fixes."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest
import uuid

if not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for workflow tests")

from app.models.article import Article
from app.services.analyzer.event_analysis_service import EventAnalysisService
from app.services.analyzer.fact_extractor import FactExtractor
from app.tasks.worker_db import worker_session


TEST_DIR = Path(__file__).resolve().parent
HOST_ROOT = TEST_DIR.parents[1]
CONTAINER_ROOT = TEST_DIR.parent
ROOT = HOST_ROOT if (HOST_ROOT / "backend").exists() else CONTAINER_ROOT
BACKEND_ROOT = ROOT / "backend" if (ROOT / "backend").exists() else ROOT


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

    def test_fallback_extracts_only_casualty_context_and_not_year(self) -> None:
        article = Article(
            id=uuid.uuid4(),
            source_id=uuid.uuid4(),
            external_url="https://example.test/a",
            title_original="事故通报",
            content_original="2026年6月，事故造成12人死亡。",
            language="zh-CN",
        )

        fragments = FactExtractor()._fallback_extract(article)

        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0]["numbers"]["description"], "casualties")
        self.assertEqual(fragments[0]["numbers"]["value"], 12)

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


if __name__ == "__main__":
    unittest.main()
