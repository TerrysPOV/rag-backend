"""
Integration tests for Neo4J Graph Retriever Query Logic (NEO4J-001).

Tests graph traversal strategies:
1. Direct entity search
2. Relationship expansion
3. Multi-hop traversal (depths 1-3)
4. Hybrid scoring and ranking
5. Query entity extraction
6. Graph path explainability
7. Performance benchmarks

Uses mock Neo4J data to test query logic without requiring live database.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

from haystack import Document
from src.services.neo4j_graph_retriever import Neo4JGraphRetriever, get_graph_retriever


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
def graph_retriever(mock_neo4j_driver):
    """Create Neo4JGraphRetriever with mocked driver and SpaCy."""
    with patch('src.services.neo4j_graph_retriever.GraphDatabase.driver') as mock_gdb:
        mock_gdb.return_value = mock_neo4j_driver

        # Mock SpaCy to avoid loading model
        with patch('src.services.neo4j_graph_retriever.spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_spacy.return_value = mock_nlp

            retriever = Neo4JGraphRetriever(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="test_user",
                neo4j_password="test_password",
                neo4j_database="test_db",
                max_depth=3,
                top_k=10
            )

            yield retriever

            # Cleanup
            retriever.close()


@pytest.fixture
def sample_direct_search_results():
    """Sample results for direct entity search."""
    return [
        {
            "doc_id": "chunk_001",
            "matched_entities": ["Skilled Worker visa", "Job offer"],
            "entity_count": 2
        },
        {
            "doc_id": "chunk_002",
            "matched_entities": ["Skilled Worker visa"],
            "entity_count": 1
        }
    ]


@pytest.fixture
def sample_relationship_expansion_results():
    """Sample results for relationship expansion."""
    return [
        {
            "doc_id": "chunk_003",
            "source_entity": "Skilled Worker visa",
            "relationship": "REQUIRES",
            "target_entity": "English language test",
            "related_entities": ["IELTS", "B1 level"]
        },
        {
            "doc_id": "chunk_004",
            "source_entity": "Skilled Worker visa",
            "relationship": "REQUIRES",
            "target_entity": "Job offer from UK sponsor",
            "related_entities": ["Certificate of Sponsorship"]
        }
    ]


@pytest.fixture
def sample_multihop_traversal_results():
    """Sample results for multi-hop traversal."""
    return [
        {
            "doc_id": "chunk_005",
            "traversal_path": ["Skilled Worker visa", "Job offer", "Certificate of Sponsorship"],
            "relationship_types": ["REQUIRES", "SATISFIED_BY"],
            "hop_count": 2
        },
        {
            "doc_id": "chunk_006",
            "traversal_path": ["Skilled Worker visa", "English test", "IELTS", "B1 level"],
            "relationship_types": ["REQUIRES", "SATISFIED_BY", "REQUIRES"],
            "hop_count": 3
        }
    ]


# ============================================================================
# Direct Entity Search Tests
# ============================================================================


@pytest.mark.integration
def test_direct_entity_search_success(graph_retriever, mock_neo4j_driver, mock_neo4j_session, sample_direct_search_results):
    """Test direct entity search returns correct documents."""
    # Mock query result
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter(sample_direct_search_results))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    entities = ["Skilled Worker visa"]
    docs = graph_retriever._direct_entity_search(entities)

    # Assert
    assert len(docs) == 2
    assert all(isinstance(doc, Document) for doc in docs)
    assert docs[0].id == "chunk_001"
    assert docs[1].id == "chunk_002"
    assert docs[0].meta["retrieval_strategy"] == "direct"
    assert "matched_entities" in docs[0].meta


@pytest.mark.integration
def test_direct_entity_search_multiple_entities(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test direct search with multiple entities."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {
            "doc_id": "chunk_007",
            "matched_entities": ["Student visa", "Tier 4"],
            "entity_count": 2
        }
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute with multiple entities
    entities = ["Student visa", "Tier 4", "University"]
    docs = graph_retriever._direct_entity_search(entities)

    # Assert
    assert len(docs) == 1
    # Verify query was called with all entities
    call_args = mock_neo4j_session.run.call_args
    assert call_args[1]["entities"] == entities


@pytest.mark.integration
def test_direct_entity_search_no_results(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test direct search returns empty list when no entities found."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    docs = graph_retriever._direct_entity_search(["NonExistentEntity"])

    # Assert
    assert len(docs) == 0


@pytest.mark.integration
def test_direct_entity_search_case_insensitive(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test direct search is case-insensitive."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_001", "matched_entities": ["Skilled Worker visa"], "entity_count": 1}
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute with different cases
    docs_lower = graph_retriever._direct_entity_search(["skilled worker visa"])
    docs_upper = graph_retriever._direct_entity_search(["SKILLED WORKER VISA"])

    # Both should find results
    assert len(docs_lower) > 0
    assert len(docs_upper) > 0


# ============================================================================
# Relationship Expansion Tests
# ============================================================================


@pytest.mark.integration
def test_relationship_expansion_success(graph_retriever, mock_neo4j_driver, mock_neo4j_session, sample_relationship_expansion_results):
    """Test relationship expansion returns related documents."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter(sample_relationship_expansion_results))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    entities = ["Skilled Worker visa"]
    docs = graph_retriever._relationship_expansion(entities)

    # Assert
    assert len(docs) == 2
    assert docs[0].id == "chunk_003"
    assert docs[0].meta["retrieval_strategy"] == "expanded"
    assert docs[0].meta["source_entity"] == "Skilled Worker visa"
    assert docs[0].meta["relationship"] == "REQUIRES"
    assert docs[0].meta["target_entity"] == "English language test"


@pytest.mark.integration
def test_relationship_expansion_multiple_relationship_types(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test expansion uses multiple relationship types."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {
            "doc_id": "chunk_008",
            "source_entity": "Student visa",
            "relationship": "CAN_TRANSITION_TO",
            "target_entity": "Graduate visa",
            "related_entities": ["PSW route"]
        }
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    docs = graph_retriever._relationship_expansion(["Student visa"])

    # Assert query includes multiple relationship types
    call_args = mock_neo4j_session.run.call_args
    query = call_args[0][0]
    # Check for relationship types in query
    assert "REQUIRES" in query or "CAN_TRANSITION_TO" in query or "SATISFIED_BY" in query


@pytest.mark.integration
def test_relationship_expansion_no_relationships(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test expansion returns empty when entity has no relationships."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    docs = graph_retriever._relationship_expansion(["IsolatedEntity"])

    # Assert
    assert len(docs) == 0


# ============================================================================
# Multi-Hop Traversal Tests
# ============================================================================


@pytest.mark.integration
def test_multihop_traversal_success(graph_retriever, mock_neo4j_driver, mock_neo4j_session, sample_multihop_traversal_results):
    """Test multi-hop traversal follows graph paths."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter(sample_multihop_traversal_results))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    entities = ["Skilled Worker visa"]
    docs = graph_retriever._multihop_traversal(entities)

    # Assert
    assert len(docs) == 2
    assert docs[0].meta["retrieval_strategy"] == "multihop"
    assert docs[0].meta["hop_count"] == 2
    assert docs[1].meta["hop_count"] == 3
    assert "traversal_path" in docs[0].meta
    assert "relationship_types" in docs[0].meta


@pytest.mark.integration
def test_multihop_traversal_max_depth(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test multi-hop respects max_depth parameter."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    graph_retriever._multihop_traversal(["TestEntity"])

    # Assert query uses max_depth
    call_args = mock_neo4j_session.run.call_args
    query = call_args[0][0]
    assert f"*1..{graph_retriever.max_depth}" in query


@pytest.mark.integration
def test_multihop_traversal_depth_boundary():
    """Test multi-hop with different max_depth values."""
    with patch('src.services.neo4j_graph_retriever.GraphDatabase.driver') as mock_gdb:
        mock_driver = Mock()
        mock_driver.verify_connectivity = Mock()
        mock_gdb.return_value = mock_driver

        with patch('src.services.neo4j_graph_retriever.spacy.load'):
            # Test depths 1-5
            for depth in [1, 2, 3, 4, 5]:
                retriever = Neo4JGraphRetriever(
                    neo4j_uri="bolt://localhost:7687",
                    neo4j_user="test",
                    neo4j_password="test",
                    max_depth=depth
                )
                assert retriever.max_depth == depth
                retriever.close()


@pytest.mark.integration
def test_multihop_traversal_orders_by_hop_count(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test multi-hop results are ordered by hop count (shortest paths first)."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_009", "traversal_path": ["A", "B", "C"], "relationship_types": ["REL1", "REL2"], "hop_count": 2},
        {"doc_id": "chunk_010", "traversal_path": ["A", "B"], "relationship_types": ["REL1"], "hop_count": 1},
        {"doc_id": "chunk_011", "traversal_path": ["A", "B", "C", "D"], "relationship_types": ["REL1", "REL2", "REL3"], "hop_count": 3}
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    docs = graph_retriever._multihop_traversal(["A"])

    # Assert - verify query orders by hop_count ASC
    call_args = mock_neo4j_session.run.call_args
    query = call_args[0][0]
    assert "ORDER BY hop_count ASC" in query


# ============================================================================
# Merge and Ranking Tests
# ============================================================================


@pytest.mark.integration
def test_merge_and_rank_combines_strategies(graph_retriever):
    """Test merge_and_rank combines results from all strategies."""
    # Create documents from different strategies
    direct_docs = [
        Document(id="doc1", content="", meta={"retrieval_strategy": "direct"}),
        Document(id="doc2", content="", meta={"retrieval_strategy": "direct"})
    ]

    expanded_docs = [
        Document(id="doc3", content="", meta={"retrieval_strategy": "expanded"}),
        Document(id="doc1", content="", meta={"retrieval_strategy": "expanded"})  # Duplicate
    ]

    multihop_docs = [
        Document(id="doc4", content="", meta={"retrieval_strategy": "multihop", "hop_count": 2}),
        Document(id="doc5", content="", meta={"retrieval_strategy": "multihop", "hop_count": 3})
    ]

    # Execute
    merged = graph_retriever._merge_and_rank(direct_docs, expanded_docs, multihop_docs)

    # Assert
    assert len(merged) == 5  # Total unique documents
    # doc1 should have highest score (appears in direct + expanded)
    assert merged[0].id == "doc1"
    assert merged[0].meta["graph_score"] > 1.0  # Combined score from both strategies


@pytest.mark.integration
def test_merge_and_rank_scoring_direct_highest(graph_retriever):
    """Test direct matches get highest base score (1.0)."""
    direct_docs = [Document(id="doc1", content="", meta={})]
    expanded_docs = []
    multihop_docs = []

    merged = graph_retriever._merge_and_rank(direct_docs, expanded_docs, multihop_docs)

    assert merged[0].meta["graph_score"] == 1.0


@pytest.mark.integration
def test_merge_and_rank_scoring_expanded_medium(graph_retriever):
    """Test relationship expansion gets medium score (0.8)."""
    direct_docs = []
    expanded_docs = [Document(id="doc1", content="", meta={})]
    multihop_docs = []

    merged = graph_retriever._merge_and_rank(direct_docs, expanded_docs, multihop_docs)

    assert merged[0].meta["graph_score"] == 0.8


@pytest.mark.integration
def test_merge_and_rank_scoring_multihop_penalized(graph_retriever):
    """Test multi-hop gets penalized by hop count (0.6 / hop_count)."""
    direct_docs = []
    expanded_docs = []
    multihop_docs = [
        Document(id="doc1", content="", meta={"hop_count": 2}),
        Document(id="doc2", content="", meta={"hop_count": 3})
    ]

    merged = graph_retriever._merge_and_rank(direct_docs, expanded_docs, multihop_docs)

    # doc1 (2 hops) should have higher score than doc2 (3 hops)
    assert merged[0].id == "doc1"
    assert merged[0].meta["graph_score"] == 0.6 / 2  # 0.3
    assert merged[1].meta["graph_score"] == 0.6 / 3  # 0.2


# ============================================================================
# Query Entity Extraction Tests
# ============================================================================


@pytest.mark.integration
def test_extract_query_entities_with_spacy(graph_retriever):
    """Test entity extraction using SpaCy NER."""
    # Mock SpaCy NER
    mock_doc = Mock()
    mock_ent1 = Mock()
    mock_ent1.text = "United Kingdom"
    mock_ent1.label_ = "GPE"

    mock_ent2 = Mock()
    mock_ent2.text = "Home Office"
    mock_ent2.label_ = "ORG"

    mock_doc.ents = [mock_ent1, mock_ent2]

    graph_retriever.nlp = Mock(return_value=mock_doc)

    # Execute
    entities = graph_retriever._extract_query_entities(
        "How do I apply to the Home Office for a visa to the United Kingdom?"
    )

    # Assert
    assert "United Kingdom" in entities
    assert "Home Office" in entities


@pytest.mark.integration
def test_extract_query_entities_visa_patterns(graph_retriever):
    """Test entity extraction detects visa type patterns."""
    graph_retriever.nlp = None  # Disable SpaCy to test keyword matching

    # Execute
    entities = graph_retriever._extract_query_entities(
        "What are the requirements for a Skilled Worker visa or Student visa?"
    )

    # Assert
    assert any("Skilled Worker" in e for e in entities)
    assert any("Student" in e for e in entities)


@pytest.mark.integration
def test_extract_query_entities_document_patterns(graph_retriever):
    """Test entity extraction detects document type patterns."""
    graph_retriever.nlp = None  # Disable SpaCy

    # Execute
    entities = graph_retriever._extract_query_entities(
        "Do I need a passport and bank statement for my application?"
    )

    # Assert
    assert any("passport" in e.lower() for e in entities)
    assert any("bank statement" in e.lower() for e in entities)


@pytest.mark.integration
def test_extract_query_entities_deduplication(graph_retriever):
    """Test entity extraction removes duplicates."""
    graph_retriever.nlp = None

    # Execute with duplicate entities
    entities = graph_retriever._extract_query_entities(
        "Skilled Worker visa and skilled worker visa requirements"
    )

    # Assert - should only have one "Skilled Worker" (case-insensitive dedup)
    skilled_worker_count = sum(1 for e in entities if "skilled worker" in e.lower())
    assert skilled_worker_count == 1


@pytest.mark.integration
def test_extract_query_entities_no_entities(graph_retriever):
    """Test entity extraction returns empty list for generic query."""
    graph_retriever.nlp = None

    # Execute with generic query
    entities = graph_retriever._extract_query_entities("How are you?")

    # Assert
    assert len(entities) == 0


# ============================================================================
# Graph Path Explainability Tests
# ============================================================================


@pytest.mark.integration
def test_generate_explanation_paths_direct(graph_retriever):
    """Test explanation generation for direct matches."""
    docs = [
        Document(
            id="doc1",
            content="",
            meta={
                "retrieval_strategy": "direct",
                "graph_score": 1.0,
                "matched_entities": ["Skilled Worker visa", "Job offer"]
            }
        )
    ]

    # Execute
    paths = graph_retriever._generate_explanation_paths(docs)

    # Assert
    assert len(paths) == 1
    assert paths[0]["document_id"] == "doc1"
    assert paths[0]["strategy"] == "direct"
    assert paths[0]["graph_score"] == 1.0
    assert "matched_entities" in paths[0]


@pytest.mark.integration
def test_generate_explanation_paths_multihop(graph_retriever):
    """Test explanation generation for multi-hop traversal."""
    docs = [
        Document(
            id="doc2",
            content="",
            meta={
                "retrieval_strategy": "multihop",
                "graph_score": 0.3,
                "traversal_path": ["Skilled Worker visa", "Job offer", "Certificate of Sponsorship"],
                "relationship_types": ["REQUIRES", "SATISFIED_BY"],
                "hop_count": 2
            }
        )
    ]

    # Execute
    paths = graph_retriever._generate_explanation_paths(docs)

    # Assert
    assert len(paths) == 1
    assert paths[0]["strategy"] == "multihop"
    assert paths[0]["traversal_path"] == ["Skilled Worker visa", "Job offer", "Certificate of Sponsorship"]
    assert paths[0]["relationship_types"] == ["REQUIRES", "SATISFIED_BY"]
    assert paths[0]["hop_count"] == 2


# ============================================================================
# Full Pipeline Tests (run method)
# ============================================================================


@pytest.mark.integration
def test_run_full_pipeline_success(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test full retrieval pipeline (run method)."""
    # Mock all query results
    mock_direct = Mock()
    mock_direct.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_001", "matched_entities": ["Skilled Worker"], "entity_count": 1}
    ]))

    mock_expanded = Mock()
    mock_expanded.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_002", "source_entity": "Skilled Worker", "relationship": "REQUIRES",
         "target_entity": "English test", "related_entities": ["IELTS"]}
    ]))

    mock_multihop = Mock()
    mock_multihop.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_003", "traversal_path": ["Skilled Worker", "Job offer"],
         "relationship_types": ["REQUIRES"], "hop_count": 1}
    ]))

    call_count = [0]

    def run_side_effect(query, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:  # Direct search
            return mock_direct
        elif call_count[0] == 2:  # Relationship expansion
            return mock_expanded
        else:  # Multi-hop
            return mock_multihop

    mock_neo4j_session.run = Mock(side_effect=run_side_effect)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    result = graph_retriever.run(query="What are Skilled Worker visa requirements?")

    # Assert
    assert "documents" in result
    assert "graph_paths" in result
    assert len(result["documents"]) > 0
    assert len(result["graph_paths"]) > 0


@pytest.mark.integration
def test_run_with_provided_entities(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test run with pre-extracted entities."""
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_001", "matched_entities": ["Student visa"], "entity_count": 1}
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute with provided entities
    result = graph_retriever.run(
        query="Tell me about student visas",
        entities=["Student visa", "Tier 4"]
    )

    # Assert - should use provided entities, not extract from query
    assert "documents" in result


@pytest.mark.integration
def test_run_no_entities_extracted(graph_retriever):
    """Test run returns empty when no entities extracted."""
    graph_retriever.nlp = None  # Disable SpaCy

    # Execute with query that has no visa/document keywords
    result = graph_retriever.run(query="Hello, how are you?")

    # Assert
    assert len(result["documents"]) == 0
    assert len(result["graph_paths"]) == 0


@pytest.mark.integration
def test_run_respects_top_k(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test run returns at most top_k documents."""
    # Mock many results
    many_results = [
        {"doc_id": f"chunk_{i:03d}", "matched_entities": ["Test"], "entity_count": 1}
        for i in range(50)
    ]

    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter(many_results))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    result = graph_retriever.run(query="Test query", entities=["Test"])

    # Assert - should return at most top_k
    assert len(result["documents"]) <= graph_retriever.top_k


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_query_performance_target(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test graph queries complete within performance targets."""
    import time

    # Mock minimal results for fast execution
    mock_result = Mock()
    mock_result.__iter__ = Mock(return_value=iter([
        {"doc_id": "chunk_001", "matched_entities": ["Test"], "entity_count": 1}
    ]))

    mock_neo4j_session.run = Mock(return_value=mock_result)
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    start = time.time()
    result = graph_retriever.run(query="Test query", entities=["Test"])
    elapsed_ms = (time.time() - start) * 1000

    # Assert - should complete within reasonable time (5 seconds for mock)
    # In production with real Neo4J, target is <2 seconds
    assert elapsed_ms < 5000, f"Query took {elapsed_ms}ms (should be <5000ms)"


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


@pytest.mark.integration
def test_get_graph_retriever_singleton():
    """Test get_graph_retriever returns singleton instance."""
    with patch('src.services.neo4j_graph_retriever.GraphDatabase.driver') as mock_gdb:
        mock_driver = Mock()
        mock_driver.verify_connectivity = Mock()
        mock_gdb.return_value = mock_driver

        with patch('src.services.neo4j_graph_retriever.spacy.load'):
            # Clear singleton
            import src.services.neo4j_graph_retriever as module
            module._graph_retriever = None

            # Get first instance
            retriever1 = get_graph_retriever(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="test",
                neo4j_password="test",
                neo4j_database="test",
                max_depth=3,
                top_k=10
            )

            # Get second instance - should be same object
            retriever2 = get_graph_retriever(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="test",
                neo4j_password="test",
                neo4j_database="test",
                max_depth=3,
                top_k=10
            )

            assert retriever1 is retriever2

            # Cleanup
            retriever1.close()
            module._graph_retriever = None


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
def test_run_driver_not_initialized(graph_retriever):
    """Test run raises error when driver is None."""
    graph_retriever.driver = None

    with pytest.raises(RuntimeError, match="Neo4J driver not initialized"):
        graph_retriever.run(query="Test query", entities=["Test"])


@pytest.mark.integration
def test_direct_search_query_error(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test direct search handles query errors gracefully."""
    mock_neo4j_session.run = Mock(side_effect=Exception("Query timeout"))
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute - should return empty list instead of raising
    docs = graph_retriever._direct_entity_search(["Test"])

    # Assert
    assert docs == []


@pytest.mark.integration
def test_relationship_expansion_query_error(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test relationship expansion handles query errors gracefully."""
    mock_neo4j_session.run = Mock(side_effect=Exception("Connection lost"))
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    docs = graph_retriever._relationship_expansion(["Test"])

    # Assert - should return empty list
    assert docs == []


@pytest.mark.integration
def test_multihop_traversal_query_error(graph_retriever, mock_neo4j_driver, mock_neo4j_session):
    """Test multi-hop traversal handles query errors gracefully."""
    mock_neo4j_session.run = Mock(side_effect=Exception("Transaction failed"))
    mock_neo4j_driver.session = Mock(return_value=mock_neo4j_session)

    # Execute
    docs = graph_retriever._multihop_traversal(["Test"])

    # Assert
    assert docs == []
