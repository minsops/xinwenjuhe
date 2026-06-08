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
6. 使用英文撰写

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
        source_ids = {fragment.source_id for fragment in fragments}
        analyzed_article_count = article_count_at_analysis
        if analyzed_article_count is None:
            analyzed_article_count = len({fragment.article_id for fragment in fragments})
        total = max(len(source_ids), 1)
        fact_groups = self._semantic_group(fragments)
        consensus = [
            {
                "fact": group["representative"],
                "confirmed_by": len(group["source_ids"]),
                "total": total,
                "source_ids": [str(source_id) for source_id in group["source_ids"]],
                "article_ids": [str(fragment.article_id) for fragment in group["fragments"]],
            }
            for group in fact_groups
            if len(group["source_ids"]) / total >= settings.consensus_threshold
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
            {"description": group["representative"], "mentioned_by": len(group["source_ids"]), "total": total}
            for group in fact_groups
            if len(group["source_ids"]) / total < 0.3
        ]
        summary = await self._generate_summary(consensus, disputed, total)
        return {
            "event_id": event_id,
            "summary": summary,
            "consensus_facts": consensus,
            "disputed_facts": disputed,
            "blind_spots": blind_spots,
            "narrative_frames": narrative_frames or [],
            "source_graph": self._source_graph(fragments, contradictions),
            "timeline": self._timeline(fragments),
            "article_count_at_analysis": analyzed_article_count,
        }

    def _semantic_group(self, fragments: list[FactFragment]) -> list[dict]:
        """Group fact fragments by embedding similarity instead of exact text."""
        groups: list[dict] = []
        for fragment in fragments:
            if not fragment.embedding:
                continue
            matched = False
            for group in groups:
                if self._cosine(fragment.embedding, group["center"]) >= self.SIMILARITY_THRESHOLD:
                    group["fragments"].append(fragment)
                    group["source_ids"].add(fragment.source_id)
                    group["center"] = self._mean_vector(
                        [item.embedding for item in group["fragments"] if item.embedding]
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
                    }
                )
        return groups

    async def _generate_summary(self, consensus: list[dict], disputed: list[dict], total: int) -> str:
        """Generate a neutral LLM summary, falling back to deterministic text."""
        try:
            prompt = self.SUMMARY_PROMPT.format(
                consensus_json=json.dumps(consensus[:10], ensure_ascii=False, indent=2),
                disputed_json=json.dumps(disputed[:10], ensure_ascii=False, indent=2),
            )
            summary = (
                await self.llm.complete(
                    "You are a neutral news editor summarizing cross-source event facts.",
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
            return f"Based on {total} source(s), the strongest common fact is: {consensus[0]['fact']}"
        if disputed:
            return f"Sources describe the event with unresolved dispute: {disputed[0]['topic']}"
        return "Insufficient cross-source evidence is available for a stable event summary."

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
            sum(value * value for value in right)
        )
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _mean_vector(vectors: list[list[float]]) -> list[float]:
        vectors = [vector for vector in vectors if vector]
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
