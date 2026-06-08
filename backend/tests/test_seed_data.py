"""Regression tests for source seed coverage requirements."""

from __future__ import annotations

import collections
import json
from pathlib import Path
import unittest


class SeedDataTest(unittest.TestCase):
    """Validate the documented source coverage floor."""

    def test_sources_cover_required_regions(self) -> None:
        rows = json.loads(Path("data/seed/sources.json").read_text(encoding="utf-8"))
        by_region = collections.Counter(row["region"] for row in rows)

        self.assertGreaterEqual(len(rows), 50)
        self.assertGreaterEqual(len(by_region), 7)
        self.assertTrue(all(count >= 5 for count in by_region.values()), by_region)

    def test_required_source_fields_exist(self) -> None:
        rows = json.loads(Path("data/seed/sources.json").read_text(encoding="utf-8"))
        required = {"name", "country", "region", "language", "feed_type", "feed_url"}
        scraper_required = {
            "list_url",
            "article_selector",
            "title_selector",
            "content_selector",
            "requires_js",
        }
        for row in rows:
            self.assertTrue(required.issubset(row), row)
            if row["feed_type"] == "rss":
                self.assertTrue(row.get("feed_url"), row["name"])
            if row["feed_type"] == "scraper":
                config = row.get("scraper_config") or {}
                self.assertTrue(scraper_required.issubset(config), row["name"])
                self.assertIsInstance(config["requires_js"], bool, row["name"])


if __name__ == "__main__":
    unittest.main()
