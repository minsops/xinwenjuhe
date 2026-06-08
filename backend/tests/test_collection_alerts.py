"""Tests for collection failure deactivation and alert retention."""

from __future__ import annotations

from importlib.util import find_spec
from types import SimpleNamespace
import unittest
from unittest.mock import patch

if not find_spec("redis") or not find_spec("sqlalchemy"):
    raise unittest.SkipTest("backend runtime dependencies are not installed")

from app.services.collector.source_registry import update_collection_failure, update_collection_success
from app.tasks import progress


class CollectionAlertsTest(unittest.TestCase):
    """Validate source deactivation threshold and operator alert recording."""

    def test_three_collection_failures_deactivate_source(self) -> None:
        source = SimpleNamespace(consecutive_failures=0, is_active=True)

        self.assertFalse(update_collection_failure(source))
        self.assertFalse(update_collection_failure(source))
        self.assertTrue(update_collection_failure(source))

        self.assertEqual(source.consecutive_failures, 3)
        self.assertFalse(source.is_active)
        update_collection_success(source)
        self.assertEqual(source.consecutive_failures, 0)

    def test_source_alerts_are_retained_in_memory_fallback(self) -> None:
        progress._memory_source_alerts.clear()

        with patch("app.tasks.progress.Redis.from_url", side_effect=RuntimeError("redis down")):
            progress.record_source_alert(
                "source-1",
                "Example Source",
                "collection_failure_threshold",
                {"consecutive_failures": 3},
            )
            alerts = progress.list_source_alerts(limit=5)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["source_id"], "source-1")
        self.assertEqual(alerts[0]["reason"], "collection_failure_threshold")


if __name__ == "__main__":
    unittest.main()
