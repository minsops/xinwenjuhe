"""Redis-backed task progress helpers with a memory fallback."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from redis import Redis

from app.config import settings

_memory_progress: dict[str, dict] = {}
_memory_history: list[dict] = []
_memory_dead_letters: list[dict] = []
_memory_source_alerts: list[dict] = []


def set_progress(task_id: str, **payload) -> None:
    """Record task status for polling by API or operators."""
    data = {"updated_at": datetime.now(timezone.utc).isoformat(), **payload}
    _memory_progress[task_id] = data
    history_item = {"task_id": task_id, **data}
    _memory_history.append(history_item)
    del _memory_history[:-100]
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.setex(f"task_progress:{task_id}", 24 * 60 * 60, json.dumps(data))
        client.lpush("task_progress_history", json.dumps(history_item))
        client.ltrim("task_progress_history", 0, 99)
    except Exception:
        return


def get_progress(task_id: str) -> dict | None:
    """Read task progress from Redis or memory."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        raw = client.get(f"task_progress:{task_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return _memory_progress.get(task_id)


def list_progress(limit: int = 50) -> list[dict]:
    """Return recent task progress updates."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        rows = client.lrange("task_progress_history", 0, limit - 1)
        return [json.loads(row) for row in rows]
    except Exception:
        return list(reversed(_memory_history[-limit:]))


def queue_depth(queue_name: str = "celery") -> int | None:
    """Return Redis queue length when the broker is reachable."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        return int(client.llen(queue_name))
    except Exception:
        return None


def record_dead_letter(task_id: str, task_name: str, exc: BaseException, args: tuple | None = None, kwargs: dict | None = None) -> None:
    """Persist final task failures for operator review and replay decisions."""
    item = {
        "task_id": task_id,
        "task_name": task_name,
        "error": type(exc).__name__,
        "message": str(exc),
        "args": _safe_json(args or ()),
        "kwargs": _safe_json(kwargs or {}),
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    _memory_dead_letters.append(item)
    del _memory_dead_letters[:-100]
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.lpush("task_dead_letters", json.dumps(item))
        client.ltrim("task_dead_letters", 0, 99)
    except Exception:
        return


def list_dead_letters(limit: int = 50) -> list[dict]:
    """Return recent final task failures."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        rows = client.lrange("task_dead_letters", 0, limit - 1)
        return [json.loads(row) for row in rows]
    except Exception:
        return list(reversed(_memory_dead_letters[-limit:]))


def record_source_alert(source_id: str, source_name: str, reason: str, details: dict | None = None) -> None:
    """Persist source-level collection alerts for operator review."""
    item = {
        "source_id": source_id,
        "source_name": source_name,
        "reason": reason,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _memory_source_alerts.append(item)
    del _memory_source_alerts[:-100]
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.lpush("source_alerts", json.dumps(item))
        client.ltrim("source_alerts", 0, 99)
    except Exception:
        return


def list_source_alerts(limit: int = 50) -> list[dict]:
    """Return recent source-level collection alerts."""
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        rows = client.lrange("source_alerts", 0, limit - 1)
        return [json.loads(row) for row in rows]
    except Exception:
        return list(reversed(_memory_source_alerts[-limit:]))


def _safe_json(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)
