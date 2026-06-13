"""Tests for analyzer output validation and analysis metadata."""

from __future__ import annotations

import asyncio
import importlib.util
from types import SimpleNamespace
import unittest
import uuid

if not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for analyzer validation tests")

from app.models.fact_fragment import FactFragment
from app.services.analyzer.consensus_mapper import ConsensusMapper
from app.services.analyzer.fact_extractor import FactExtractor
from app.services.analyzer.narrative_analyzer import NarrativeAnalyzer


class AnalyzerValidationTest(unittest.TestCase):
    """Validate schema cleanup before analyzer output reaches persistence/UI."""

    def test_fact_extractor_drops_invalid_rows_and_normalizes_defaults(self) -> None:
        extractor = FactExtractor()

        rows = extractor._validate_fragments(
            [
                {"type": "invalid", "content": " Officials confirmed 12 injuries. ", "entities": [], "numbers": []},
                {"type": "invalid", "content": " 官方确认有12人受伤。 ", "content_en": "Officials confirmed 12 injuries.", "entities": [], "numbers": []},
                {"type": "number", "content": ""},
                "not-a-dict",
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["type"], "what")
        self.assertEqual(rows[0]["content"], "官方确认有12人受伤。")
        self.assertEqual(rows[0]["entities"], {})
        self.assertEqual(rows[0]["numbers"], {})
        self.assertEqual(rows[0]["source_attribution"], "unattributed")

    def test_narrative_frame_output_is_normalized(self) -> None:
        article = SimpleNamespace(id=uuid.uuid4(), source_id=uuid.uuid4())

        frame = NarrativeAnalyzer._validate_frame({"frames": "security", "emphasis": "official claims"}, article)

        self.assertEqual(frame["article_id"], str(article.id))
        self.assertEqual(frame["source_id"], str(article.source_id))
        self.assertEqual(frame["frames"], ["安全事件"])
        self.assertEqual(frame["emphasis"], ["official claims"])
        self.assertEqual(frame["tone"], "中性")

    def test_non_chinese_fact_content_is_rejected_for_analysis_display(self) -> None:
        extractor = FactExtractor()

        rows = extractor._validate_fragments(
            [{"type": "what", "content": "Officials confirmed the incident.", "content_en": "Officials confirmed the incident."}],
            language="en",
        )

        self.assertEqual(rows, [])

    def test_content_en_is_required_even_when_display_content_is_chinese(self) -> None:
        extractor = FactExtractor()

        rows = extractor._validate_fragments(
            [{"type": "what", "content": "官方确认事件已经发生。"}],
            language="en",
        )

        self.assertEqual(rows, [])

    def test_consensus_payload_records_article_count_not_source_count(self) -> None:
        event_id = uuid.uuid4()
        source_id = uuid.uuid4()
        fragments = [
            _fragment(event_id, uuid.uuid4(), source_id, "Shared fact"),
            _fragment(event_id, uuid.uuid4(), source_id, "Shared fact"),
        ]

        payload = asyncio.run(ConsensusMapper().generate_analysis_payload(event_id, fragments, []))

        self.assertEqual(payload["article_count_at_analysis"], 2)


def _fragment(event_id: uuid.UUID, article_id: uuid.UUID, source_id: uuid.UUID, content: str) -> FactFragment:
    return FactFragment(
        id=uuid.uuid4(),
        event_id=event_id,
        article_id=article_id,
        source_id=source_id,
        fragment_type="what",
        content=content,
        content_en=content,
        entities={},
        numbers={},
        source_attribution="official_statement",
        certainty_level="confirmed",
    )


if __name__ == "__main__":
    unittest.main()
