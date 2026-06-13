"""Tests for Celery analysis pipeline payload contracts."""

from __future__ import annotations

from importlib.util import find_spec
import unittest
from unittest import mock

HAS_PIPELINE_DEPS = bool(find_spec("celery") and find_spec("sqlalchemy") and find_spec("redis"))

if HAS_PIPELINE_DEPS:
    from app.tasks.analyze_task import _event_id_from_payload, process_event_pipeline


@unittest.skipUnless(HAS_PIPELINE_DEPS, "Celery, Redis, and SQLAlchemy are required for pipeline tests")
class AnalyzeTaskPipelineTest(unittest.TestCase):
    """Validate the current no-group analysis pipeline contract."""

    def test_event_id_from_payload_prefers_standard_dict(self) -> None:
        self.assertEqual(_event_id_from_payload({"event_id": "event-2"}), "event-2")
        self.assertEqual(_event_id_from_payload([{"event_id": "event-3"}]), "")
        self.assertEqual(_event_id_from_payload({"result": {"event_id": "legacy"}}), "")

    def test_process_pipeline_no_longer_uses_group_merge_or_translation_stage(self) -> None:
        names: list[str] = []

        class Step:
            def __init__(self, name: str) -> None:
                self.name = name

            def s(self, *args):
                names.append(self.name)
                return self

        class Workflow:
            def apply_async(self):
                return type("Result", (), {"id": "workflow-id"})()

        with mock.patch("app.tasks.analyze_task._acquire_pipeline_lock", return_value=True), mock.patch(
            "app.tasks.analyze_task.chain", side_effect=lambda *steps: Workflow()
        ), mock.patch("app.tasks.analyze_task.collect_articles_for_event", Step("collect_articles_for_event")), mock.patch(
            "app.tasks.analyze_task.deduplicate_articles", Step("deduplicate_articles")
        ), mock.patch(
            "app.tasks.analyze_task.extract_facts", Step("extract_facts")
        ), mock.patch(
            "app.tasks.analyze_task.detect_contradictions", Step("detect_contradictions")
        ), mock.patch(
            "app.tasks.analyze_task.analyze_narratives", Step("analyze_narratives")
        ), mock.patch(
            "app.tasks.analyze_task.generate_consensus_map", Step("generate_consensus_map")
        ), mock.patch(
            "app.tasks.analyze_task.notify_clients", Step("notify_clients")
        ):
            self.assertEqual(process_event_pipeline("event-1"), "workflow-id")

        self.assertEqual(
            names,
            [
                "collect_articles_for_event",
                "deduplicate_articles",
                "extract_facts",
                "detect_contradictions",
                "analyze_narratives",
                "generate_consensus_map",
                "notify_clients",
            ],
        )
        self.assertNotIn("translate_articles", names)
        self.assertNotIn("merge_group_results", names)


if __name__ == "__main__":
    unittest.main()
