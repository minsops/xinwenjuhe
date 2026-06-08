"""Unit tests for stable cursor pagination helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib.util import find_spec
from types import SimpleNamespace
from uuid import uuid4
import unittest

if not find_spec("fastapi"):
    raise unittest.SkipTest("FastAPI dependencies are not installed")

from app.core.errors import ApiError
from app.api.v1.events import _article_cursor, _decode_cursor, _event_cursor
from app.api.v1.sources import (
    _decode_cursor as _decode_source_cursor,
    _parse_cursor_datetime,
    _source_cursor,
)


class CursorPaginationTest(unittest.TestCase):
    """Ensure list cursors include the endpoint sort keys, not only row IDs."""

    def test_event_heat_cursor_encodes_sort_keys(self) -> None:
        event = SimpleNamespace(
            id=uuid4(),
            heat_score=87.5,
            created_at=datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc),
            last_updated_at=datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc),
        )

        payload = _decode_cursor(_event_cursor(event, "heat"), "events:heat")

        self.assertEqual(payload["kind"], "events:heat")
        self.assertEqual(payload["heat_score"], 87.5)
        self.assertEqual(payload["created_at"], "2026-06-01T08:30:00+00:00")
        self.assertEqual(payload["id"], str(event.id))

    def test_article_cursor_encodes_published_and_created_tiebreakers(self) -> None:
        article = SimpleNamespace(
            id=uuid4(),
            published_at=datetime(2026, 6, 1, 7, 30, tzinfo=timezone.utc),
            created_at=datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc),
        )

        payload = _decode_cursor(_article_cursor(article), "event_articles")

        self.assertEqual(payload["kind"], "event_articles")
        self.assertEqual(payload["published_at"], "2026-06-01T07:30:00+00:00")
        self.assertEqual(payload["created_at"], "2026-06-01T08:30:00+00:00")
        self.assertEqual(payload["id"], str(article.id))

    def test_bare_uuid_cursor_is_rejected(self) -> None:
        with self.assertRaises(ApiError):
            _decode_cursor(str(uuid4()), "events:heat")

    def test_source_cursor_encodes_sort_keys(self) -> None:
        source = SimpleNamespace(id=uuid4(), region="europe", name="Reuters")

        payload = _decode_source_cursor(_source_cursor(source), "sources")

        self.assertEqual(payload["kind"], "sources")
        self.assertEqual(payload["region"], "europe")
        self.assertEqual(payload["name"], "Reuters")
        self.assertEqual(payload["id"], str(source.id))

    def test_malformed_cursor_datetime_is_rejected(self) -> None:
        with self.assertRaises(ApiError):
            _parse_cursor_datetime("not-a-date")


if __name__ == "__main__":
    unittest.main()
