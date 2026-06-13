"""Regression tests for translation cache semantics."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if find_spec("redis"):
    from app.services.processor.translator import (
        TRANSLATION_CACHE_VERSION,
        TranslationError,
        TranslationService,
    )
    from app.api.v1.articles import _stores_article_translation, _translation_fallback_response
else:
    TRANSLATION_CACHE_VERSION = "missing"
    TranslationError = RuntimeError
    TranslationService = None
    _stores_article_translation = None
    _translation_fallback_response = None


@unittest.skipUnless(TranslationService is not None, "backend runtime dependencies are not installed")
class TranslationServiceTest(unittest.TestCase):
    """Validate documented article-target cache keys."""

    def test_article_translation_cache_key_includes_article_field_and_target(self) -> None:
        key = TranslationService.cache_key("hello", "zh", article_id="article-1", field="title")

        self.assertEqual(key, f"translate:{TRANSLATION_CACHE_VERSION}:article-1:title:zh")

    def test_text_hash_fallback_cache_key_is_stable(self) -> None:
        key = TranslationService.cache_key("hello", "zh")

        self.assertTrue(key.startswith(f"translate:{TRANSLATION_CACHE_VERSION}:"))
        self.assertTrue(key.endswith(":zh"))
        self.assertNotIn("article-1", key)

    def test_rejects_english_output_for_chinese_translation(self) -> None:
        with self.assertRaises(TranslationError):
            TranslationService._validate_translation("hello world", "hello world", "en", "zh")

        with self.assertRaises(TranslationError):
            TranslationService._validate_translation("hello world", "translated text", "en", "zh")

    def test_article_translation_failure_returns_honest_chinese_fallback(self) -> None:
        response = _translation_fallback_response("zh", TranslationError("翻译服务返回了原文"))

        self.assertTrue(response.fallback)
        self.assertFalse(response.cached)
        self.assertIn("自动翻译服务没有返回可用的中文译文", response.content)
        self.assertIn("翻译服务返回了原文", response.message or "")

    def test_article_translation_fields_cache_chinese_ui_text(self) -> None:
        self.assertTrue(_stores_article_translation("zh"))
        self.assertTrue(_stores_article_translation("zh-CN"))
        self.assertFalse(_stores_article_translation("en"))


if __name__ == "__main__":
    unittest.main()
