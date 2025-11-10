"""
Optimized Neo4J Cypher Queries - Performance Tuning

This module contains optimized Cypher queries for Neo4J graph traversals.
These queries replace the inefficient queries in neo4j_graph_retriever.py
and neo4j_graph_service.py.

Performance improvements:
- Full-text indexes instead of CONTAINS with toLower()
- Directed relationships instead of undirected
- LIMIT clauses to prevent result explosion
- Composite indexes for multi-field queries
- Efficient aggregation and path traversal

Usage:
    from src.database.neo4j_optimized_queries import NEO4J_QUERIES

    # Execute optimized query
    result = session.run(
        NEO4J_QUERIES["direct_entity_search"],
        entities=["Skilled Worker", "Student"],
        limit=20
    )
"""

# ============================================================================
# Schema Initialization Queries
# ============================================================================

SCHEMA_QUERIES = {
    # Create unique constraint on Entity.id
    "create_entity_id_constraint": """
        CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
        FOR (e:Entity) REQUIRE e.id IS UNIQUE
    """,
    # Create full-text index for case-insensitive text search
    "create_fulltext_index": """
        CREATE FULLTEXT INDEX entity_text_fulltext IF NOT EXISTS
        FOR (e:Entity) ON EACH [e.text, e.name]
    """,
    # Create standard index on chunk_ids for health checks
    "create_chunk_ids_index": """
        CREATE INDEX entity_chunk_ids IF NOT EXISTS
        FOR (e:Entity) ON (e.chunk_ids)
    """,
    # Create relationship type indexes
    "create_requires_index": """
        CREATE INDEX rel_requires IF NOT EXISTS
        FOR ()-[r:REQUIRES]-() ON (type(r))
    """,
    "create_satisfied_by_index": """
        CREATE INDEX rel_satisfied_by IF NOT EXISTS
        FOR ()-[r:SATISFIED_BY]-() ON (type(r))
    """,
    "create_contains_entity_index": """
        CREATE INDEX rel_contains_entity IF NOT EXISTS
        FOR ()-[r:CONTAINS_ENTITY]-() ON (type(r))
    """,
    # Composite index for visualization queries
    "create_composite_id_labels_index": """
        CREATE INDEX entity_id_type IF NOT EXISTS
        FOR (e:Entity) ON (e.id, e.type)
    """,
}

# ============================================================================
# Retrieval Queries (Optimized)
# ============================================================================

NEO4J_QUERIES = {
    # ========================================================================
    # Direct Entity Search (Optimized with Full-Text Index)
    # ========================================================================
    "direct_entity_search": """
        // Use full-text index for case-insensitive search
        UNWIND $entities AS entity_text
        CALL db.index.fulltext.queryNodes('entity_text_fulltext', entity_text)
        YIELD node AS e, score

        // Get documents containing this entity
        MATCH (d)-[:CONTAINS_ENTITY]->(e)

        // Aggregate results
        RETURN DISTINCT d.id AS doc_id,
               collect(DISTINCT e.text)[..5] AS matched_entities,
               count(DISTINCT e) AS entity_count,
               max(score) AS max_score
        ORDER BY max_score DESC, entity_count DESC
        LIMIT $limit
    """,
    # ========================================================================
    # Relationship Expansion (Optimized with Directed Relationships)
    # ========================================================================
    "relationship_expansion": """
        // Use full-text index for starting entities
        UNWIND $entities AS entity_text
        CALL db.index.fulltext.queryNodes('entity_text_fulltext', entity_text)
        YIELD node AS e, score

        // Directed relationship traversal with type constraints
        MATCH (e)-[r:REQUIRES|SATISFIED_BY|DEPENDS_ON|APPLIES_IF|CAN_TRANSITION_TO]->(related:Entity)

        // Get documents containing related entities
        MATCH (d)-[:CONTAINS_ENTITY]->(related)

        // Aggregate efficiently
        RETURN DISTINCT d.id AS doc_id,
               e.text AS source_entity,
               type(r) AS relationship,
               related.text AS target_entity,
               collect(DISTINCT related.text)[..3] AS related_entities,
               score
        ORDER BY score DESC
        LIMIT $limit
    """,
    # ========================================================================
    # Multi-Hop Traversal (Optimized with Direction and Depth Control)
    # ========================================================================
    "multihop_traversal": """
        // Use full-text index for starting entities
        UNWIND $entities AS entity_text
        CALL db.index.fulltext.queryNodes('entity_text_fulltext', entity_text)
        YIELD node AS start, score

        // Directed multi-hop with relationship type filter
        // Note: Using '->' for direction prevents path explosion
        MATCH path = (start)-[r:REQUIRES|SATISFIED_BY|DEPENDS_ON|APPLIES_IF*1..{max_depth}]->(end:Entity)
        WHERE length(path) <= {max_depth}

        // Get documents containing end entity
        MATCH (d)-[:CONTAINS_ENTITY]->(end)

        // Aggregate with shortest path preference
        WITH d.id AS doc_id,
             min(length(path)) AS hop_count,
             [node IN nodes(path) | coalesce(node.text, node.name)][..5] AS traversal_path,
             [rel IN relationships(path) | type(rel)][..5] AS relationship_types,
             score

        RETURN DISTINCT doc_id,
               hop_count,
               traversal_path,
               relationship_types,
               score
        ORDER BY hop_count ASC, score DESC
        LIMIT $limit
    """,
    # ========================================================================
    # Entity Search with Pagination (Optimized)
    # ========================================================================
    "entity_search_paginated": """
        // Get total count first (for pagination metadata)
        CALL {
            CALL db.index.fulltext.queryNodes('entity_text_fulltext', $search_term)
            YIELD node
            RETURN count(node) AS total
        }

        // Get page of results
        CALL db.index.fulltext.queryNodes('entity_text_fulltext', $search_term)
        YIELD node, score

        // Apply type filter if provided
        WHERE $entity_types IS NULL OR any(label IN labels(node) WHERE label IN $entity_types)

        RETURN node.id AS id,
               labels(node) AS labels,
               coalesce(node.text, node.name) AS text,
               properties(node) AS properties,
               score,
               total
        ORDER BY score DESC
        SKIP $skip
        LIMIT $page_size
    """,
    # ========================================================================
    # Visualization Data (Optimized with Result Limits)
    # ========================================================================
    "visualization_data": """
        // Directed traversal with depth limit
        MATCH path = (root {id: $entity_id})-[r:REQUIRES|SATISFIED_BY|CONTAINS_ENTITY*0..{depth}]->(node)
        WHERE length(path) <= {depth}

        // Limit paths to prevent explosion
        WITH path, length(path) AS path_length
        ORDER BY path_length ASC
        LIMIT 500

        // Extract unique nodes and edges
        WITH collect(path) AS paths
        UNWIND paths AS p
        WITH nodes(p) AS path_nodes, relationships(p) AS path_rels

        // Collect unique nodes
        UNWIND path_nodes AS n
        WITH collect(DISTINCT {
            id: n.id,
            label: coalesce(n.text, n.name, n.id),
            type: labels(n)[0],
            properties: properties(n)
        }) AS nodes, path_rels

        // Collect unique edges
        UNWIND path_rels AS r
        WITH nodes, collect(DISTINCT {
            source: startNode(r).id,
            target: endNode(r).id,
            type: type(r)
        }) AS edges

        // Return with client-side pagination limits
        RETURN nodes[..200] AS nodes, edges[..500] AS edges
    """,
    # ========================================================================
    # Graph Statistics (Optimized with Parallel Aggregation)
    # ========================================================================
    "graph_statistics": """
        // Get node counts by type (parallel)
        CALL {
            MATCH (n)
            RETURN labels(n) AS labels, count(n) AS count
        }

        // Get relationship counts by type (parallel)
        CALL {
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(r) AS rel_count
        }

        // Get totals (parallel)
        CALL {
            MATCH (n) RETURN count(n) AS total_nodes
        }

        CALL {
            MATCH ()-[r]->() RETURN count(r) AS total_rels
        }

        // Return aggregated stats
        RETURN labels, count, rel_type, rel_count, total_nodes, total_rels
    """,
    # ========================================================================
    # Health Check - Orphaned Nodes (Optimized)
    # ========================================================================
    "health_check_orphaned": """
        // Find nodes with no relationships (efficiently)
        MATCH (n:Entity)
        WHERE NOT (n)--()
        RETURN count(n) AS orphaned_count
    """,
    # ========================================================================
    # Health Check - Broken References (Optimized with Index)
    # ========================================================================
    "health_check_broken_refs": """
        // Use chunk_ids index for fast lookup
        MATCH (n:Entity)
        WHERE n.chunk_ids IS NULL OR size(n.chunk_ids) = 0
        RETURN count(n) AS broken_count
    """,
    # ========================================================================
    # Entity Details with Relationships (Optimized)
    # ========================================================================
    "entity_details": """
        // Get entity properties
        MATCH (e {id: $entity_id})

        // Get outgoing relationships
        OPTIONAL MATCH (e)-[r_out]->(target)
        WITH e, labels(e) AS labels,
             collect(DISTINCT {
                 type: type(r_out),
                 direction: 'outgoing',
                 target_id: target.id,
                 target_text: coalesce(target.text, target.name)
             })[..50] AS outgoing_rels

        // Get incoming relationships
        OPTIONAL MATCH (source)-[r_in]->(e)
        WITH e, labels, outgoing_rels,
             collect(DISTINCT {
                 type: type(r_in),
                 direction: 'incoming',
                 source_id: source.id,
                 source_text: coalesce(source.text, source.name)
             })[..50] AS incoming_rels

        RETURN e, labels, outgoing_rels, incoming_rels
    """,
}

# ============================================================================
# Query Timeout Configuration
# ============================================================================

QUERY_TIMEOUTS = {
    "direct_entity_search": 5000,  # 5 seconds
    "relationship_expansion": 5000,  # 5 seconds
    "multihop_traversal": 10000,  # 10 seconds (complex query)
    "entity_search_paginated": 3000,  # 3 seconds
    "visualization_data": 8000,  # 8 seconds (depth=4 can be slow)
    "graph_statistics": 5000,  # 5 seconds
    "health_check_orphaned": 5000,  # 5 seconds
    "health_check_broken_refs": 3000,  # 3 seconds (uses index)
    "entity_details": 3000,  # 3 seconds
}

# ============================================================================
# Helper Functions
# ============================================================================


def format_multihop_query(max_depth: int) -> str:
    """
    Format multi-hop query with specified max depth.

    Args:
        max_depth: Maximum traversal depth (1-5)

    Returns:
        Formatted Cypher query string
    """
    if not 1 <= max_depth <= 5:
        raise ValueError("max_depth must be between 1 and 5")

    return NEO4J_QUERIES["multihop_traversal"].format(max_depth=max_depth)


def format_visualization_query(depth: int) -> str:
    """
    Format visualization query with specified depth.

    Args:
        depth: Traversal depth (1-4)

    Returns:
        Formatted Cypher query string
    """
    if not 1 <= depth <= 4:
        raise ValueError("depth must be between 1 and 4")

    return NEO4J_QUERIES["visualization_data"].format(depth=depth)


def get_query_timeout(query_name: str) -> int:
    """
    Get recommended timeout for query.

    Args:
        query_name: Query name from NEO4J_QUERIES

    Returns:
        Timeout in milliseconds
    """
    return QUERY_TIMEOUTS.get(query_name, 5000)  # Default 5 seconds
