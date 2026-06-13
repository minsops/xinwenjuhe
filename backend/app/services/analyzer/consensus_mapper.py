"""Consensus, dispute, and blind-spot map generation."""

from __future__ import annotations

import json
import math
from uuid import UUID

from app.config import settings
from app.models.contradiction import Contradiction
from app.models.fact_fragment import FactFragment
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.processor.translator import TranslationError, TranslationService


class ConsensusMapper:
    """Generate the right-panel known/disputed/blind-spot analysis map."""

    SIMILARITY_THRESHOLD = 0.85
    SUMMARY_PROMPT = """你是一个中立的新闻编辑。根据以下来自多个不同国家、不同立场媒体的事实碎片，撰写一段事件概要。

规则：
1. 只使用被多个独立来源确认的事实
2. 对于有争议的部分，使用"据部分来源报道"等限定词
3. 不使用任何带有立场倾向的形容词
4. 不做任何因果推断
5. 字数控制在 200 字以内
6. 使用中文撰写

共识事实：
{consensus_json}

争议事实：
{disputed_json}

请输出中立、简洁的事件概要。仅输出摘要文本，不要任何前缀或解释。"""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()

    async def generate_analysis_payload(
        self,
        event_id: UUID,
        fragments: list[FactFragment],
        contradictions: list[Contradiction],
        narrative_frames: list[dict] | None = None,
        article_count_at_analysis: int | None = None,
    ) -> dict:
        independent_source_keys = {self._independent_source_key(fragment) for fragment in fragments}
        analyzed_article_count = article_count_at_analysis
        if analyzed_article_count is None:
            analyzed_article_count = len({fragment.article_id for fragment in fragments})
        total = max(len(independent_source_keys), 1)
        fact_groups = self._semantic_group(fragments)
        consensus = [
            {
                "fact": group["representative"],
                "confirmed_by": len(group["independent_source_keys"]),
                "total": total,
                "source_ids": [str(source_id) for source_id in group["source_ids"]],
                "article_ids": [str(fragment.article_id) for fragment in group["fragments"]],
                "syndicated_count": self._syndicated_count(group["fragments"]),
            }
            for group in fact_groups
            if len(group["independent_source_keys"]) / total >= settings.consensus_threshold
        ]
        disputed = [
            {
                "topic": contradiction.description,
                "type": contradiction.contradiction_type,
                "severity": contradiction.severity,
                "details": contradiction.details,
            }
            for contradiction in contradictions
        ]
        blind_spots = [
            {"description": group["representative"], "mentioned_by": len(group["independent_source_keys"]), "total": total}
            for group in fact_groups
            if len(group["independent_source_keys"]) / total < 0.3
        ]
        summary = await self._generate_summary(consensus, disputed, total)
        timeline = self._timeline(fragments)
        payload = {
            "event_id": event_id,
            "summary": summary,
            "consensus_facts": consensus,
            "disputed_facts": disputed,
            "blind_spots": blind_spots,
            "narrative_frames": narrative_frames or [],
            "source_graph": self._source_graph(fragments, contradictions),
            "timeline": timeline,
            "article_count_at_analysis": analyzed_article_count,
        }
        return await self.localize_payload(payload)

    async def localize_payload(self, payload: dict, include_summary_original: bool = False) -> dict:
        """Translate user-visible analysis fields to Chinese while preserving originals."""
        translator = TranslationService()
        await self._translate_payload_field(
            payload,
            "summary",
            "summary_original",
            translator,
            preserve_original=include_summary_original,
            fallback="这条事件概要暂时没有可用中文翻译。请查看原文。",
        )
        for item in (payload.get("consensus_facts") or [])[:12]:
            await self._translate_item_field(
                item,
                "fact",
                "fact_original",
                translator,
                fallback="这条共识事实暂时没有可用中文翻译。请点击“显示原文”查看原始表述。",
            )
        for item in (payload.get("disputed_facts") or [])[:20]:
            await self._translate_item_field(
                item,
                "topic",
                "topic_original",
                translator,
                fallback="这条争议点暂时没有可用中文翻译。请点击“显示原文”查看原始表述。",
            )
        for item in (payload.get("blind_spots") or [])[:12]:
            await self._translate_item_field(
                item,
                "description",
                "description_original",
                translator,
                fallback=(
                    "这是一条报道盲区线索，但暂时没有可用中文翻译。"
                    "它表示只有少数来源提到、覆盖不足，需要点击“显示原文”继续核验。"
                ),
            )
        for item in (payload.get("timeline") or [])[:8]:
            await self._translate_item_field(
                item,
                "fact",
                "fact_original",
                translator,
                fallback="这条时间轴事实暂时没有可用中文翻译。请点击“显示原文”查看原始表述。",
            )
        return payload

    @classmethod
    async def _translate_payload_field(
        cls,
        payload: dict,
        field: str,
        original_field: str,
        translator: TranslationService,
        preserve_original: bool,
        fallback: str,
    ) -> None:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip() or not cls._needs_chinese_translation(value):
            return
        if preserve_original:
            payload.setdefault(original_field, value)
            payload.setdefault(f"{original_field}_language", "auto")
        try:
            translated, _ = await translator.translate_on_demand(
                value,
                "auto",
                "zh",
                field=f"analysis_{field}",
            )
        except TranslationError:
            translated = fallback
        payload[field] = translated

    @classmethod
    async def _translate_item_field(
        cls,
        item: dict,
        field: str,
        original_field: str,
        translator: TranslationService,
        fallback: str,
    ) -> None:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip() or not cls._needs_chinese_translation(value):
            return
        item.setdefault(original_field, value)
        item.setdefault(f"{original_field}_language", "auto")
        try:
            translated, _ = await translator.translate_on_demand(
                value,
                "auto",
                "zh",
                field=f"analysis_{field}",
            )
        except TranslationError:
            translated = fallback
        item[field] = translated

    @staticmethod
    def _needs_chinese_translation(value: str) -> bool:
        text = value.strip()
        if not text:
            return False
        chinese_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        latin_count = sum(1 for char in text if char.isascii() and char.isalpha())
        kana_count = sum(1 for char in text if "\u3040" <= char <= "\u30ff")
        if kana_count:
            return True
        if chinese_count < 6:
            return True
        return latin_count > chinese_count * 1.5

    def _semantic_group(self, fragments: list[FactFragment]) -> list[dict]:
        """Group fact fragments by embedding similarity instead of exact text."""
        groups: list[dict] = []
        for fragment in fragments:
            if not _has_vector(fragment.embedding):
                continue
            matched = False
            for group in groups:
                if self._cosine(fragment.embedding, group["center"]) >= self.SIMILARITY_THRESHOLD:
                    group["fragments"].append(fragment)
                    group["source_ids"].add(fragment.source_id)
                    group["independent_source_keys"].add(self._independent_source_key(fragment))
                    group["center"] = self._mean_vector(
                        [item.embedding for item in group["fragments"] if _has_vector(item.embedding)]
                    )
                    if len(fragment.content) > len(group["representative"]):
                        group["representative"] = fragment.content
                    matched = True
                    break
            if not matched:
                groups.append(
                    {
                        "representative": fragment.content,
                        "center": fragment.embedding,
                        "fragments": [fragment],
                        "source_ids": {fragment.source_id},
                        "independent_source_keys": {self._independent_source_key(fragment)},
                    }
                )
        return groups

    @staticmethod
    def _independent_source_key(fragment: FactFragment) -> str:
        entities = fragment.entities or {}
        wire_agency = entities.get("_via_wire")
        if isinstance(wire_agency, str) and wire_agency.strip():
            return f"wire:{wire_agency.strip().upper()}"
        return str(fragment.source_id)

    @classmethod
    def _syndicated_count(cls, fragments: list[FactFragment]) -> int:
        wire_counts: dict[str, int] = {}
        for fragment in fragments:
            key = cls._independent_source_key(fragment)
            if key.startswith("wire:"):
                wire_counts[key] = wire_counts.get(key, 0) + 1
        return sum(max(0, count - 1) for count in wire_counts.values())

    async def _generate_summary(self, consensus: list[dict], disputed: list[dict], total: int) -> str:
        """Generate a neutral LLM summary, falling back to deterministic text."""
        try:
            prompt = self.SUMMARY_PROMPT.format(
                consensus_json=json.dumps(consensus[:10], ensure_ascii=False, indent=2),
                disputed_json=json.dumps(disputed[:10], ensure_ascii=False, indent=2),
            )
            summary = (
                await self.llm.complete(
                    "你是一个中立的中文新闻编辑，负责总结跨来源事件事实。",
                    prompt,
                )
            ).strip()
            if len(summary) > 20:
                return summary
        except Exception:
            pass
        return self._fallback_summary(consensus, disputed, total)

    @staticmethod
    def _fallback_summary(consensus: list[dict], disputed: list[dict], total: int) -> str:
        """Return a deterministic summary when no LLM provider is available."""
        if consensus:
            return f"基于 {total} 个来源，目前最稳定的共同事实是：{consensus[0]['fact']}"
        if disputed:
            return f"不同来源对事件仍存在未解决争议：{disputed[0]['topic']}"
        return "目前缺少足够的跨来源证据，暂不能形成稳定事件概要。"

    @staticmethod
    def _cosine(left: list[float] | None, right: list[float] | None) -> float:
        left_values = _vector_values(left)
        right_values = _vector_values(right)
        if not left_values or not right_values or len(left_values) != len(right_values):
            return 0.0
        numerator = sum(a * b for a, b in zip(left_values, right_values, strict=False))
        denominator = math.sqrt(sum(value * value for value in left_values)) * math.sqrt(
            sum(value * value for value in right_values)
        )
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _mean_vector(vectors: list[list[float] | None]) -> list[float]:
        vectors = [list(vector) for vector in vectors if _has_vector(vector)]
        if not vectors:
            return []
        dims = min(len(vector) for vector in vectors)
        return [sum(vector[index] for vector in vectors) / len(vectors) for index in range(dims)]

    @staticmethod
    def _timeline(fragments: list[FactFragment]) -> list[dict]:
        """Build a chronological timeline from timestamped fact fragments."""
        items = []
        for fragment in fragments:
            if not fragment.timestamp_mentioned:
                continue
            items.append(
                {
                    "timestamp": fragment.timestamp_mentioned.isoformat(),
                    "fact": fragment.content,
                    "fragment_type": fragment.fragment_type,
                    "article_id": str(fragment.article_id),
                    "source_id": str(fragment.source_id),
                }
            )
        return sorted(items, key=lambda item: item["timestamp"])

    @staticmethod
    def _source_graph(fragments: list[FactFragment], contradictions: list[Contradiction]) -> dict:
        """Build a lightweight source graph for propagation and conflict views."""
        source_ids = sorted({str(fragment.source_id) for fragment in fragments})
        nodes = [{"id": source_id, "type": "source"} for source_id in source_ids]
        edges = []
        for fragment in fragments:
            edges.append(
                {
                    "from": str(fragment.source_id),
                    "to": str(fragment.article_id),
                    "type": "reported",
                    "fragment_id": str(fragment.id),
                    "fragment_type": fragment.fragment_type,
                }
            )
        for contradiction in contradictions:
            related_sources = [str(source_id) for source_id in contradiction.source_ids]
            for source_id in related_sources:
                edges.append(
                    {
                        "from": source_id,
                        "to": str(contradiction.id),
                        "type": contradiction.contradiction_type,
                        "severity": contradiction.severity,
                    }
                )
            nodes.append(
                {
                    "id": str(contradiction.id),
                    "type": "contradiction",
                    "severity": contradiction.severity,
                }
            )
        return {"nodes": nodes, "edges": edges}


def _has_vector(vector: list[float] | None) -> bool:
    return vector is not None and len(vector) > 0


def _vector_values(vector: list[float] | None) -> list[float]:
    if vector is None:
        return []
    return list(vector)
