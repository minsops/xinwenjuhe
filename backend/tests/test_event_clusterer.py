"""Tests for semantic event clustering behavior."""

from __future__ import annotations

import asyncio
import importlib.util
from types import SimpleNamespace
import unittest

if not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for clustering tests")

from app.services.clustering.event_clusterer import EventClusterer


class EventClustererTest(unittest.TestCase):
    """Validate new-article clustering does not merge unrelated roots."""

    def test_new_articles_form_separate_similarity_clusters(self) -> None:
        articles = [
            SimpleNamespace(embedding=[1.0, 0.0], title_original="a", content_original="a", content_translated=None),
            SimpleNamespace(embedding=[0.99, 0.01], title_original="b", content_original="b", content_translated=None),
            SimpleNamespace(embedding=[0.0, 1.0], title_original="c", content_original="c", content_translated=None),
        ]

        clusters = asyncio.run(EventClusterer().cluster_new_articles(articles))
        sizes = sorted(len(grouped) for grouped in clusters.values())

        self.assertEqual(sizes, [1, 2])


if __name__ == "__main__":
    unittest.main()
