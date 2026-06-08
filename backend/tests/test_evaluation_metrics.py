"""Regression tests for offline evaluation metrics."""

from __future__ import annotations

import unittest

from app.evaluation.metrics import contradiction_precision_recall, pairwise_clustering_f1


class EvaluationMetricsTest(unittest.TestCase):
    """Validate the custom metrics named in the project test strategy."""

    def test_pairwise_clustering_f1(self) -> None:
        rows = [
            {"article_id": "a1", "gold_event_id": "g1", "predicted_event_id": "p1"},
            {"article_id": "a2", "gold_event_id": "g1", "predicted_event_id": "p1"},
            {"article_id": "a3", "gold_event_id": "g2", "predicted_event_id": "p1"},
            {"article_id": "a4", "gold_event_id": "g2", "predicted_event_id": "p2"},
        ]

        metrics = pairwise_clustering_f1(rows)

        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["predicted"], 3)
        self.assertEqual(metrics["gold"], 2)
        self.assertEqual(metrics["precision"], 0.3333)
        self.assertEqual(metrics["recall"], 0.5)

    def test_contradiction_precision_recall(self) -> None:
        payload = {
            "gold": [
                {"contradiction_type": "number_discrepancy", "fragment_ids": ["f1", "f2"]},
                {"contradiction_type": "omission", "fragment_ids": ["f3"]},
            ],
            "predicted": [
                {"contradiction_type": "number_discrepancy", "fragment_ids": ["f2", "f1"]},
                {"contradiction_type": "timeline_conflict", "fragment_ids": ["f4", "f5"]},
            ],
        }

        metrics = contradiction_precision_recall(payload)

        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["f1"], 0.5)


if __name__ == "__main__":
    unittest.main()
