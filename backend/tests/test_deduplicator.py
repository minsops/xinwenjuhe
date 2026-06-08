"""Regression tests for article normalization and duplicate detection."""

from __future__ import annotations

import unittest

from app.services.processor.deduplicator import Deduplicator


class DeduplicatorTest(unittest.TestCase):
    """Cover pure text cleaning and similarity checks."""

    def test_normalize_text_removes_html_and_collapses_space(self) -> None:
        deduplicator = Deduplicator()
        self.assertEqual(deduplicator.normalize_text("<p>Hello&nbsp; “world”</p>"), 'Hello "world"')

    def test_content_duplicate_uses_similarity_threshold(self) -> None:
        deduplicator = Deduplicator()
        self.assertTrue(deduplicator.is_content_duplicate("The same report text", "The same report text"))
        self.assertFalse(deduplicator.is_content_duplicate("Short unrelated text", "Completely different copy"))

    def test_wire_copy_detection_recognizes_common_agencies(self) -> None:
        deduplicator = Deduplicator()
        self.assertEqual(deduplicator.detect_wire_copy("By AP\nThe report follows..."), "AP")
        self.assertEqual(deduplicator.detect_wire_copy("Reuters - Officials said..."), "REUTERS")
        self.assertIsNone(deduplicator.detect_wire_copy("Local staff wrote this report."))


if __name__ == "__main__":
    unittest.main()
