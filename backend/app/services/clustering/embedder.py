"""Text embedding abstraction with lightweight deterministic fallback."""

from __future__ import annotations

import hashlib
import logging
import math


logger = logging.getLogger(__name__)


class TextEmbedder:
    """Generate multilingual embeddings, falling back to hashed vectors if unavailable."""

    def __init__(self) -> None:
        self._model = None
        self._using_fallback = False

    async def embed_text(self, text: str) -> list[float]:
        try:
            from sentence_transformers import SentenceTransformer

            if self._model is None:
                logger.info("Loading sentence-transformers model...")
                self._model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
                logger.info("Model loaded successfully")
            return self._model.encode(text, normalize_embeddings=True).tolist()
        except Exception as exc:
            if not self._using_fallback:
                logger.warning("sentence-transformers unavailable, using hash fallback: %s", exc)
                self._using_fallback = True
            return self._hash_embedding(text)

    @property
    def is_using_fallback(self) -> bool:
        """Return true after the embedder has fallen back to hashed vectors."""
        return self._using_fallback

    def _hash_embedding(self, text: str, dims: int = 384) -> list[float]:
        vector = [0.0] * dims
        for token in text.lower().split():
            digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vector[digest % dims] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
