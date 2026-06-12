"""Rule and LLM-assisted contradiction detection among fact fragments."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from uuid import UUID

from app.models.contradiction import Contradiction
from app.models.fact_fragment import FactFragment
from app.services.clustering.event_clusterer import EventClusterer


class ContradictionDetector:
    """Detect numeric discrepancies, omissions, and semantic conflicts."""

    COMPARABLE_NUMBER_FIELDS = {"casualties", "injuries", "damage_cost", "distance", "count"}

    async def detect_all_from_fragments(self, event_id: UUID, fragments: list[FactFragment]) -> list[Contradiction]:
        contradictions = []
        contradictions += await self.detect_number_discrepancies(event_id, fragments)
        contradictions += await self.detect_attribution_conflicts(event_id, fragments)
        contradictions += await self.detect_timeline_conflicts(event_id, fragments)
        contradictions += await self.detect_omissions(event_id, fragments)
        contradictions += await self.detect_framing_differences(event_id, fragments)
        return contradictions

    async def detect_number_discrepancies(self, event_id: UUID, fragments: list[FactFragment] | None = None) -> list[Contradiction]:
        fragments = fragments or []
        grouped: dict[str, list[FactFragment]] = defaultdict(list)
        for fragment in fragments:
            if fragment.fragment_type == "number" and fragment.numbers:
                field = fragment.numbers.get("description")
                if field in self.COMPARABLE_NUMBER_FIELDS:
                    grouped[field].append(fragment)

        contradictions: list[Contradiction] = []
        for field, items in grouped.items():
            values = [
                (item, float(item.numbers.get("value")))
                for item in items
                if item.numbers and item.numbers.get("value") is not None
            ]
            if len(values) < 2:
                continue
            raw_values = [value for _, value in values]
            if min(raw_values) <= 0:
                continue
            ratio = max(raw_values) / min(raw_values)
            if ratio > 1.5:
                contradictions.append(
                    Contradiction(
                        event_id=event_id,
                        contradiction_type="number_discrepancy",
                        description=f"不同来源对{_number_field_label(field)}的说法相差约 {ratio:.1f} 倍",
                        severity="critical" if ratio >= 3 else "high",
                        fragment_ids=[item.id for item, _ in values],
                        source_ids=list({item.source_id for item, _ in values}),
                        details={
                            "field": _number_field_label(field),
                            "values": [
                                {
                                    "source_id": str(item.source_id),
                                    "value": value,
                                    "certainty": item.certainty_level,
                                }
                                for item, value in values
                            ],
                        },
                    )
                )
        return contradictions

    async def detect_attribution_conflicts(self, event_id: UUID, fragments: list[FactFragment] | None = None) -> list[Contradiction]:
        """Detect incompatible responsibility or cause attribution across sources."""
        fragments = fragments or []
        candidates = [
            fragment
            for fragment in fragments
            if fragment.fragment_type in {"cause", "consequence", "who"} or _attribution_label(fragment)
        ]
        by_topic = self._group_by_topic_semantic(candidates)

        contradictions: list[Contradiction] = []
        for topic, items in by_topic.items():
            labels: dict[str, list[FactFragment]] = defaultdict(list)
            for item in items:
                label = _attribution_label(item)
                if label:
                    labels[label].append(item)
            if len(labels) < 2:
                continue
            involved = [fragment for group in labels.values() for fragment in group]
            contradictions.append(
                Contradiction(
                    event_id=event_id,
                    contradiction_type="attribution_conflict",
                    description=f"不同来源对“{topic}”的责任归属说法不一致",
                    severity=_severity_for_count(len(labels)),
                    fragment_ids=[fragment.id for fragment in involved],
                    source_ids=list({fragment.source_id for fragment in involved}),
                    details={
                        "topic": topic,
                        "attributions": [
                            {
                                "label": label,
                                "source_ids": [str(fragment.source_id) for fragment in label_items],
                                "fragments": [fragment.content for fragment in label_items],
                            }
                            for label, label_items in labels.items()
                        ],
                    },
                )
            )
        return contradictions

    async def detect_timeline_conflicts(self, event_id: UUID, fragments: list[FactFragment] | None = None) -> list[Contradiction]:
        """Detect materially different timestamps for substantially similar event claims."""
        fragments = [fragment for fragment in fragments or [] if fragment.timestamp_mentioned]
        by_topic = self._group_by_topic_semantic(fragments)

        contradictions: list[Contradiction] = []
        for topic, items in by_topic.items():
            if len({item.source_id for item in items}) < 2:
                continue
            timestamps = [item.timestamp_mentioned for item in items if item.timestamp_mentioned]
            if len(timestamps) < 2:
                continue
            earliest, latest = min(timestamps), max(timestamps)
            delta = latest - earliest
            if delta < timedelta(hours=6):
                continue
            contradictions.append(
                Contradiction(
                    event_id=event_id,
                    contradiction_type="timeline_conflict",
                    description=f"不同来源对“{topic}”的发生时间说法相差 {delta}",
                    severity="high" if delta >= timedelta(days=1) else "medium",
                    fragment_ids=[item.id for item in items],
                    source_ids=list({item.source_id for item in items}),
                    details={
                        "topic": topic,
                        "earliest": earliest.isoformat(),
                        "latest": latest.isoformat(),
                        "reports": [
                            {
                                "source_id": str(item.source_id),
                                "timestamp": item.timestamp_mentioned.isoformat() if item.timestamp_mentioned else None,
                                "content": item.content,
                            }
                            for item in items
                        ],
                    },
                )
            )
        return contradictions

    async def detect_omissions(self, event_id: UUID, fragments: list[FactFragment] | None = None) -> list[Contradiction]:
        fragments = fragments or []
        source_ids = {fragment.source_id for fragment in fragments}
        if len(source_ids) < 3:
            return []
        by_content: dict[str, set[UUID]] = defaultdict(set)
        fragment_ids: dict[str, list[UUID]] = defaultdict(list)
        for fragment in fragments:
            key = fragment.content.lower()[:120]
            by_content[key].add(fragment.source_id)
            fragment_ids[key].append(fragment.id)
        omissions = []
        for key, covered in by_content.items():
            coverage = len(covered) / len(source_ids)
            if coverage >= 0.7 and len(covered) != len(source_ids):
                omissions.append(
                    Contradiction(
                        event_id=event_id,
                        contradiction_type="omission",
                        description=f"有 {len(source_ids - covered)} 个来源没有提到其他来源频繁报道的事实",
                        severity="medium",
                        fragment_ids=fragment_ids[key],
                        source_ids=list(source_ids - covered),
                        details={"coverage": coverage, "fact": key},
                    )
                )
        return omissions

    async def detect_framing_differences(self, event_id: UUID, fragments: list[FactFragment] | None = None) -> list[Contradiction]:
        """Detect sharply different wording for the same actor or action."""
        fragments = fragments or []
        by_topic = self._group_by_topic_semantic(fragments)

        contradictions: list[Contradiction] = []
        for topic, items in by_topic.items():
            labelled = [
                (fragment, label)
                for fragment in items
                if (label := _framing_label(fragment.content))
            ]
            labels = {label for _, label in labelled}
            if len(labels) < 2:
                continue
            items = [fragment for fragment, _ in labelled]
            contradictions.append(
                Contradiction(
                    event_id=event_id,
                    contradiction_type="framing_difference",
                    description=f"不同来源在“{topic}”上使用了不同叙事措辞",
                    severity=_severity_for_count(len(labels), default="low"),
                    fragment_ids=[fragment.id for fragment in items],
                    source_ids=list({fragment.source_id for fragment in items}),
                    details={
                        "topic": topic,
                        "wording": [
                            {
                                "source_id": str(fragment.source_id),
                                "label": label,
                                "content": fragment.content,
                            }
                            for fragment, label in labelled
                        ],
                    },
                )
            )
        return contradictions

    def _group_by_topic_semantic(
        self,
        fragments: list[FactFragment],
        similarity_threshold: float = 0.80,
    ) -> dict[str, list[FactFragment]]:
        """Group by rule-derived topic, then merge groups with similar embeddings."""
        by_topic: dict[str, list[FactFragment]] = defaultdict(list)
        for fragment in fragments:
            by_topic[_topic_key(fragment)].append(fragment)

        keys = list(by_topic.keys())
        merged: dict[str, list[FactFragment]] = {}
        used: set[str] = set()
        for index, key_a in enumerate(keys):
            if key_a in used:
                continue
            group = list(by_topic[key_a])
            for key_b in keys[index + 1 :]:
                if key_b in used:
                    continue
                emb_a = by_topic[key_a][0].embedding
                emb_b = by_topic[key_b][0].embedding
                if _has_vector(emb_a) and _has_vector(emb_b) and EventClusterer.cosine(emb_a, emb_b) > similarity_threshold:
                    group.extend(by_topic[key_b])
                    used.add(key_b)
            merged[key_a] = group
            used.add(key_a)
        return merged


def _topic_key(fragment: FactFragment) -> str:
    entities = fragment.entities or {}
    for key in ("event", "target", "location", "actor"):
        value = entities.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize(value)[:80]
    text = fragment.content_en or fragment.content
    tokens = _normalize(text).split()
    return " ".join(tokens[:8]) or fragment.fragment_type


def _attribution_label(fragment: FactFragment) -> str | None:
    entities = fragment.entities or {}
    for key in ("responsible", "perpetrator", "actor", "cause", "attributed_to"):
        value = entities.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize(value)[:80]

    text = _normalize(fragment.content_en or fragment.content)
    patterns = (
        r"(?:blamed|accused|attributed|caused by|responsibility attributed to)\s+([a-z0-9\s\-]+)",
        r"([a-z0-9\s\-]+)\s+(?:claimed responsibility|was responsible|caused the)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            label = re.sub(r"\b(for|of|in|on|the|a|an)\b.*$", "", match.group(1)).strip()
            if label:
                return label[:80]
    return None


def _framing_label(text: str) -> str | None:
    normalized = _normalize(text)
    term_groups = {
        "解放叙事": ("liberation", "liberated", "freedom fighter"),
        "入侵叙事": ("invasion", "invaded", "occupying force"),
        "军事行动叙事": ("special operation", "security operation", "military operation"),
        "恐怖主义叙事": ("terrorist", "terrorism", "terror attack"),
        "武装组织叙事": ("militant", "armed group", "fighter"),
        "袭击叙事": ("attack", "strike", "assault", "bombardment"),
        "防御叙事": ("defense", "defensive", "retaliation"),
    }
    for label, terms in term_groups.items():
        if any(term in normalized for term in terms):
            return label
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s\-]", " ", value.lower())).strip()


def _severity_for_count(count: int, default: str = "medium") -> str:
    if count >= 4:
        return "critical"
    if count == 3:
        return "high"
    return default


def _number_field_label(field: str) -> str:
    labels = {
        "casualties": "死亡或伤亡人数",
        "injuries": "受伤人数",
        "damage_cost": "损失金额",
        "distance": "距离",
        "count": "数量",
    }
    return labels.get(field, field)


def _has_vector(vector: list[float] | None) -> bool:
    return vector is not None and len(vector) > 0
