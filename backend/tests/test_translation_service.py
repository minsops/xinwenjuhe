"""Regression tests for translation cache semantics."""

from __future__ import annotations

from importlib.util import find_spec
import unittest

if not find_spec("redis"):
    raise unittest.SkipTest("backend runtime dependencies are not installed")

from app.services.processor.translator import (
    TRANSLATION_CACHE_VERSION,
    TranslationError,
    TranslationService,
)


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


if __name__ == "__main__":
    unittest.main()
