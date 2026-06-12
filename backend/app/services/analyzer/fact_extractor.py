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
你是一个专业的新闻事实核查分析师。新闻原文可能是任何语言，请直接阅读原文，不要要求先翻译整篇文章。

字段：
- type: what/who/where/when/number/cause/consequence
- content: 必填。用简体中文写出事实声明的完整内容，不要照抄外文
- content_en: 必填。将该事实声明用英文表达；如果原文已经是英文，可直接复制 content
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
        text = article.content_original
        prompt = f"{self.EXTRACTION_PROMPT}\n\n标题：{article.title_original}\n正文：{text[:6000]}"
        raw = await self.llm.complete("Extract structured news facts.", prompt)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and isinstance(parsed.get("facts"), list):
                parsed = parsed["facts"]
            if isinstance(parsed, list):
                fragments = self._validate_fragments(parsed, article.language)
                return fragments or self._fallback_extract(article)
            return self._fallback_extract(article)
        except json.JSONDecodeError:
            return self._fallback_extract(article)

    async def batch_extract(self, articles: list[Article]) -> list[dict]:
        fragments: list[dict] = []
        for article in articles:
            fragments.extend(await self.extract(article))
        return fragments

    def _fallback_extract(self, article: Article) -> list[dict]:
        text = article.content_original[:2000]
        fragments: list[dict] = []
        patterns = (
            ("casualties", r"(?P<value>\d+(?:\.\d+)?)\s*人?(?:死亡|遇难|丧生|身亡)"),
            ("injuries", r"(?P<value>\d+(?:\.\d+)?)\s*人?(?:受伤|受伤者|伤者)"),
            ("casualties", r"(?P<value>\d+(?:\.\d+)?)\s+(?:people\s+)?(?:killed|dead|deaths|died|fatalities)"),
            ("injuries", r"(?P<value>\d+(?:\.\d+)?)\s+(?:people\s+)?(?:injured|wounded|hurt)"),
        )
        seen: set[tuple[str, float]] = set()
        for description, pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = float(match.group("value"))
                if 1900 <= value <= 2099:
                    continue
                key = (description, value)
                if key in seen:
                    continue
                seen.add(key)
                if description == "casualties":
                    content = f"报道提到至少 {value:g} 人死亡或遇难。"
                else:
                    content = f"报道提到至少 {value:g} 人受伤。"
                content_en = self._context(text, match.start(), match.end()) or content
                fragments.append(
                    {
                        "type": "number",
                        "content": content,
                        "content_en": content_en,
                        "entities": {},
                        "numbers": {"value": value, "unit": "people", "description": description},
                        "source_attribution": "unattributed",
                        "certainty_level": "reportedly",
                    }
                )
        return fragments

    def _validate_fragments(self, rows: list[dict], language: str = "en") -> list[dict]:
        """Keep only schema-compatible fact fragments and fill safe defaults."""
        fragments: list[dict] = []
        is_english = language.lower().startswith("en")
        for row in rows:
            if not isinstance(row, dict):
                continue
            content = str(row.get("content") or "").strip()
            content_en = str(row.get("content_en") or "").strip()
            if not content:
                continue
            if not content_en and is_english:
                content_en = content
            if not content_en:
                continue
            if not _contains_cjk(content) and not language.lower().startswith("zh"):
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
                    "content_en": content_en,
                    "entities": row.get("entities") if isinstance(row.get("entities"), dict) else {},
                    "numbers": row.get("numbers") if isinstance(row.get("numbers"), dict) else {},
                    "source_attribution": source_attribution,
                    "certainty_level": certainty_level,
                }
            )
        return fragments

    @staticmethod
    def _context(text: str, start: int, end: int, radius: int = 80) -> str:
        return re.sub(r"\s+", " ", text[max(0, start - radius) : min(len(text), end + radius)]).strip()


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)
