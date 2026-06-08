"""Small metric helpers for offline TruthPuzzle evaluation sets."""

from __future__ import annotations

from itertools import combinations
from typing import Any


def _prf(true_positives: int, predicted: int, gold: int) -> dict[str, float | int]:
    precision = true_positives / predicted if predicted else 0.0
    recall = true_positives / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": true_positives,
        "predicted": predicted,
        "gold": gold,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def pairwise_clustering_f1(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    """Compute pairwise clustering precision/recall/F1 from article event labels."""
    gold_pairs: set[tuple[str, str]] = set()
    predicted_pairs: set[tuple[str, str]] = set()
    for left, right in combinations(rows, 2):
        pair = tuple(sorted((str(left["article_id"]), str(right["article_id"]))))
        if left["gold_event_id"] == right["gold_event_id"]:
            gold_pairs.add(pair)
        if left["predicted_event_id"] == right["predicted_event_id"]:
            predicted_pairs.add(pair)
    return _prf(len(gold_pairs & predicted_pairs), len(predicted_pairs), len(gold_pairs))


def contradiction_precision_recall(payload: dict[str, list[dict[str, Any]]]) -> dict[str, float | int]:
    """Compute exact-match contradiction detection metrics by type and fragment set."""
    gold = {_contradiction_key(item) for item in payload.get("gold", [])}
    predicted = {_contradiction_key(item) for item in payload.get("predicted", [])}
    return _prf(len(gold & predicted), len(predicted), len(gold))


def _contradiction_key(item: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    fragment_ids = tuple(sorted(str(fragment_id) for fragment_id in item.get("fragment_ids", [])))
    return str(item["contradiction_type"]), fragment_ids
