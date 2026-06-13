"""Tests for semantic consensus grouping and LLM summary fallback."""

from __future__ import annotations

import asyncio
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

if not importlib.util.find_spec("sqlalchemy"):
    raise unittest.SkipTest("SQLAlchemy is required for consensus tests")

from app.models.fact_fragment import FactFragment
from app.services.analyzer.consensus_mapper import ConsensusMapper
from app.services.llm.base import LLMProvider


class SummaryLLM(LLMProvider):
    """Test double that returns a readable summary."""

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return "Two independent sources report a strike on the military base while details remain limited."


class EmptyLLM(LLMProvider):
    """Test double that forces fallback summary generation."""

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return "{}"


class ConsensusSemanticTest(unittest.TestCase):
    """Validate semantic fact grouping behavior."""

    def test_semantically_similar_fragments_are_grouped(self) -> None:
        event_id = uuid.uuid4()
        fragments = [
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "The strike targeted the air base", [1.0, 0.0, 0.0]),
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "Military base was hit by missiles", [0.96, 0.04, 0.0]),
        ]

        payload = asyncio.run(
            ConsensusMapper(llm=EmptyLLM()).generate_analysis_payload(event_id, fragments, [])
        )

        self.assertEqual(len(payload["consensus_facts"]), 1)
        self.assertEqual(payload["consensus_facts"][0]["confirmed_by"], 2)
        self.assertEqual(len(payload["consensus_facts"][0]["article_ids"]), 2)
        self.assertEqual(payload["consensus_facts"][0]["fact_original"], "Military base was hit by missiles")
        self.assertEqual(payload["consensus_facts"][0]["fact_original_language"], "en")

    def test_dissimilar_fragments_stay_separate(self) -> None:
        event_id = uuid.uuid4()
        fragments = [
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "The strike targeted the air base", [1.0, 0.0, 0.0]),
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "Oil prices surged after the incident", [0.0, 1.0, 0.0]),
        ]

        groups = ConsensusMapper(llm=EmptyLLM())._semantic_group(fragments)

        self.assertEqual(len(groups), 2)

    def test_fragments_without_embedding_are_skipped(self) -> None:
        event_id = uuid.uuid4()
        fragments = [
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "No vector", None),
            _fragment(event_id, uuid.uuid4(), uuid.uuid4(), "Vector fact", [1.0, 0.0, 0.0]),
        ]

        groups = ConsensusMapper(llm=EmptyLLM())._semantic_group(fragments)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["representative"], "Vector fact")

    def test_llm_summary_is_used_when_valid(self) -> None:
        summary = asyncio.run(
            ConsensusMapper(llm=SummaryLLM())._generate_summary(
                [{"fact": "The base was struck", "confirmed_by": 2, "total": 2}],
                [],
                2,
            )
        )

        self.assertIn("independent sources", summary)

    def test_summary_falls_back_when_llm_is_empty(self) -> None:
        summary = asyncio.run(
            ConsensusMapper(llm=EmptyLLM())._generate_summary(
                [{"fact": "The base was struck", "confirmed_by": 2, "total": 2}],
                [],
                2,
            )
        )

        self.assertTrue(summary.startswith("基于 2 个来源"))

    def test_localize_payload_preserves_english_summary_original_for_api(self) -> None:
        payload = {
            "summary": "Two independent sources report a strike while details remain limited.",
            "consensus_facts": [],
            "disputed_facts": [],
            "blind_spots": [],
            "timeline": [],
        }

        localized = asyncio.run(
            ConsensusMapper(llm=EmptyLLM()).localize_payload(payload, include_summary_original=True)
        )

        self.assertNotEqual(localized["summary"], localized["summary_original"])
        self.assertGreaterEqual(_cjk_count(localized["summary"]), 6)
        self.assertEqual(localized["summary_original"], "Two independent sources report a strike while details remain limited.")
        self.assertEqual(localized["summary_original_language"], "en")

    def test_localize_payload_explains_blind_spot_translation_fallback(self) -> None:
        payload = {
            "summary": "中文概要",
            "consensus_facts": [],
            "disputed_facts": [],
            "blind_spots": [
                {
                    "description": "Only one regional outlet reported damage near the port.",
                    "mentioned_by": 1,
                    "total": 5,
                }
            ],
            "timeline": [],
        }

        async def fail_translation(*args, **kwargs):
            from app.services.processor.translator import TranslationError

            raise TranslationError("翻译服务返回了原文")

        with patch("app.services.processor.translator.TranslationService.translate_on_demand", fail_translation):
            localized = asyncio.run(ConsensusMapper(llm=EmptyLLM()).localize_payload(payload))

        blind_spot = localized["blind_spots"][0]
        self.assertIn("报道盲区", blind_spot["description"])
        self.assertIn("覆盖不足", blind_spot["description"])
        self.assertEqual(blind_spot["description_original"], "Only one regional outlet reported damage near the port.")
        self.assertEqual(blind_spot["description_original_language"], "en")

    def test_guess_language_labels_common_original_scripts(self) -> None:
        mapper = ConsensusMapper(llm=EmptyLLM())

        self.assertEqual(mapper._guess_language("Military base was hit by missiles"), "en")
        self.assertEqual(mapper._guess_language("Военные сообщили о новых ударах"), "ru")
        self.assertEqual(mapper._guess_language("政府は新たな調査を発表した"), "ja")

    def test_wire_reposts_count_as_one_independent_source(self) -> None:
        event_id = uuid.uuid4()
        wire_sources = [uuid.uuid4() for _ in range(4)]
        independent_sources = [uuid.uuid4(), uuid.uuid4()]
        fragments = [
            _fragment(
                event_id,
                uuid.uuid4(),
                source_id,
                "Reuters reported 12 casualties after the crash",
                [1.0, 0.0, 0.0],
                entities={"_via_wire": "REUTERS"},
            )
            for source_id in wire_sources
        ]
        fragments.extend(
            _fragment(
                event_id,
                uuid.uuid4(),
                source_id,
                "Officials reported 12 casualties after the crash",
                [0.99, 0.01, 0.0],
            )
            for source_id in independent_sources
        )

        payload = asyncio.run(
            ConsensusMapper(llm=EmptyLLM()).generate_analysis_payload(event_id, fragments, [])
        )

        self.assertEqual(payload["consensus_facts"][0]["confirmed_by"], 3)
        self.assertEqual(payload["consensus_facts"][0]["total"], 3)
        self.assertEqual(payload["consensus_facts"][0]["syndicated_count"], 3)
        self.assertEqual(len(payload["consensus_facts"][0]["source_ids"]), 6)


def _fragment(
    event_id: uuid.UUID,
    article_id: uuid.UUID,
    source_id: uuid.UUID,
    content: str,
    embedding: list[float] | None,
    entities: dict | None = None,
) -> FactFragment:
    return FactFragment(
        id=uuid.uuid4(),
        event_id=event_id,
        article_id=article_id,
        source_id=source_id,
        fragment_type="what",
        content=content,
        content_en=content,
        entities=entities or {},
        numbers={},
        source_attribution="official_statement",
        certainty_level="confirmed",
        embedding=embedding,
    )


def _cjk_count(value: str) -> int:
    return sum(1 for char in value if "\u4e00" <= char <= "\u9fff")


if __name__ == "__main__":
    unittest.main()
