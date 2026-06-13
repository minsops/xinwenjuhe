"""Tests for the text embedding fallback contract."""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from unittest.mock import patch

from app.services.clustering.embedder import TextEmbedder


class TextEmbedderTest(unittest.TestCase):
    """Validate model loading and fallback state reporting."""

    def test_successful_model_encode_does_not_mark_fallback(self) -> None:
        fake_module = types.ModuleType("sentence_transformers")
        fake_module.SentenceTransformer = FakeSentenceTransformer

        with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
            embedder = TextEmbedder()
            vector = asyncio.run(embedder.embed_text("shared event fact"))

        self.assertEqual(vector, [1.0, 0.0, 0.0])
        self.assertFalse(embedder.is_using_fallback)

    def test_import_failure_marks_fallback_and_returns_384_dimensions(self) -> None:
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            embedder = TextEmbedder()
            vector = asyncio.run(embedder.embed_text("shared event fact"))

        self.assertTrue(embedder.is_using_fallback)
        self.assertEqual(len(vector), 384)
        self.assertGreater(sum(abs(value) for value in vector), 0)


class FakeSentenceTransformer:
    """Small sentence-transformers stand-in."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def encode(self, text: str, normalize_embeddings: bool) -> "FakeVector":
        return FakeVector([1.0, 0.0, 0.0])


class FakeVector(list):
    """List with the numpy-like API used by TextEmbedder."""

    def tolist(self) -> list[float]:
        return list(self)


if __name__ == "__main__":
    unittest.main()
