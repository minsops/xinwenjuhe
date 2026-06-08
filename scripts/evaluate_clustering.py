"""Evaluate event clustering against a hand-labeled JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.metrics import pairwise_clustering_f1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path, help="JSON list with article_id, gold_event_id, predicted_event_id")
    args = parser.parse_args()
    rows = json.loads(args.labels.read_text(encoding="utf-8"))
    print(json.dumps(pairwise_clustering_f1(rows), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
