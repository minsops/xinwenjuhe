"""LLM-backed fact fragment extraction from news articles."""

from __future__ import annotations

import json
import re

from app.models.article import Article
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider


class FactExtractor:
    """Extract independently verifiable fact claims from article text."""

    EXTRACTION_PROMPT = """
你是一个专业的新闻事实核查分析师。请从以下新闻报道中提取所有可独立验证的事实声明。

字段：
- type: what/who/where/when/number/cause/consequence
- content: 事实声明的完整内容
- entities: 涉及的实体
- numbers: 涉及的量化数据
- source_attribution: firsthand/official_statement/anonymous/cited_media/unattributed
- certainty_level: confirmed/alleged/reportedly/unverified

只输出 JSON 数组。
"""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.allowed_types = {"what", "who", "where", "when", "number", "cause", "consequence"}
        self.allowed_attribution = {"firsthand", "official_statement", "anonymous", "cited_media", "unattributed"}
        self.allowed_certainty = {"confirmed", "alleged", "reportedly", "unverified"}

    async def extract(self, article: Article) -> list[dict]:
        text = article.content_translated or article.content_original
        prompt = f"{self.EXTRACTION_PROMPT}\n\n标题：{article.title_original}\n正文：{text[:6000]}"
        raw = await self.llm.complete("Extract structured news facts.", prompt)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and isinstance(parsed.get("facts"), list):
                parsed = parsed["facts"]
            return self._validate_fragments(parsed) if isinstance(parsed, list) else self._fallback_extract(article)
        except json.JSONDecodeError:
            return self._fallback_extract(article)

    async def batch_extract(self, articles: list[Article]) -> list[dict]:
        fragments: list[dict] = []
        for article in articles:
            fragments.extend(await self.extract(article))
        return fragments

    def _fallback_extract(self, article: Article) -> list[dict]:
        fragments: list[dict] = [
            {
                "type": "what",
                "content": article.title_original,
                "entities": {},
                "numbers": {},
                "source_attribution": "unattributed",
                "certainty_level": "reportedly",
            }
        ]
        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*([A-Za-z%]+)?", article.content_original[:2000]):
            fragments.append(
                {
                    "type": "number",
                    "content": match.group(0),
                    "entities": {},
                    "numbers": {"value": float(match.group(1)), "unit": match.group(2), "description": "reported_number"},
                    "source_attribution": "unattributed",
                    "certainty_level": "reportedly",
                }
            )
        return fragments

    def _validate_fragments(self, rows: list[dict]) -> list[dict]:
        """Keep only schema-compatible fact fragments and fill safe defaults."""
        fragments: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            content = str(row.get("content") or "").strip()
            if not content:
                continue
            fragment_type = row.get("type") if row.get("type") in self.allowed_types else "what"
            source_attribution = (
                row.get("source_attribution")
                if row.get("source_attribution") in self.allowed_attribution
                else "unattributed"
            )
            certainty_level = (
                row.get("certainty_level") if row.get("certainty_level") in self.allowed_certainty else "reportedly"
            )
            fragments.append(
                {
                    "type": fragment_type,
                    "content": content,
                    "content_en": row.get("content_en"),
                    "entities": row.get("entities") if isinstance(row.get("entities"), dict) else {},
                    "numbers": row.get("numbers") if isinstance(row.get("numbers"), dict) else {},
                    "source_attribution": source_attribution,
                    "certainty_level": certainty_level,
                }
            )
        return fragments
