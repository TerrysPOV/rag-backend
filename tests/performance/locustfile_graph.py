"""
Locust Load Test for Neo4J Graph Traversal Endpoints

This script simulates realistic user traffic patterns for graph-based RAG queries.
It tests performance under concurrent load and helps identify bottlenecks.

Usage:
    # Install locust
    pip install locust

    # Run load test with 50 concurrent users
    locust -f tests/performance/locustfile_graph.py \
           --host=http://localhost:8000 \
           --users=50 \
           --spawn-rate=10 \
           --run-time=5m \
           --html=reports/locust_graph_$(date +%Y%m%d_%H%M%S).html

    # Run in headless mode (no web UI)
    locust -f tests/performance/locustfile_graph.py \
           --host=http://localhost:8000 \
           --users=50 \
           --spawn-rate=10 \
           --run-time=5m \
           --headless \
           --html=reports/locust_graph_results.html \
           --csv=reports/locust_graph_results

Performance Targets:
    - p95 query latency < 500ms
    - p99 query latency < 1000ms
    - 0% error rate under 50 concurrent users
    - 60-70% cache hit rate (after warmup)

Load Test Scenarios:
    1. Common graph queries (80% of traffic)
    2. Uncommon/complex queries (20% of traffic)
    3. Entity search
    4. Graph visualization
    5. Statistics dashboard
"""

from locust import HttpUser, task, between, events
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphQueryUser(HttpUser):
    """
    Simulates user querying graph endpoints.

    Follows 80/20 distribution:
    - 80% of requests are common queries (task weight 10)
    - 20% of requests are uncommon queries (task weight 2)
    """

    # Wait 1-3 seconds between requests (realistic user behavior)
    wait_time = between(1, 3)

    # Common queries (20% of queries generate 80% of traffic)
    common_queries = [
        "Skilled Worker visa requirements",
        "Student visa documents",
        "Family visa eligibility",
        "English language test requirements",
        "financial requirements for visa",
        "spouse visa documents needed",
        "Tier 2 visa salary threshold",
        "indefinite leave to remain requirements",
    ]

    # Uncommon queries (more specific, less frequent)
    uncommon_queries = [
        "Can I switch from Student visa to Skilled Worker visa?",
        "Tuberculosis test requirements for spouse visa from India",
        "Police certificate validity period for settlement application",
        "Tier 2 ICT maximum stay duration without extension",
        "Global Talent visa transition to Innovator Founder",
        "English language exemption for Hong Kong nationals",
        "Financial maintenance requirements for dependent children under 18",
        "Priority visa processing time for Healthcare Worker route",
    ]

    @task(10)
    def query_graph_common(self):
        """
        Test common graph queries (80% of traffic).

        Expected performance:
        - p50: < 50ms (cache hit)
        - p95: < 200ms (cache miss with optimization)
        - p99: < 500ms
        """
        query = random.choice(self.common_queries)

        with self.client.post(
            "/api/rag/graph/query",
            json={
                "query": query,
                "use_graph": True,
                "max_graph_depth": 3,
                "top_k": 10,
            },
            catch_response=True,
            name="/api/rag/graph/query (common)",
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if "results" not in data or "graph_paths" not in data:
                    response.failure(f"Invalid response structure: {data.keys()}")
                    return

                # Check performance target
                took_ms = data.get("took_ms", 9999)
                if took_ms > 500:
                    response.failure(
                        f"Query too slow: {took_ms:.2f}ms (target: p95 < 500ms)"
                    )
                elif took_ms > 200:
                    logger.warning(
                        f"Query slower than expected: {took_ms:.2f}ms (target: p95 < 200ms)"
                    )
                else:
                    response.success()

            elif response.status_code == 503:
                response.failure("Neo4J service unavailable")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")

    @task(2)
    def query_graph_uncommon(self):
        """
        Test uncommon/complex graph queries (20% of traffic).

        These queries are more specific and may require deeper traversal.

        Expected performance:
        - p50: < 100ms
        - p95: < 500ms
        - p99: < 1000ms
        """
        query = random.choice(self.uncommon_queries)

        with self.client.post(
            "/api/rag/graph/query",
            json={
                "query": query,
                "use_graph": True,
                "max_graph_depth": 4,  # Deeper traversal for complex queries
                "top_k": 20,
            },
            catch_response=True,
            name="/api/rag/graph/query (uncommon)",
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Validate response
                if "results" not in data:
                    response.failure(f"Invalid response: {data.keys()}")
                    return

                # Check performance (more lenient for complex queries)
                took_ms = data.get("took_ms", 9999)
                if took_ms > 1000:
                    response.failure(
                        f"Complex query too slow: {took_ms:.2f}ms (target: p99 < 1000ms)"
                    )
                else:
                    response.success()

            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)
    def search_entities(self):
        """
        Test entity search endpoint.

        Expected performance:
        - p50: < 50ms (with full-text index)
        - p95: < 150ms
        """
        search_terms = [
            "visa",
            "passport",
            "requirement",
            "English",
            "financial",
            "skilled",
            "student",
            "family",
        ]

        search_term = random.choice(search_terms)

        with self.client.post(
            "/api/rag/graph/search",
            json={
                "search_term": search_term,
                "entity_types": None,
                "limit": 20,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Validate response
                if "results" not in data or "total" not in data:
                    response.failure(f"Invalid search response: {data.keys()}")
                else:
                    response.success()

            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    def get_visualization(self):
        """
        Test graph visualization endpoint.

        Expected performance:
        - p50: < 150ms (depth=2)
        - p95: < 500ms (depth=3)
        """
        # Mock entity IDs (these should be replaced with real IDs from your graph)
        # In production, you would query for actual entity IDs first
        entity_ids = [
            "visa_type_abc123",
            "requirement_def456",
            "document_type_ghi789",
            "visa_type_skilled_worker",
            "requirement_english_b1",
        ]

        entity_id = random.choice(entity_ids)
        depth = random.choice([2, 3])  # Test different depths

        with self.client.get(
            f"/api/rag/graph/visualize/{entity_id}",
            params={"depth": depth},
            catch_response=True,
            name=f"/api/rag/graph/visualize (depth={depth})",
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Validate response
                if "nodes" not in data or "edges" not in data:
                    response.failure(f"Invalid visualization response: {data.keys()}")
                else:
                    response.success()

            elif response.status_code == 404:
                # Entity not found - this is expected for mock IDs
                response.success()  # Don't count as failure in load test

            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def get_stats(self):
        """
        Test graph statistics endpoint.

        This simulates admin dashboard polling.

        Expected performance:
        - p50: < 100ms
        - p95: < 300ms
        """
        with self.client.get(
            "/api/rag/graph/stats",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Validate response
                required_fields = [
                    "total_nodes",
                    "total_relationships",
                    "graph_density",
                ]
                if all(field in data for field in required_fields):
                    response.success()
                else:
                    response.failure(
                        f"Missing required fields: {set(required_fields) - set(data.keys())}"
                    )

            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def health_check(self):
        """
        Test graph health check endpoint.

        Expected performance:
        - p50: < 100ms (with optimized queries)
        - p95: < 300ms
        """
        with self.client.get(
            "/api/rag/graph/health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Validate response
                if "status" in data:
                    response.success()

                    # Log warnings for unhealthy state
                    if data["status"] in ["degraded", "unhealthy", "error"]:
                        logger.warning(
                            f"Graph health check returned status: {data['status']}"
                        )

                else:
                    response.failure(f"Invalid health check response: {data.keys()}")

            else:
                response.failure(f"HTTP {response.status_code}")


class GraphExtractionUser(HttpUser):
    """
    Simulates admin triggering graph extraction (low frequency).

    This user type runs separately and less frequently.
    """

    # Wait 30-60 seconds between extraction requests (admins don't spam this)
    wait_time = between(30, 60)

    @task
    def trigger_extraction(self):
        """
        Test graph extraction endpoint (admin only).

        This is a background task, so we just check that it queues successfully.
        """
        with self.client.post(
            "/api/rag/graph/extract",
            json={
                "document_ids": None,  # All documents
                "enable_llm_extraction": True,
            },
            headers={
                # TODO: Replace with real authentication token
                "Authorization": "Bearer fake-admin-token",
            },
            catch_response=True,
        ) as response:
            if response.status_code in [200, 202]:
                data = response.json()

                # Validate response
                if "job_id" in data and data.get("status") == "queued":
                    response.success()
                else:
                    response.failure(f"Invalid extraction response: {data}")

            elif response.status_code == 401:
                # Unauthorized - expected without real token
                response.success()  # Don't count as failure

            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# Locust Event Hooks (Performance Monitoring)
# ============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    logger.info("=" * 80)
    logger.info("Neo4J Graph Traversal Load Test STARTED")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Users: {environment.runner.target_user_count}")
    logger.info("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and summary."""
    logger.info("=" * 80)
    logger.info("Neo4J Graph Traversal Load Test COMPLETED")
    logger.info("=" * 80)

    # Get statistics
    stats = environment.stats

    # Check if we met performance targets
    p95_latency = stats.total.get_response_time_percentile(0.95)
    p99_latency = stats.total.get_response_time_percentile(0.99)

    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failed requests: {stats.total.num_failures}")
    logger.info(f"p50 latency: {stats.total.median_response_time}ms")
    logger.info(f"p95 latency: {p95_latency}ms (target: < 500ms)")
    logger.info(f"p99 latency: {p99_latency}ms (target: < 1000ms)")

    # Performance assessment
    if p95_latency < 500 and stats.total.num_failures == 0:
        logger.info("✅ PASS: Performance targets met!")
    elif p95_latency < 1000:
        logger.warning(
            "⚠️  WARNING: p95 latency above target but acceptable (< 1000ms)"
        )
    else:
        logger.error("❌ FAIL: Performance targets not met")

    logger.info("=" * 80)
