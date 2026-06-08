"""Helpers for source collection state and scoring defaults."""

from __future__ import annotations

from app.models.source import Source


def update_collection_success(source: Source) -> None:
    """Mark a source collection run as successful."""
    source.consecutive_failures = 0


def update_collection_failure(source: Source) -> bool:
    """Increment failure count and deactivate after three consecutive failures."""
    source.consecutive_failures += 1
    if source.consecutive_failures >= 3:
        source.is_active = False
        return True
    return False
