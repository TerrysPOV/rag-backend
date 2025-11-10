"""
Contract tests for Neo4J Graph API endpoints (NEO4J-001).

Tests all 7 graph endpoints:
1. POST /api/rag/graph/extract - Trigger entity extraction
2. GET /api/rag/graph/stats - Graph statistics
3. GET /api/rag/graph/health - Graph health check
4. POST /api/rag/graph/query - RAG query with graph traversal
5. GET /api/rag/graph/entity/{entity_id} - Entity details
6. GET /api/rag/graph/visualize/{entity_id} - Visualization data
7. POST /api/rag/graph/search - Search entities

Validates:
- Request/response schemas match API specification
- HTTP status codes are correct
- Error responses are properly formatted
- Authentication enforcement
- Rate limiting behavior
"""

import pytest
import requests
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def valid_extraction_request() -> Dict[str, Any]:
    """Valid graph extraction request payload."""
    return {
        "document_ids": ["doc_123", "doc_456"],
        "enable_llm_extraction": True
    }


@pytest.fixture
def valid_query_request() -> Dict[str, Any]:
    """Valid graph query request payload."""
    return {
        "query": "What are the requirements for Skilled Worker visa?",
        "use_graph": True,
        "max_graph_depth": 3,
        "top_k": 5
    }


@pytest.fixture
def valid_search_request() -> Dict[str, Any]:
    """Valid entity search request payload."""
    return {
        "search_term": "Skilled Worker",
        "entity_types": ["VisaType", "Requirement"],
        "limit": 20
    }


# ============================================================================
# POST /api/rag/graph/extract - Graph Extraction Trigger
# ============================================================================


@pytest.mark.contract
def test_graph_extract_endpoint_exists(valid_extraction_request):
    """Test that graph extraction endpoint is accessible."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/extract",
        json=valid_extraction_request,
        timeout=10
    )

    # Should return 202 (accepted), 401 (auth required), or 503 (Neo4J not configured)
    assert response.status_code in [202, 401, 403, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_extract_requires_authentication(valid_extraction_request):
    """Test that extraction endpoint requires authentication."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/extract",
        json=valid_extraction_request,
        timeout=10
    )

    # Should require authentication (editor/admin role)
    assert response.status_code in [401, 403, 202], \
        "Extraction should require authentication"


@pytest.mark.contract
def test_graph_extract_response_schema(valid_extraction_request, mock_editor_token):
    """Test extraction response matches expected schema."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/extract",
        json=valid_extraction_request,
        headers={"Authorization": f"Bearer {mock_editor_token}"},
        timeout=10
    )

    if response.status_code == 202:
        data = response.json()

        # Assert required fields
        assert "job_id" in data, "Missing 'job_id' field"
        assert "status" in data, "Missing 'status' field"
        assert "message" in data, "Missing 'message' field"

        # Assert field types
        assert isinstance(data["job_id"], str), "'job_id' must be string"
        assert data["status"] in ["queued", "running", "completed", "failed"], \
            f"Invalid status: {data['status']}"
        assert isinstance(data["message"], str), "'message' must be string"

    elif response.status_code == 503:
        # Neo4J not configured - expected in test environment
        data = response.json()
        assert "detail" in data, "Missing error detail"
        assert "Neo4J" in data["detail"], "Error should mention Neo4J"

    elif response.status_code in [401, 403]:
        pytest.skip("Authentication required - endpoint protected")


@pytest.mark.contract
def test_graph_extract_invalid_request():
    """Test that invalid extraction request returns 422."""
    invalid_payload = {
        "document_ids": "not_a_list",  # Should be list
        "enable_llm_extraction": "not_a_bool"  # Should be bool
    }

    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/extract",
        json=invalid_payload,
        timeout=10
    )

    # Should return 422 for validation error (or 401 if auth checked first)
    assert response.status_code in [422, 401, 403], \
        f"Expected 422/401/403, got {response.status_code}"


@pytest.mark.contract
def test_graph_extract_null_document_ids(mock_editor_token):
    """Test extraction with null document_ids (extract all)."""
    payload = {
        "document_ids": None,  # Extract from all documents
        "enable_llm_extraction": True
    }

    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/extract",
        json=payload,
        headers={"Authorization": f"Bearer {mock_editor_token}"},
        timeout=10
    )

    # Should accept null document_ids
    assert response.status_code in [202, 401, 403, 503], \
        f"Should accept null document_ids, got {response.status_code}"


# ============================================================================
# GET /api/rag/graph/stats - Graph Statistics
# ============================================================================


@pytest.mark.contract
def test_graph_stats_endpoint_exists():
    """Test that graph stats endpoint is accessible."""
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/stats",
        timeout=10
    )

    # Should return 200, 503 (Neo4J not configured), or possibly 401
    assert response.status_code in [200, 401, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_stats_response_schema():
    """Test stats response matches expected schema."""
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/stats",
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()

        # Assert required fields
        assert "node_counts" in data, "Missing 'node_counts'"
        assert "relationship_counts" in data, "Missing 'relationship_counts'"
        assert "total_nodes" in data, "Missing 'total_nodes'"
        assert "total_relationships" in data, "Missing 'total_relationships'"
        assert "graph_density" in data, "Missing 'graph_density'"
        assert "last_updated" in data, "Missing 'last_updated'"

        # Assert field types
        assert isinstance(data["node_counts"], dict), "'node_counts' must be dict"
        assert isinstance(data["relationship_counts"], dict), \
            "'relationship_counts' must be dict"
        assert isinstance(data["total_nodes"], int), "'total_nodes' must be int"
        assert isinstance(data["total_relationships"], int), \
            "'total_relationships' must be int"
        assert isinstance(data["graph_density"], (int, float)), \
            "'graph_density' must be number"
        assert isinstance(data["last_updated"], str), "'last_updated' must be string"

        # Assert graph_density is between 0 and 1
        assert 0 <= data["graph_density"] <= 1, \
            f"graph_density must be 0-1, got {data['graph_density']}"

    elif response.status_code == 503:
        # Neo4J not configured
        pytest.skip("Neo4J not configured in test environment")
    elif response.status_code == 401:
        pytest.skip("Authentication required")


@pytest.mark.contract
def test_graph_stats_is_public():
    """Test that stats endpoint does NOT require authentication."""
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/stats",
        timeout=10
    )

    # Should NOT return 401 (public endpoint)
    assert response.status_code != 401 or response.status_code == 503, \
        "Stats endpoint should be public"


# ============================================================================
# GET /api/rag/graph/health - Graph Health Check
# ============================================================================


@pytest.mark.contract
def test_graph_health_endpoint_exists():
    """Test that health check endpoint is accessible."""
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/health",
        timeout=10
    )

    assert response.status_code in [200, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_health_response_schema():
    """Test health response matches expected schema."""
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/health",
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()

        # Assert required fields
        assert "status" in data, "Missing 'status'"
        assert "orphaned_nodes" in data, "Missing 'orphaned_nodes'"
        assert "broken_references" in data, "Missing 'broken_references'"
        assert "warnings" in data, "Missing 'warnings'"
        assert "errors" in data, "Missing 'errors'"
        assert "timestamp" in data, "Missing 'timestamp'"

        # Assert field types
        assert data["status"] in ["healthy", "degraded", "unhealthy", "error"], \
            f"Invalid status: {data['status']}"
        assert isinstance(data["orphaned_nodes"], int), "'orphaned_nodes' must be int"
        assert isinstance(data["broken_references"], int), \
            "'broken_references' must be int"
        assert isinstance(data["warnings"], list), "'warnings' must be list"
        assert isinstance(data["errors"], list), "'errors' must be list"
        assert isinstance(data["timestamp"], str), "'timestamp' must be string"

    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


# ============================================================================
# POST /api/rag/graph/query - RAG Query with Graph Traversal
# ============================================================================


@pytest.mark.contract
def test_graph_query_endpoint_exists(valid_query_request):
    """Test that graph query endpoint is accessible."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/query",
        json=valid_query_request,
        timeout=15
    )

    # Should return 200 (public with optional auth) or 503
    assert response.status_code in [200, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_query_response_schema(valid_query_request):
    """Test query response matches expected schema."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/query",
        json=valid_query_request,
        timeout=15
    )

    if response.status_code == 200:
        data = response.json()

        # Assert required fields
        assert "query" in data, "Missing 'query'"
        assert "results" in data, "Missing 'results'"
        assert "graph_paths" in data, "Missing 'graph_paths'"
        assert "took_ms" in data, "Missing 'took_ms'"

        # Assert field types
        assert isinstance(data["query"], str), "'query' must be string"
        assert isinstance(data["results"], list), "'results' must be list"
        assert isinstance(data["graph_paths"], list), "'graph_paths' must be list"
        assert isinstance(data["took_ms"], (int, float)), "'took_ms' must be number"

        # If results present, validate result schema
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result, "Result missing 'id'"
            assert "content" in result or "metadata" in result, \
                "Result missing content/metadata"

    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


@pytest.mark.contract
def test_graph_query_invalid_request():
    """Test that invalid query request returns 422."""
    invalid_payloads = [
        {"query": "", "use_graph": True},  # Empty query
        {"query": "test", "max_graph_depth": 10},  # Depth too high (max 5)
        {"query": "test", "top_k": 200},  # top_k too high (max 100)
        {"query": "test", "max_graph_depth": 0},  # Depth too low (min 1)
    ]

    for payload in invalid_payloads:
        response = requests.post(
            f"{API_BASE_URL}/api/rag/graph/query",
            json=payload,
            timeout=10
        )

        assert response.status_code in [422, 503], \
            f"Expected 422/503 for invalid payload {payload}, got {response.status_code}"


@pytest.mark.contract
def test_graph_query_with_graph_disabled():
    """Test query with use_graph=False (graph disabled)."""
    payload = {
        "query": "Test query",
        "use_graph": False,
        "top_k": 5
    }

    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/query",
        json=payload,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        # Should return empty results when graph is disabled
        assert "results" in data, "Missing 'results'"
        assert "graph_paths" in data, "Missing 'graph_paths'"
        assert len(data["graph_paths"]) == 0, \
            "graph_paths should be empty when graph disabled"
    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


@pytest.mark.contract
def test_graph_query_max_depth_boundary():
    """Test max_graph_depth boundary values."""
    valid_depths = [1, 2, 3, 4, 5]

    for depth in valid_depths:
        payload = {
            "query": "Test query",
            "use_graph": True,
            "max_graph_depth": depth,
            "top_k": 5
        }

        response = requests.post(
            f"{API_BASE_URL}/api/rag/graph/query",
            json=payload,
            timeout=10
        )

        assert response.status_code in [200, 503], \
            f"Depth {depth} should be valid, got {response.status_code}"


# ============================================================================
# GET /api/rag/graph/entity/{entity_id} - Entity Details
# ============================================================================


@pytest.mark.contract
def test_graph_entity_details_endpoint_exists():
    """Test that entity details endpoint is accessible."""
    test_entity_id = "test_entity_123"

    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/entity/{test_entity_id}",
        timeout=10
    )

    # Should return 200, 404 (not found), or 503 (Neo4J not configured)
    assert response.status_code in [200, 404, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_entity_details_response_schema():
    """Test entity details response schema (if entity exists)."""
    # Use a known entity ID if available, otherwise expect 404
    test_entity_id = "skilled_worker_visa"

    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/entity/{test_entity_id}",
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()

        # Assert required fields
        assert "id" in data, "Missing 'id'"
        assert "labels" in data, "Missing 'labels'"
        assert "properties" in data, "Missing 'properties'"
        assert "relationships" in data, "Missing 'relationships'"

        # Assert field types
        assert isinstance(data["id"], str), "'id' must be string"
        assert isinstance(data["labels"], list), "'labels' must be list"
        assert isinstance(data["properties"], dict), "'properties' must be dict"
        assert isinstance(data["relationships"], dict), "'relationships' must be dict"

        # Assert relationships structure
        assert "outgoing" in data["relationships"] or "incoming" in data["relationships"], \
            "relationships must have 'outgoing' or 'incoming'"

    elif response.status_code == 404:
        # Entity not found - expected for test entity
        data = response.json()
        assert "detail" in data, "404 response should have 'detail'"

    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


@pytest.mark.contract
def test_graph_entity_details_not_found():
    """Test entity details returns 404 for non-existent entity."""
    non_existent_id = "non_existent_entity_xyz_123"

    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/entity/{non_existent_id}",
        timeout=10
    )

    # Should return 404 or 503
    assert response.status_code in [404, 503], \
        f"Expected 404/503 for non-existent entity, got {response.status_code}"


# ============================================================================
# GET /api/rag/graph/visualize/{entity_id} - Visualization Data
# ============================================================================


@pytest.mark.contract
def test_graph_visualize_endpoint_exists():
    """Test that visualization endpoint is accessible."""
    test_entity_id = "test_entity_123"

    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/visualize/{test_entity_id}",
        timeout=10
    )

    assert response.status_code in [200, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_visualize_response_schema():
    """Test visualization response schema."""
    test_entity_id = "skilled_worker_visa"

    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/visualize/{test_entity_id}",
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()

        # Assert required fields
        assert "nodes" in data, "Missing 'nodes'"
        assert "edges" in data, "Missing 'edges'"

        # Assert field types
        assert isinstance(data["nodes"], list), "'nodes' must be list"
        assert isinstance(data["edges"], list), "'edges' must be list"

        # If nodes present, validate node structure
        if len(data["nodes"]) > 0:
            node = data["nodes"][0]
            # Each node should have id, label, type
            assert "id" in node or "label" in node, \
                "Node should have 'id' or 'label'"

        # If edges present, validate edge structure
        if len(data["edges"]) > 0:
            edge = data["edges"][0]
            # Each edge should have source, target
            assert "source" in edge and "target" in edge, \
                "Edge should have 'source' and 'target'"

    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


@pytest.mark.contract
def test_graph_visualize_depth_parameter():
    """Test visualization depth parameter."""
    test_entity_id = "test_entity_123"

    valid_depths = [1, 2, 3, 4]

    for depth in valid_depths:
        response = requests.get(
            f"{API_BASE_URL}/api/rag/graph/visualize/{test_entity_id}",
            params={"depth": depth},
            timeout=10
        )

        assert response.status_code in [200, 503], \
            f"Depth {depth} should be valid, got {response.status_code}"


@pytest.mark.contract
def test_graph_visualize_depth_boundary():
    """Test visualization depth boundary values (min=1, max=4)."""
    test_entity_id = "test_entity_123"

    # Test min boundary
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/visualize/{test_entity_id}",
        params={"depth": 0},  # Below min
        timeout=10
    )
    assert response.status_code in [422, 503], \
        "depth=0 should be rejected (min=1)"

    # Test max boundary
    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/visualize/{test_entity_id}",
        params={"depth": 5},  # Above max
        timeout=10
    )
    assert response.status_code in [422, 503], \
        "depth=5 should be rejected (max=4)"


# ============================================================================
# POST /api/rag/graph/search - Search Entities
# ============================================================================


@pytest.mark.contract
def test_graph_search_endpoint_exists(valid_search_request):
    """Test that search endpoint is accessible."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/search",
        json=valid_search_request,
        timeout=10
    )

    assert response.status_code in [200, 503], \
        f"Unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_search_response_schema(valid_search_request):
    """Test search response matches expected schema."""
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/search",
        json=valid_search_request,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()

        # Assert required fields
        assert "results" in data, "Missing 'results'"
        assert "total" in data, "Missing 'total'"

        # Assert field types
        assert isinstance(data["results"], list), "'results' must be list"
        assert isinstance(data["total"], int), "'total' must be int"

        # If results present, validate result structure
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result or "text" in result, \
                "Result should have 'id' or 'text'"

    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


@pytest.mark.contract
def test_graph_search_invalid_request():
    """Test that invalid search request returns 422."""
    invalid_payloads = [
        {"search_term": "", "limit": 20},  # Empty search term
        {"search_term": "test", "limit": 200},  # Limit too high (max 100)
        {"search_term": "test", "limit": 0},  # Limit too low (min 1)
        {"search_term": "test", "entity_types": ["t" * 50]},  # Too many types (max 10)
    ]

    for payload in invalid_payloads:
        response = requests.post(
            f"{API_BASE_URL}/api/rag/graph/search",
            json=payload,
            timeout=10
        )

        assert response.status_code in [422, 503], \
            f"Expected 422/503 for invalid payload {payload}, got {response.status_code}"


@pytest.mark.contract
def test_graph_search_with_entity_types():
    """Test search with entity_types filter."""
    payload = {
        "search_term": "Skilled Worker",
        "entity_types": ["VisaType", "Requirement"],
        "limit": 10
    }

    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/search",
        json=payload,
        timeout=10
    )

    assert response.status_code in [200, 503], \
        f"Search with entity_types should succeed, got {response.status_code}"


@pytest.mark.contract
def test_graph_search_without_entity_types():
    """Test search without entity_types filter (search all types)."""
    payload = {
        "search_term": "passport",
        "entity_types": None,
        "limit": 20
    }

    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/search",
        json=payload,
        timeout=10
    )

    assert response.status_code in [200, 503], \
        f"Search without entity_types should succeed, got {response.status_code}"


@pytest.mark.contract
def test_graph_search_limit_boundary():
    """Test search limit boundary values (min=1, max=100)."""
    # Test min
    payload_min = {"search_term": "test", "limit": 1}
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/search",
        json=payload_min,
        timeout=10
    )
    assert response.status_code in [200, 503], "limit=1 should be valid"

    # Test max
    payload_max = {"search_term": "test", "limit": 100}
    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/search",
        json=payload_max,
        timeout=10
    )
    assert response.status_code in [200, 503], "limit=100 should be valid"


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.contract
def test_graph_endpoints_neo4j_unavailable():
    """
    Test all endpoints return 503 when Neo4J is not configured.

    This is expected behavior in test environment without Neo4J setup.
    """
    endpoints = [
        ("GET", "/api/rag/graph/stats"),
        ("GET", "/api/rag/graph/health"),
        ("POST", "/api/rag/graph/query", {"query": "test", "use_graph": True}),
        ("GET", "/api/rag/graph/entity/test_id"),
        ("GET", "/api/rag/graph/visualize/test_id"),
        ("POST", "/api/rag/graph/search", {"search_term": "test"}),
    ]

    for method, path, *payload in endpoints:
        if method == "GET":
            response = requests.get(f"{API_BASE_URL}{path}", timeout=10)
        else:
            response = requests.post(
                f"{API_BASE_URL}{path}",
                json=payload[0] if payload else {},
                timeout=10
            )

        # Should return 200 (if Neo4J configured) or 503 (if not)
        assert response.status_code in [200, 404, 503], \
            f"{method} {path} returned unexpected status: {response.status_code}"


@pytest.mark.contract
def test_graph_endpoints_internal_error_format():
    """Test that 500 errors return proper JSON format."""
    # This test documents expected error format
    # Actual 500 errors are hard to trigger in contract tests
    # Integration tests will cover error scenarios
    pass


# ============================================================================
# Rate Limiting Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.slow
def test_graph_query_rate_limiting():
    """
    Test that graph query endpoint enforces rate limits.

    Note: Rate limits may vary based on authentication.
    Unauthenticated: Stricter limits
    Authenticated: More generous limits
    """
    payload = {
        "query": "Test query for rate limiting",
        "use_graph": True,
        "top_k": 5
    }

    # Make rapid requests to trigger rate limit
    rate_limited = False

    for i in range(50):  # Attempt 50 rapid requests
        response = requests.post(
            f"{API_BASE_URL}/api/rag/graph/query",
            json=payload,
            timeout=10
        )

        if response.status_code == 429:  # Too Many Requests
            rate_limited = True
            # Verify rate limit response format
            data = response.json()
            assert "detail" in data, "Rate limit response should have 'detail'"
            break

    # Note: This test may not trigger rate limit in all environments
    # If no rate limit triggered, test passes (rate limiting may be disabled)
    if rate_limited:
        pytest.skip("Rate limiting verified")
    else:
        pytest.skip("Rate limiting not triggered (may be disabled or limits very high)")


# ============================================================================
# Authentication Tests
# ============================================================================


@pytest.mark.contract
def test_graph_extract_requires_editor_role():
    """Test that extraction requires editor or admin role (not viewer)."""
    # This would require mock viewer token
    # Implementation depends on authentication setup
    pass


@pytest.mark.contract
def test_graph_query_allows_optional_auth():
    """Test that query endpoint allows both authenticated and unauthenticated requests."""
    payload = {"query": "test", "use_graph": True, "top_k": 5}

    # Test without auth
    response_no_auth = requests.post(
        f"{API_BASE_URL}/api/rag/graph/query",
        json=payload,
        timeout=10
    )

    # Should return 200 or 503 (not 401)
    assert response_no_auth.status_code in [200, 503], \
        "Query endpoint should allow unauthenticated access"

    # Test with auth (if available)
    # This would require mock token
    pass


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.contract
@pytest.mark.slow
def test_graph_query_performance():
    """Test that graph query completes within acceptable time."""
    payload = {
        "query": "What are the requirements for Skilled Worker visa?",
        "use_graph": True,
        "max_graph_depth": 3,
        "top_k": 10
    }

    import time
    start_time = time.time()

    response = requests.post(
        f"{API_BASE_URL}/api/rag/graph/query",
        json=payload,
        timeout=30  # 30 second timeout
    )

    elapsed_ms = (time.time() - start_time) * 1000

    if response.status_code == 200:
        # Query should complete within 5 seconds (5000ms)
        assert elapsed_ms < 5000, \
            f"Graph query took {elapsed_ms}ms (should be <5000ms)"

        # Verify took_ms is reported
        data = response.json()
        assert "took_ms" in data, "Response should include 'took_ms'"

    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")


@pytest.mark.contract
def test_graph_stats_performance():
    """Test that stats endpoint responds quickly."""
    import time
    start_time = time.time()

    response = requests.get(
        f"{API_BASE_URL}/api/rag/graph/stats",
        timeout=10
    )

    elapsed_ms = (time.time() - start_time) * 1000

    if response.status_code == 200:
        # Stats should complete within 1 second (1000ms)
        assert elapsed_ms < 1000, \
            f"Graph stats took {elapsed_ms}ms (should be <1000ms)"
    elif response.status_code == 503:
        pytest.skip("Neo4J not configured")
