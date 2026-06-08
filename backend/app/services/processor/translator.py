"""Multilingual article translation with Redis-compatible cache keys."""

from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider


TRANSLATION_PROMPT = """将以下{source_lang}新闻报道翻译为{target_lang}。

翻译要求：
1. 保留原文的语气和措辞倾向（不要将带有立场的表述翻译成中性表述）
2. 专有名词保留原文，括号内标注翻译
3. 保留原文中的直接引述，不做改写
4. 保留原文的段落结构
5. 对于难以精确翻译的文化特定表述，保留原文并在括号内解释

原文：
{original_text}
"""

TRANSLATION_CACHE_VERSION = "v1"


class TranslationService:
    """LLM-backed translation service preserving original article fields."""

    _memory_cache: dict[str, str] = {}

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()

    async def translate_article(self, text: str, source_lang: str, target_lang: str = "en") -> str:
        prompt = TRANSLATION_PROMPT.format(
            source_lang=source_lang, target_lang=target_lang, original_text=text
        )
        return await self.llm.complete("You are a precise news translator.", prompt)

    async def translate_on_demand(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        article_id: str | None = None,
        field: str = "content",
    ) -> tuple[str, bool]:
        key = self.cache_key(text, target_lang, article_id=article_id, field=field)
        cached = await self._get_cached(key)
        if cached is not None:
            return cached, True
        translated = await self.translate_article(text, source_lang, target_lang)
        await self._set_cached(key, translated)
        return translated, False

    async def _get_cached(self, key: str) -> str | None:
        if key in self._memory_cache:
            return self._memory_cache[key]
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            value = await client.get(key)
            await client.aclose()
            if value is not None:
                self._memory_cache[key] = value
            return value
        except Exception:
            return None

    async def _set_cached(self, key: str, translated: str) -> None:
        self._memory_cache[key] = translated
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            await client.setex(key, 30 * 24 * 60 * 60, translated)
            await client.aclose()
        except Exception:
            return

    @staticmethod
    def cache_key(text: str, target_lang: str, article_id: str | None = None, field: str = "content") -> str:
        if article_id:
            return f"translate:{TRANSLATION_CACHE_VERSION}:{article_id}:{field}:{target_lang}"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"translate:{TRANSLATION_CACHE_VERSION}:{digest}:{target_lang}"
