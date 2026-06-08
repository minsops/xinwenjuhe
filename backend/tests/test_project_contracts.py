"""Static contract tests for deployment and database requirements."""

from __future__ import annotations

from pathlib import Path
import unittest


TEST_DIR = Path(__file__).resolve().parent
HOST_ROOT = TEST_DIR.parents[1]
CONTAINER_ROOT = TEST_DIR.parent
ROOT = HOST_ROOT if (HOST_ROOT / "backend").exists() else CONTAINER_ROOT
BACKEND_ROOT = ROOT / "backend" if (ROOT / "backend").exists() else ROOT


class ProjectContractsTest(unittest.TestCase):
    """Validate important project-level contracts without external services."""

    def test_migration_uses_pgvector_and_indexes_embeddings(self) -> None:
        migration = (BACKEND_ROOT / "alembic/versions/0001_initial.py").read_text(encoding="utf-8")
        event_vector_migration = (BACKEND_ROOT / "alembic/versions/0002_event_center_pgvector.py").read_text(encoding="utf-8")
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector", migration)
        self.assertIn("Vector(384)", migration)
        self.assertIn("idx_articles_embedding", migration)
        self.assertIn("idx_events_center_embedding", migration)
        self.assertIn("idx_facts_embedding", migration)
        self.assertIn("vector_cosine_ops", migration)
        self.assertIn("ALTER COLUMN center_embedding TYPE vector(384)", event_vector_migration)
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_events_center_embedding", event_vector_migration)
        events_model = (BACKEND_ROOT / "app/models/event.py").read_text(encoding="utf-8")
        self.assertIn("from pgvector.sqlalchemy import Vector", events_model)
        self.assertIn("center_embedding: Mapped[list[float] | None] = mapped_column(Vector(384))", events_model)

    def test_compose_declares_required_services(self) -> None:
        compose_path = ROOT / "docker-compose.yml"
        if not compose_path.exists():
            self.skipTest("root docker-compose.yml is not copied into this test environment")
        compose = compose_path.read_text(encoding="utf-8")
        for service in ("db:", "redis:", "meilisearch:", "backend:", "celery_worker:", "celery_beat:", "frontend:"):
            self.assertIn(service, compose)
        self.assertIn("pgvector/pgvector:pg16", compose)
        self.assertIn("getmeili/meilisearch", compose)
        self.assertIn("condition: service_healthy", compose)

    def test_stack_verifier_checks_database_contracts(self) -> None:
        verifier_path = ROOT / "scripts/verify_stack.sh"
        if not verifier_path.exists():
            self.skipTest("root stack verifier is not copied into this test environment")
        verifier = verifier_path.read_text(encoding="utf-8")
        self.assertIn("docker is required", verifier)
        self.assertIn("pg_extension", verifier)
        self.assertIn("localhost:7700/health", verifier)
        self.assertIn("source_count >= 50", verifier)

    def test_event_management_and_discovery_routes_exist(self) -> None:
        events_api = (BACKEND_ROOT / "app/api/v1/events.py").read_text(encoding="utf-8")
        discovery_api = (BACKEND_ROOT / "app/api/v1/discovery.py").read_text(encoding="utf-8")
        sources_api = (BACKEND_ROOT / "app/api/v1/sources.py").read_text(encoding="utf-8")
        self.assertIn('/{event_id}/merge', events_api)
        self.assertIn('/{event_id}/split', events_api)
        self.assertIn('router.post("/sources")', discovery_api)
        self.assertIn("DiscoveredSourceCreate", discovery_api)
        self.assertIn('/sources/{candidate_id}/approve', discovery_api)
        self.assertIn("Source(", discovery_api)
        self.assertIn("cursor: str | None = None", sources_api)
        self.assertIn("_source_cursor", sources_api)
        self.assertIn("_source_article_cursor", sources_api)

    def test_analysis_payload_includes_graph_and_timeline(self) -> None:
        mapper = (BACKEND_ROOT / "app/services/analyzer/consensus_mapper.py").read_text(encoding="utf-8")
        service = (BACKEND_ROOT / "app/services/analyzer/event_analysis_service.py").read_text(encoding="utf-8")
        events_api = (BACKEND_ROOT / "app/api/v1/events.py").read_text(encoding="utf-8")
        self.assertIn("source_graph", mapper)
        self.assertIn("timeline", mapper)
        self.assertIn("def _source_graph", mapper)
        self.assertIn("def _timeline", mapper)
        self.assertIn("analyzed_article_count", mapper)
        self.assertIn("should_reanalyze", service)
        self.assertIn("settings.reanalyze_threshold", service)
        self.assertIn("process_event_pipeline.delay", events_api)

    def test_analyzer_outputs_are_schema_validated(self) -> None:
        extractor = (BACKEND_ROOT / "app/services/analyzer/fact_extractor.py").read_text(encoding="utf-8")
        narrative = (BACKEND_ROOT / "app/services/analyzer/narrative_analyzer.py").read_text(encoding="utf-8")
        self.assertIn("_validate_fragments", extractor)
        self.assertIn("allowed_types", extractor)
        self.assertIn("allowed_attribution", extractor)
        self.assertIn("_validate_frame", narrative)
        self.assertIn("article_id", narrative)

    def test_contradiction_detector_declares_five_documented_detectors(self) -> None:
        detector = (BACKEND_ROOT / "app/services/analyzer/contradiction_detector.py").read_text(encoding="utf-8")
        for name in (
            "detect_number_discrepancies",
            "detect_attribution_conflicts",
            "detect_timeline_conflicts",
            "detect_omissions",
            "detect_framing_differences",
        ):
            self.assertIn(f"async def {name}", detector)
        self.assertIn('contradiction_type="number_discrepancy"', detector)
        self.assertIn('contradiction_type="attribution_conflict"', detector)
        self.assertIn('contradiction_type="timeline_conflict"', detector)
        self.assertIn('contradiction_type="omission"', detector)
        self.assertIn('contradiction_type="framing_difference"', detector)

    def test_fact_fragments_receive_embeddings_before_analysis(self) -> None:
        service = (BACKEND_ROOT / "app/services/analyzer/event_analysis_service.py").read_text(encoding="utf-8")
        self.assertIn("TextEmbedder", service)
        self.assertIn("embed_text", service)
        self.assertIn("embedding=", service)

    def test_clustering_uses_time_window_existing_events_and_source_diversity(self) -> None:
        pipeline = (BACKEND_ROOT / "app/services/clustering/pipeline.py").read_text(encoding="utf-8")
        clusterer = (BACKEND_ROOT / "app/services/clustering/event_clusterer.py").read_text(encoding="utf-8")
        self.assertIn("settings.cluster_time_window_hours", pipeline)
        self.assertIn("_recent_events_with_centers", pipeline)
        self.assertIn("_matching_event", pipeline)
        self.assertIn("settings.cluster_similarity_threshold", pipeline)
        self.assertIn("len(source_ids) < 3", pipeline)
        self.assertIn("clusters[len(clusters)] = [article]", clusterer)

    def test_analysis_pipeline_performs_real_deduplication_task(self) -> None:
        analyze_task = (BACKEND_ROOT / "app/tasks/analyze_task.py").read_text(encoding="utf-8")
        self.assertIn("Deduplicator", analyze_task)
        self.assertIn("duplicate_of", analyze_task)
        self.assertIn("wire_agency", analyze_task)
        self.assertIn("content_similarity", analyze_task)

    def test_scraper_supports_js_rendering_pagination_and_retries(self) -> None:
        scraper = (BACKEND_ROOT / "app/services/collector/scraper.py").read_text(encoding="utf-8")
        self.assertIn("requires_js", scraper)
        self.assertIn("from scrapy import Selector", scraper)
        self.assertIn('"engine": "playwright" if config.get("requires_js") else "scrapy"', scraper)
        self.assertIn("async_playwright", scraper)
        self.assertIn("_list_pages", scraper)
        self.assertIn("next_button", scraper)
        self.assertIn("@retry", scraper)
        self.assertIn("_parse_date", scraper)

    def test_api_feed_type_is_collected_with_generic_json_mapper(self) -> None:
        collector = (BACKEND_ROOT / "app/services/collector/api_collector.py").read_text(encoding="utf-8")
        ingestion = (BACKEND_ROOT / "app/services/collector/ingestion.py").read_text(encoding="utf-8")
        self.assertIn("class APICollector", collector)
        self.assertIn("items_path", collector)
        self.assertIn("title_path", collector)
        self.assertIn("content_path", collector)
        self.assertIn('source.feed_type == "api"', ingestion)
        self.assertIn("self.api.fetch_feed(source)", ingestion)

    def test_documented_test_and_browser_dependencies_are_declared(self) -> None:
        pyproject = (BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        requirements = (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8")
        dev_requirements = (BACKEND_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
        self.assertIn("scrapy", pyproject)
        self.assertIn("playwright", pyproject)
        self.assertIn("testcontainers", pyproject)
        self.assertIn("locust", pyproject)
        self.assertIn("scrapy==", requirements)
        self.assertIn("playwright==", requirements)
        self.assertIn("torch==2.2.2", requirements)
        self.assertIn("sentence-transformers==", requirements)
        self.assertIn("pytest==", dev_requirements)
        self.assertIn("testcontainers[postgresql]==", dev_requirements)
        self.assertIn("locust==", dev_requirements)
        dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("python:3.11-slim-bookworm", dockerfile)
        self.assertIn("pip install --no-cache-dir -r requirements.txt", dockerfile)
        self.assertIn("python -m playwright install chromium", dockerfile)
        self.assertIn("libnss3", dockerfile)
        self.assertIn("urllib.request.urlopen", dockerfile)
        locustfile = BACKEND_ROOT / "tests/performance/locustfile.py"
        self.assertTrue(locustfile.exists())

    def test_documented_offline_evaluation_scripts_exist(self) -> None:
        clustering_script = ROOT / "scripts/evaluate_clustering.py"
        contradiction_script = ROOT / "scripts/evaluate_contradictions.py"
        if not clustering_script.exists() or not contradiction_script.exists():
            self.skipTest("root evaluation scripts are not copied into this test environment")
        clustering = clustering_script.read_text(encoding="utf-8")
        contradiction = contradiction_script.read_text(encoding="utf-8")
        metrics = (BACKEND_ROOT / "app/evaluation/metrics.py").read_text(encoding="utf-8")
        self.assertIn("pairwise_clustering_f1", clustering)
        self.assertIn("contradiction_precision_recall", contradiction)
        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("f1", metrics)

    def test_celery_records_dead_letters_for_final_failures(self) -> None:
        celery_app = (BACKEND_ROOT / "app/tasks/celery_app.py").read_text(encoding="utf-8")
        progress = (BACKEND_ROOT / "app/tasks/progress.py").read_text(encoding="utf-8")
        tasks_api = (BACKEND_ROOT / "app/api/v1/tasks.py").read_text(encoding="utf-8")
        ingestion = (BACKEND_ROOT / "app/services/collector/ingestion.py").read_text(encoding="utf-8")
        collect_task = (BACKEND_ROOT / "app/tasks/collect_task.py").read_text(encoding="utf-8")
        config = (BACKEND_ROOT / "app/config.py").read_text(encoding="utf-8")
        self.assertIn("class TruthPuzzleTask", celery_app)
        self.assertIn("on_failure", celery_app)
        self.assertIn("record_dead_letter", celery_app)
        self.assertIn("task_dead_letters", progress)
        self.assertIn("/dead-letters", tasks_api)
        self.assertIn("record_source_alert", progress)
        self.assertIn("source_alerts", progress)
        self.assertIn("/source-alerts", tasks_api)
        self.assertIn("collection_failure_threshold", ingestion)
        self.assertIn('"status": "failed"', ingestion)
        self.assertIn("regular_collect_interval_minutes", config)
        self.assertIn("hot_event_collect_interval_minutes", config)
        self.assertIn("hot_event_threshold", config)
        self.assertIn("collect-hot-events", celery_app)
        self.assertIn("settings.regular_collect_interval_minutes * 60", celery_app)
        self.assertIn("settings.hot_event_collect_interval_minutes * 60", celery_app)
        self.assertIn("collect_hot_events", collect_task)
        self.assertIn("Event.heat_score >= settings.hot_event_threshold", collect_task)
        self.assertIn("/collect-hot-events", tasks_api)

    def test_search_service_has_meilisearch_with_database_fallback(self) -> None:
        search = (BACKEND_ROOT / "app/services/search.py").read_text(encoding="utf-8")
        self.assertIn("ExternalSearchClient", search)
        self.assertIn("/indexes/{index}/search", search)
        self.assertIn("_search_events", search)
        self.assertIn("_search_articles", search)

    def test_llm_calls_use_provider_interface_with_runtime_fallback(self) -> None:
        factory = (BACKEND_ROOT / "app/services/llm/factory.py").read_text(encoding="utf-8")
        self.assertIn("class FallbackLLMProvider", factory)
        self.assertIn("provider.complete", factory)
        self.assertIn("EchoLLMProvider", factory)
        direct_sdk_hits = []
        for path in (BACKEND_ROOT / "app").rglob("*.py"):
            if "/services/llm/" in str(path):
                continue
            text = path.read_text(encoding="utf-8")
            if "AsyncOpenAI" in text or "AsyncAnthropic" in text or "chat.completions" in text:
                direct_sdk_hits.append(str(path))
        self.assertFalse(direct_sdk_hits, direct_sdk_hits)

    def test_websocket_updates_are_fanned_out_from_celery_via_redis(self) -> None:
        websocket = (BACKEND_ROOT / "app/api/v1/websocket.py").read_text(encoding="utf-8")
        main = (BACKEND_ROOT / "app/main.py").read_text(encoding="utf-8")
        analyze_task = (BACKEND_ROOT / "app/tasks/analyze_task.py").read_text(encoding="utf-8")
        self.assertIn("EVENT_UPDATE_CHANNEL", websocket)
        self.assertIn("publish_event_update", websocket)
        self.assertIn("redis_event_listener", websocket)
        self.assertIn("create_task(redis_event_listener())", main)
        self.assertIn("publish_event_update", analyze_task)
        self.assertIn('"analysis_updated"', analyze_task)


if __name__ == "__main__":
    unittest.main()
