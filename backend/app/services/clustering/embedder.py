"""Text embedding abstraction with lightweight deterministic fallback."""

from __future__ import annotations

import hashlib
import math


class TextEmbedder:
    """Generate multilingual embeddings, falling back to hashed vectors if unavailable."""

    def __init__(self) -> None:
        self._model = None

    async def embed_text(self, text: str) -> list[float]:
        try:
            from sentence_transformers import SentenceTransformer

            if self._model is None:
                self._model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            return self._model.encode(text, normalize_embeddings=True).tolist()
        except Exception:
            return self._hash_embedding(text)

    def _hash_embedding(self, text: str, dims: int = 384) -> list[float]:
        vector = [0.0] * dims
        for token in text.lower().split():
            digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vector[digest % dims] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

