"""Tests for generic JSON API collector helpers."""

from __future__ import annotations

import unittest
from importlib.util import find_spec

if not find_spec("httpx") or not find_spec("tenacity"):
    raise unittest.SkipTest("httpx and tenacity are required for API collector tests")

from app.services.collector.api_collector import APICollector


class APICollectorTest(unittest.TestCase):
    """Validate JSON path extraction and date parsing without network calls."""

    def test_value_reads_nested_dict_and_list_paths(self) -> None:
        payload = {"data": {"articles": [{"title": "first"}, {"title": "second"}]}}

        self.assertEqual(APICollector._value(payload, "data.articles.1.title"), "second")
        self.assertIsNone(APICollector._value(payload, "data.articles.9.title"))

    def test_parse_date_accepts_iso_and_rfc822(self) -> None:
        iso = APICollector._parse_date("2026-06-02T12:30:00Z")
        rfc = APICollector._parse_date("Tue, 02 Jun 2026 12:30:00 GMT")

        self.assertEqual(iso.year if iso else None, 2026)
        self.assertEqual(rfc.year if rfc else None, 2026)
        self.assertIsNotNone(iso.tzinfo if iso else None)
        self.assertIsNotNone(rfc.tzinfo if rfc else None)


if __name__ == "__main__":
    unittest.main()
