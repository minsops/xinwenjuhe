"""Celery application and beat schedule."""

from __future__ import annotations

from celery import Celery, Task

from app.config import settings
from app.tasks.progress import record_dead_letter, set_progress


class TruthPuzzleTask(Task):
    """Common Celery task behavior for retries, progress, and dead letters."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        record_dead_letter(task_id, self.name, exc, args=args, kwargs=kwargs)
        set_progress(task_id, status="failed", step=self.name, error=str(exc))
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery = Celery("truthpuzzle", broker=settings.redis_url, backend=settings.redis_url, task_cls=TruthPuzzleTask)
celery.conf.timezone = "UTC"
celery.conf.task_default_retry_delay = 30
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1
celery.conf.imports = (
    "app.tasks.analyze_task",
    "app.tasks.cluster_task",
    "app.tasks.collect_task",
    "app.tasks.credibility_task",
)
celery.conf.beat_schedule = {
    "collect-active-sources": {
        "task": "app.tasks.collect_task.collect_active_sources",
        "schedule": settings.regular_collect_interval_minutes * 60,
    },
    "collect-hot-events": {
        "task": "app.tasks.collect_task.collect_hot_events",
        "schedule": settings.hot_event_collect_interval_minutes * 60,
    },
    "cluster-new-articles": {
        "task": "app.tasks.cluster_task.cluster_new_articles",
        "schedule": settings.collect_interval_minutes * 60,
    },
    "refresh-source-credibility": {
        "task": "app.tasks.credibility_task.refresh_source_credibility",
        "schedule": 30 * 24 * 60 * 60,
    },
}
