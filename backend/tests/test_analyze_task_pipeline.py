"""Tests for Celery analysis pipeline payload normalization."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if not find_spec("celery") or not find_spec("sqlalchemy"):
    raise unittest.SkipTest("Celery and SQLAlchemy are required for pipeline tests")

from app.tasks.analyze_task import _event_id_from_payload, merge_group_results


class AnalyzeTaskPipelineTest(unittest.TestCase):
    """Validate group result merging and event id extraction."""

    def test_merge_group_results_combines_dicts_and_nested_lists(self) -> None:
        result = merge_group_results.run(
            [
                {"event_id": "event-1", "translated": 2},
                [{"deduplicated": True, "duplicates": 1}],
            ]
        )

        self.assertEqual(result["event_id"], "event-1")
        self.assertEqual(result["translated"], 2)
        self.assertTrue(result["deduplicated"])
        self.assertEqual(result["duplicates"], 1)

    def test_event_id_from_payload_prefers_standard_dict(self) -> None:
        self.assertEqual(_event_id_from_payload({"event_id": "event-2"}), "event-2")
        self.assertEqual(_event_id_from_payload([{"event_id": "event-3"}]), "event-3")
        self.assertEqual(_event_id_from_payload({"result": {"event_id": "legacy"}}), "")


if __name__ == "__main__":
    unittest.main()
