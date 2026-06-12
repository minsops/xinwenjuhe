"""Unit tests for the five documented contradiction detectors."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
import unittest
import uuid

if not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for ORM-backed detector tests")

from app.models.fact_fragment import FactFragment
from app.services.analyzer.contradiction_detector import ContradictionDetector


class ContradictionDetectorTest(unittest.TestCase):
    """Exercise numeric, attribution, timeline, omission, and framing detectors."""

    def test_detect_all_covers_documented_contradiction_types(self) -> None:
        event_id = uuid.uuid4()
        source_a, source_b, source_c, source_d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        article_a, article_b, article_c, article_d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        base_time = datetime(2026, 6, 2, 9, tzinfo=timezone.utc)
        fragments = [
            _fragment(event_id, article_a, source_a, "number", "casualties reported at 10", numbers={"description": "casualties", "value": 10}),
            _fragment(event_id, article_b, source_b, "number", "casualties reported at 80", numbers={"description": "casualties", "value": 80}),
            _fragment(event_id, article_a, source_a, "cause", "Officials blamed Alpha Brigade for the blast", entities={"event": "harbor blast", "responsible": "Alpha Brigade"}),
            _fragment(event_id, article_b, source_b, "cause", "Officials blamed Beta Cell for the blast", entities={"event": "harbor blast", "responsible": "Beta Cell"}),
            _fragment(event_id, article_a, source_a, "when", "The blast happened at dawn", entities={"event": "harbor blast"}, timestamp=base_time),
            _fragment(event_id, article_b, source_b, "when", "The blast happened late evening", entities={"event": "harbor blast"}, timestamp=base_time + timedelta(hours=10)),
            _fragment(event_id, article_a, source_a, "what", "Authorities evacuated the harbor district", entities={"event": "evacuation"}),
            _fragment(event_id, article_b, source_b, "what", "Authorities evacuated the harbor district", entities={"event": "evacuation"}),
            _fragment(event_id, article_c, source_c, "what", "Authorities evacuated the harbor district", entities={"event": "evacuation"}),
            _fragment(event_id, article_a, source_a, "what", "The group called it a liberation of the city", entities={"event": "city operation"}),
            _fragment(event_id, article_b, source_b, "what", "The mayor described it as an invasion of the city", entities={"event": "city operation"}),
            _fragment(event_id, article_d, source_d, "what", "A fourth source covered adjacent facts", entities={"event": "other"}),
        ]

        contradictions = asyncio.run(ContradictionDetector().detect_all_from_fragments(event_id, fragments))
        types = {item.contradiction_type for item in contradictions}

        self.assertIn("number_discrepancy", types)
        self.assertIn("attribution_conflict", types)
        self.assertIn("timeline_conflict", types)
        self.assertIn("omission", types)
        self.assertIn("framing_difference", types)
        self.assertTrue(all(item.fragment_ids for item in contradictions))
        self.assertTrue(all(item.source_ids for item in contradictions))

    def test_semantic_topic_grouping_merges_different_rule_keys(self) -> None:
        event_id = uuid.uuid4()
        fragments = [
            _fragment(
                event_id,
                uuid.uuid4(),
                uuid.uuid4(),
                "cause",
                "Officials blamed Alpha Brigade for the air base strike",
                entities={"event": "air base strike", "responsible": "Alpha Brigade"},
                embedding=[1.0, 0.0, 0.0],
            ),
            _fragment(
                event_id,
                uuid.uuid4(),
                uuid.uuid4(),
                "cause",
                "Authorities accused Beta Cell over the missile hit on the base",
                entities={"target": "missile hit base", "responsible": "Beta Cell"},
                embedding=[0.97, 0.03, 0.0],
            ),
        ]

        contradictions = asyncio.run(ContradictionDetector().detect_attribution_conflicts(event_id, fragments))

        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0].contradiction_type, "attribution_conflict")
        self.assertEqual(len(contradictions[0].fragment_ids), 2)

    def test_reported_number_fragments_do_not_create_fake_discrepancies(self) -> None:
        event_id = uuid.uuid4()
        fragments = [
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "number", "2026", numbers={"description": "reported_number", "value": 2026}),
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "number", "12", numbers={"description": "reported_number", "value": 12}),
        ]

        contradictions = asyncio.run(ContradictionDetector().detect_number_discrepancies(event_id, fragments))

        self.assertEqual(contradictions, [])


def _fragment(
    event_id: uuid.UUID,
    article_id: uuid.UUID,
    source_id: uuid.UUID,
    fragment_type: str,
    content: str,
    *,
    entities: dict | None = None,
    numbers: dict | None = None,
    timestamp: datetime | None = None,
    embedding: list[float] | None = None,
) -> FactFragment:
    return FactFragment(
        id=uuid.uuid4(),
        event_id=event_id,
        article_id=article_id,
        source_id=source_id,
        fragment_type=fragment_type,
        content=content,
        content_en=content,
        entities=entities or {},
        numbers=numbers or {},
        source_attribution="official_statement",
        certainty_level="reported",
        timestamp_mentioned=timestamp,
        embedding=embedding,
    )


if __name__ == "__main__":
    unittest.main()
