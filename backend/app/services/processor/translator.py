"""Multilingual article translation with Redis-compatible cache keys."""

from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider


TRANSLATION_PROMPT = """将以下{source_lang}新闻报道翻译为{target_lang_label}。

翻译要求：
1. 保留原文的语气和措辞倾向（不要将带有立场的表述翻译成中性表述）
2. 如果目标语言是简体中文，所有新闻信息都必须用中文表达，不要保留整句英文或其他外文
3. 专有名词优先使用通行中文译名；没有通行译名时，才保留原文并在括号内给出中文解释
4. 保留原文中的直接引述，不做改写
5. 保留原文的段落结构
6. 对于难以精确翻译的文化特定表述，保留原文并在括号内解释
7. 只输出译文，不要输出说明、前缀、Markdown 或“以下是翻译”

原文：
{original_text}
"""

TRANSLATION_CACHE_VERSION = "v3"


class TranslationError(RuntimeError):
    """Raised when a translation provider returns unusable output."""


class TranslationService:
    """LLM-backed translation service preserving original article fields."""

    _memory_cache: dict[str, str] = {}

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()

    async def translate_article(self, text: str, source_lang: str, target_lang: str = "en") -> str:
        if not text.strip():
            return ""
        if self._same_language(source_lang, target_lang):
            return text
        prompt = TRANSLATION_PROMPT.format(
            source_lang=self.language_label(source_lang),
            target_lang_label=self.language_label(target_lang),
            original_text=text,
        )
        translated = (await self.llm.complete("你是专业新闻译者，必须忠实翻译并只输出译文。", prompt)).strip()
        self._validate_translation(text, translated, source_lang, target_lang)
        return translated

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

    @staticmethod
    def language_label(language: str) -> str:
        normalized = (language or "").lower()
        labels = {
            "zh": "简体中文",
            "zh-cn": "简体中文",
            "zh-hans": "简体中文",
            "auto": "原文语言",
            "en": "英文",
            "en-us": "英文",
            "en-gb": "英文",
        }
        return labels.get(normalized, language or "原文语言")

    @staticmethod
    def _same_language(source_lang: str, target_lang: str) -> bool:
        source = (source_lang or "").lower()
        target = (target_lang or "").lower()
        return bool(source and target and source.split("-")[0] == target.split("-")[0])

    @staticmethod
    def _validate_translation(original: str, translated: str, source_lang: str, target_lang: str) -> None:
        if not translated:
            raise TranslationError("翻译服务没有返回内容")
        if translated.strip() == original.strip() and not TranslationService._same_language(source_lang, target_lang):
            raise TranslationError("翻译服务返回了原文")
        if target_lang.lower().startswith("zh") and not source_lang.lower().startswith("zh"):
            cjk_chars = sum(1 for char in translated if "\u4e00" <= char <= "\u9fff")
            if cjk_chars < max(6, min(30, len(translated) // 20)):
                raise TranslationError("翻译结果不像中文")
            if TranslationService._has_long_latin_sentence(translated):
                raise TranslationError("翻译结果仍包含大段外文")

    @staticmethod
    def _has_long_latin_sentence(value: str) -> bool:
        run = 0
        for char in value:
            if char.isascii() and (char.isalpha() or char in " ,;:'\"()/-"):
                run += 1
                if run >= 48:
                    return True
            else:
                run = 0
        return False
