"""Evaluate contradiction detection against a hand-labeled JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.metrics import contradiction_precision_recall


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path, help="JSON object with gold and predicted contradiction lists")
    args = parser.parse_args()
    payload = json.loads(args.labels.read_text(encoding="utf-8"))
    print(json.dumps(contradiction_precision_recall(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
