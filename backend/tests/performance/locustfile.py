"""Locust performance smoke tests for the TruthPuzzle API."""

from __future__ import annotations

from locust import HttpUser, between, task


class TruthPuzzleApiUser(HttpUser):
    """Exercise high-traffic read paths and operational status endpoints."""

    wait_time = between(1, 3)

    @task(4)
    def list_events(self) -> None:
        self.client.get("/api/v1/events?limit=20", name="events:list")

    @task(3)
    def search(self) -> None:
        self.client.get("/api/v1/search?q=conflict&limit=10", name="search:query")

    @task(2)
    def list_sources(self) -> None:
        self.client.get("/api/v1/sources?limit=20", name="sources:list")

    @task(1)
    def task_status(self) -> None:
        self.client.get("/api/v1/tasks?limit=10", name="tasks:status")
