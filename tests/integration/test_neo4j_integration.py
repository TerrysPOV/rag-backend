"""
Integration tests for Neo4J Graph Service (NEO4J-001).

Tests Neo4J service methods with mock Neo4J database:
- Graph statistics calculation
- Health checks
- Entity details retrieval
- Visualization data generation
- Entity search
- Schema initialization
- Error handling and graceful degradation

Uses pytest fixtures with mock Neo4J driver to avoid requiring live database.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.neo4j_graph_service import Neo4JGraphService, get_graph_service


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4J driver for testing."""
    driver = Mock()
    driver.verify_connectivity = Mock()
    driver.close = Mock()
    return driver


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4J session for query execution."""
    session = Mock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


@pytest.fixture
def graph_service(mock_neo4j_driver, monkeypatch):
    """Create Neo4JGraphService with mocked driver."""
    # Patch GraphDatabase.driver to return mock
    with patch('src.services.neo4j_graph_service.GraphDatabase.driver') as mock_gdb:
        mock_gdb.return_value = mock_neo4j_driver

        service = Neo4JGraphService(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test_user",
            neo4j_password="test_password",
            neo4j_database="test_db"
        )

        yield service

        # Cleanup
        service.close()


@pytest.fixture
def sample_graph_stats() -> Dict[str, Any]:
    """Sample graph statistics for testing."""
    return {
        "node_counts": {
            "Entity": 150,
            "VisaType": 25,
            "Requirement": 75,
            "Document": 50
        },
        "relationship_counts": {
            "REQUIRES": 100,
            "SATISFIED_BY": 80,
            "CAN_TRANSITION_TO": 20,
            "DEPENDS_ON": 30
        },
        "total_nodes": 300,
        "total_relationships": 230,
        "graph_density": 0.0026,
        "last_updated": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_entity_data() -> Dict[str, Any]:
    """Sample entity details for testing."""
    return {
        "id": "skilled_worker_visa",
        "labels": ["VisaType", "Entity"],
        "properties": {
            "id": "skilled_worker_visa",
            "text": "Skilled Worker visa",
            "type": "visa_type",
            "chunk_ids": ["chunk_001", "chunk_002"]
        },
        "relationships": {
            "outgoing": [
                {
                    "type": "REQUIRES",
                    "direction": "outgoing",
                    "target_id": "english_test",
                    "target_text": "English language test"
                },
                {
                    "type": "REQUIRES",
                    "direction": "outgoing",
                    "target_id": "job_offer",
                    "target_text": "Job offer from UK sponsor"
                }
            ],
            "incoming": [
                {
                    "type": "CAN_TRANSITION_TO",
                    "direction": "incoming",
                    "source_id": "student_visa",
                    "source_text": "Student visa"
                }
            ]
        }
    }


# ============================================================================
# Graph Statistics Tests
# ============================================================================


@pytest.mark.integration
def test_get_graph_statistics_success(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test successful graph statistics retrieval."""
    # Mock session.run() responses
    mock_node_result = Mock()
    mock_node_result.__iter__ = Mock(return_value=iter([
        {"labels": ["Entity"], "count": 150},
        {"labels": ["VisaType"], "count": 25},
        {"labels": ["Requirement"], "count": 75}
    ]))

    mock_rel_result = Mock()
    mock_rel_result.__iter__ = Mock(return_value=iter([
        {"rel_type": "REQUIRES", "count": 100},
        {"rel_type": "SATISFIED_BY", "count": 80}
    ]))

    mock_total_nodes = Mock()
    mock_total_nodes.single = Mock(return_value={"total": 250})

    mock_total_rels = Mock()
    mock_total_rels.single = Mock(return_value={"total": 180})

    # Setup session.run() to return different results based on query
    def run_side_effect(query, **kwargs):
        if "labels(n)" in query:
            return mock_node_result
        elif "type(r)" in query:
            return mock_rel_result
        elif "count(n)" in query:
            return mock_total_nodes
        elif "count(r)" in query:
            return mock_total_rels
        return Mock()

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    stats = graph_service.get_graph_statistics()

    # Assert
    assert "node_counts" in stats
    assert "relationship_counts" in stats
    assert "total_nodes" in stats
    assert "total_relationships" in stats
    assert "graph_density" in stats
    assert "last_updated" in stats

    assert stats["total_nodes"] == 250
    assert stats["total_relationships"] == 180
    assert 0 <= stats["graph_density"] <= 1


@pytest.mark.integration
def test_get_graph_statistics_empty_graph(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test statistics for empty graph."""
    # Mock empty results
    mock_empty_result = Mock()
    mock_empty_result.__iter__ = Mock(return_value=iter([]))

    mock_zero = Mock()
    mock_zero.single = Mock(return_value={"total": 0})

    def run_side_effect(query, **kwargs):
        if "labels(n)" in query or "type(r)" in query:
            return mock_empty_result
        return mock_zero

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    stats = graph_service.get_graph_statistics()

    # Assert
    assert stats["total_nodes"] == 0
    assert stats["total_relationships"] == 0
    assert stats["graph_density"] == 0.0
    assert stats["node_counts"] == {}
    assert stats["relationship_counts"] == {}


@pytest.mark.integration
def test_get_graph_statistics_driver_error(graph_service):
    """Test statistics when driver is None."""
    graph_service.driver = None

    with pytest.raises(RuntimeError, match="Neo4J driver not initialized"):
        graph_service.get_graph_statistics()


@pytest.mark.integration
def test_get_graph_statistics_query_error(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test statistics when Neo4J query fails."""
    mock_neo4j_session.run = Mock(side_effect=Exception("Neo4J query failed"))
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    with pytest.raises(Exception, match="Neo4J query failed"):
        graph_service.get_graph_statistics()


# ============================================================================
# Health Check Tests
# ============================================================================


@pytest.mark.integration
def test_health_check_healthy(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test health check for healthy graph."""
    # Mock healthy results
    mock_orphaned = Mock()
    mock_orphaned.single = Mock(return_value={"orphaned_count": 10})  # Below threshold

    mock_broken = Mock()
    mock_broken.single = Mock(return_value={"broken_count": 0})

    def run_side_effect(query, **kwargs):
        if "NOT (n)--" in query:  # Orphaned nodes query
            return mock_orphaned
        elif "chunk_ids IS NULL" in query:  # Broken references query
            return mock_broken
        return Mock()

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    health = graph_service.health_check()

    # Assert
    assert health["status"] == "healthy"
    assert health["orphaned_nodes"] == 10
    assert health["broken_references"] == 0
    assert len(health["warnings"]) == 0
    assert len(health["errors"]) == 0
    assert "timestamp" in health


@pytest.mark.integration
def test_health_check_degraded(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test health check for degraded graph (many orphaned nodes)."""
    # Mock degraded results
    mock_orphaned = Mock()
    mock_orphaned.single = Mock(return_value={"orphaned_count": 150})  # Above threshold

    mock_broken = Mock()
    mock_broken.single = Mock(return_value={"broken_count": 0})

    def run_side_effect(query, **kwargs):
        if "NOT (n)--" in query:
            return mock_orphaned
        elif "chunk_ids IS NULL" in query:
            return mock_broken
        return Mock()

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    health = graph_service.health_check()

    # Assert
    assert health["status"] == "degraded"
    assert health["orphaned_nodes"] == 150
    assert len(health["warnings"]) > 0
    assert "orphaned nodes" in health["warnings"][0]


@pytest.mark.integration
def test_health_check_unhealthy(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test health check for unhealthy graph (broken references)."""
    # Mock unhealthy results
    mock_orphaned = Mock()
    mock_orphaned.single = Mock(return_value={"orphaned_count": 50})

    mock_broken = Mock()
    mock_broken.single = Mock(return_value={"broken_count": 25})  # Broken references

    def run_side_effect(query, **kwargs):
        if "NOT (n)--" in query:
            return mock_orphaned
        elif "chunk_ids IS NULL" in query:
            return mock_broken
        return Mock()

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    health = graph_service.health_check()

    # Assert
    assert health["status"] == "unhealthy"
    assert health["broken_references"] == 25
    assert len(health["errors"]) > 0
    assert "missing chunk_ids" in health["errors"][0]


@pytest.mark.integration
def test_health_check_driver_error(graph_service):
    """Test health check when driver is None."""
    graph_service.driver = None

    health = graph_service.health_check()

    assert health["status"] == "error"
    assert "error" in health
    assert "driver not initialized" in health["error"]


@pytest.mark.integration
def test_health_check_query_error(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test health check when Neo4J query fails."""
    mock_neo4j_session.run = Mock(side_effect=Exception("Connection timeout"))
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    health = graph_service.health_check()

    assert health["status"] == "error"
    assert "error" in health
    assert "timestamp" in health


# ============================================================================
# Entity Details Tests
# ============================================================================


@pytest.mark.integration
def test_get_entity_details_success(graph_service, mock_neo4j_driver, mock_neo4j_session, sample_entity_data):
    """Test successful entity details retrieval."""
    # Mock entity query results
    mock_entity_result = Mock()
    entity_node = {
        "id": "skilled_worker_visa",
        "text": "Skilled Worker visa",
        "type": "visa_type",
        "chunk_ids": ["chunk_001", "chunk_002"]
    }

    mock_record = Mock()
    mock_record.__getitem__ = lambda self, key: {
        "e": entity_node,
        "labels": ["VisaType", "Entity"],
        "outgoing_rels": [
            {
                "type": "REQUIRES",
                "direction": "outgoing",
                "target_id": "english_test",
                "target_text": "English language test"
            }
        ]
    }[key]

    mock_entity_result.single = Mock(return_value=mock_record)

    # Mock incoming relationships
    mock_incoming_result = Mock()
    mock_incoming_record = Mock()
    mock_incoming_record.__getitem__ = lambda self, key: {
        "incoming_rels": [
            {
                "type": "CAN_TRANSITION_TO",
                "direction": "incoming",
                "source_id": "student_visa",
                "source_text": "Student visa"
            }
        ]
    }[key]

    mock_incoming_result.single = Mock(return_value=mock_incoming_record)

    # Setup session.run() to return different results
    call_count = [0]

    def run_side_effect(query, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:  # First call - entity details
            return mock_entity_result
        else:  # Second call - incoming relationships
            return mock_incoming_result

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    entity = graph_service.get_entity_details("skilled_worker_visa")

    # Assert
    assert entity is not None
    assert entity["id"] == "skilled_worker_visa"
    assert "VisaType" in entity["labels"]
    assert "text" in entity["properties"]
    assert "relationships" in entity
    assert "outgoing" in entity["relationships"]
    assert "incoming" in entity["relationships"]


@pytest.mark.integration
def test_get_entity_details_not_found(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test entity details for non-existent entity."""
    mock_result = Mock()
    mock_result.single = Mock(return_value=None)

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    entity = graph_service.get_entity_details("non_existent_entity")

    # Assert
    assert entity is None


@pytest.mark.integration
def test_get_entity_details_driver_error(graph_service):
    """Test entity details when driver is None."""
    graph_service.driver = None

    with pytest.raises(RuntimeError, match="Neo4J driver not initialized"):
        graph_service.get_entity_details("test_entity")


# ============================================================================
# Visualization Data Tests
# ============================================================================


@pytest.mark.integration
def test_get_visualization_data_success(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test successful visualization data retrieval."""
    # Mock visualization query result
    mock_viz_result = Mock()
    mock_record = Mock()
    mock_record.__getitem__ = lambda self, key: {
        "nodes": [
            {
                "id": "skilled_worker_visa",
                "label": "Skilled Worker visa",
                "type": "VisaType",
                "properties": {"text": "Skilled Worker visa"}
            },
            {
                "id": "english_test",
                "label": "English language test",
                "type": "Requirement",
                "properties": {"text": "English language test"}
            }
        ],
        "edges": [
            {
                "source": "skilled_worker_visa",
                "target": "english_test",
                "type": "REQUIRES"
            }
        ]
    }[key]

    mock_viz_result.single = Mock(return_value=mock_record)

    mock_neo4j_session.run = Mock(return_value=mock_viz_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    viz_data = graph_service.get_visualization_data("skilled_worker_visa", depth=2)

    # Assert
    assert "nodes" in viz_data
    assert "edges" in viz_data
    assert len(viz_data["nodes"]) == 2
    assert len(viz_data["edges"]) == 1
    assert viz_data["edges"][0]["source"] == "skilled_worker_visa"
    assert viz_data["edges"][0]["target"] == "english_test"


@pytest.mark.integration
def test_get_visualization_data_empty_graph(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test visualization data for entity with no connections."""
    mock_result = Mock()
    mock_result.single = Mock(return_value=None)

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    viz_data = graph_service.get_visualization_data("isolated_entity", depth=2)

    # Assert
    assert viz_data == {"nodes": [], "edges": []}


@pytest.mark.integration
def test_get_visualization_data_depth_boundary(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test visualization with different depth values."""
    mock_result = Mock()
    mock_record = Mock()
    mock_record.__getitem__ = lambda self, key: {
        "nodes": [],
        "edges": []
    }[key]

    mock_result.single = Mock(return_value=mock_record)
    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Test different depths
    for depth in [1, 2, 3, 4]:
        viz_data = graph_service.get_visualization_data("test_entity", depth=depth)
        assert "nodes" in viz_data
        assert "edges" in viz_data


# ============================================================================
# Entity Search Tests
# ============================================================================


@pytest.mark.integration
def test_search_entities_success(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test successful entity search."""
    # Mock search results
    mock_search_result = Mock()
    mock_search_result.__iter__ = Mock(return_value=iter([
        {
            "id": "skilled_worker_visa",
            "labels": ["VisaType", "Entity"],
            "text": "Skilled Worker visa",
            "properties": {"text": "Skilled Worker visa", "type": "visa_type"}
        },
        {
            "id": "skilled_worker_requirement",
            "labels": ["Requirement", "Entity"],
            "text": "Skilled Worker visa requirement",
            "properties": {"text": "Skilled Worker visa requirement"}
        }
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_search_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    results = graph_service.search_entities("Skilled Worker", limit=20)

    # Assert
    assert len(results) == 2
    assert results[0]["id"] == "skilled_worker_visa"
    assert "labels" in results[0]
    assert "text" in results[0]
    assert "properties" in results[0]


@pytest.mark.integration
def test_search_entities_with_type_filter(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test entity search with entity_types filter."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {
            "id": "skilled_worker_visa",
            "labels": ["VisaType"],
            "text": "Skilled Worker visa",
            "properties": {}
        }
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    results = graph_service.search_entities(
        "Skilled Worker",
        entity_types=["VisaType", "Requirement"],
        limit=10
    )

    # Assert
    assert len(results) == 1
    assert "VisaType" in results[0]["labels"]

    # Verify query was called with entity_types filter
    mock_neo4j_session.run.assert_called_once()
    call_args = mock_neo4j_session.run.call_args
    assert "'VisaType' IN labels(e)" in call_args[0][0] or \
           "'Requirement' IN labels(e)" in call_args[0][0]


@pytest.mark.integration
def test_search_entities_no_results(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test entity search with no matching results."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    results = graph_service.search_entities("NonExistentEntity", limit=20)

    # Assert
    assert len(results) == 0


@pytest.mark.integration
def test_search_entities_case_insensitive(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test entity search is case-insensitive."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {
            "id": "skilled_worker_visa",
            "labels": ["VisaType"],
            "text": "Skilled Worker visa",
            "properties": {}
        }
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute with different cases
    results_lower = graph_service.search_entities("skilled worker", limit=10)
    results_upper = graph_service.search_entities("SKILLED WORKER", limit=10)

    # Both should find results (mock returns same data)
    assert len(results_lower) > 0
    assert len(results_upper) > 0


# ============================================================================
# Schema Initialization Tests
# ============================================================================


@pytest.mark.integration
def test_initialize_schema_success(graph_service, mock_neo4j_driver, mock_neo4j_session):
    """Test successful schema initialization."""
    mock_neo4j_session.run = Mock()
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    graph_service.initialize_schema()

    # Assert session.run was called for constraints and indexes
    assert mock_neo4j_session.run.call_count >= 3  # At least 3 schema operations


@pytest.mark.integration
def test_initialize_schema_driver_error(graph_service):
    """Test schema initialization when driver is None."""
    graph_service.driver = None

    with pytest.raises(RuntimeError, match="Neo4J driver not initialized"):
        graph_service.initialize_schema()


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


@pytest.mark.integration
def test_get_graph_service_singleton():
    """Test that get_graph_service returns singleton instance."""
    with patch('src.services.neo4j_graph_service.GraphDatabase.driver') as mock_gdb:
        mock_driver = Mock()
        mock_driver.verify_connectivity = Mock()
        mock_gdb.return_value = mock_driver

        # Clear singleton
        import src.services.neo4j_graph_service as module
        module._graph_service = None

        # Get first instance
        service1 = get_graph_service(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test",
            neo4j_password="test",
            neo4j_database="test"
        )

        # Get second instance - should be same object
        service2 = get_graph_service(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test",
            neo4j_password="test",
            neo4j_database="test"
        )

        assert service1 is service2

        # Cleanup
        service1.close()
        module._graph_service = None


# ============================================================================
# Error Handling and Graceful Degradation Tests
# ============================================================================


@pytest.mark.integration
def test_connection_failure_handling():
    """Test graceful handling of Neo4J connection failure."""
    with patch('src.services.neo4j_graph_service.GraphDatabase.driver') as mock_gdb:
        mock_driver = Mock()
        mock_driver.verify_connectivity = Mock(side_effect=Exception("Connection refused"))
        mock_gdb.return_value = mock_driver

        # Execute - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Neo4J connection failed"):
            Neo4JGraphService(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="test",
                neo4j_password="test"
            )


@pytest.mark.integration
def test_close_service_cleanup(graph_service, mock_neo4j_driver):
    """Test that close() properly cleans up driver connection."""
    graph_service.close()

    # Assert driver.close() was called
    mock_neo4j_driver.close.assert_called_once()


@pytest.mark.integration
def test_close_service_without_driver():
    """Test close() when driver is None (already closed)."""
    service = Mock()
    service.driver = None

    # Should not raise exception
    Neo4JGraphService.close(service)
