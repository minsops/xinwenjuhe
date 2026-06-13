"""Article cleaning and duplicate detection utilities."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from html import unescape


class Deduplicator:
    """Detect URL and content duplicates and normalize article content."""

    def normalize_text(self, text: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = unescape(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned.replace("“", '"').replace("”", '"').replace("’", "'")

    def is_content_duplicate(self, left: str, right: str, threshold: float = 0.92) -> bool:
        return SequenceMatcher(None, self.normalize_text(left), self.normalize_text(right)).ratio() >= threshold

    def detect_wire_copy(self, text: str) -> str | None:
        lowered = text.lower()
        prefix = lowered[:500]
        agency_patterns = {
            "REUTERS": r"\breuters\b",
            "AP": r"\b(?:associated press|ap)\b",
            "AFP": r"\bafp\b",
            "EFE": r"\befe\b",
            "XINHUA": r"\b(?:xinhua|xinhuanet)\b|新华社|新华网",
            "TASS": r"\b(?:tass|itar-tass)\b|тасс",
            "ANADOLU": r"\b(?:anadolu|aa)\b",
            "DPA": r"\b(?:deutsche presse-agentur|dpa)\b",
            "KYODO": r"\bkyodo\b|共同社",
            "YONHAP": r"\byonhap\b|연합뉴스|韩联社",
            "PTI": r"\b(?:press trust of india|pti)\b",
            "IRNA": r"\birna\b",
        }
        for agency, pattern in agency_patterns.items():
            if re.search(pattern, prefix):
                return agency
        return None
