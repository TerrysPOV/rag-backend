#!/bin/bash
# ============================================================================
# validate_graph_schema.sh
# ============================================================================
# Feature: NEO4J-024 - Graph Traversals Integration
# Date: 2025-11-10
# Author: Database Developer Python T2 Agent
# Purpose: Validate Neo4J and PostgreSQL schemas for graph integration
# Usage: ./validate_graph_schema.sh
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# CONFIGURATION
# ============================================================================

# Neo4J Configuration
NEO4J_CONTAINER="${NEO4J_CONTAINER:-gov-ai-neo4j}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-}"

# PostgreSQL Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gov-ai-postgres}"
POSTGRES_USER="${POSTGRES_USER:-gov_ai_user}"
POSTGRES_DB="${POSTGRES_DB:-gov_ai_db}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

validate_neo4j_connection() {
    print_header "1. VALIDATING NEO4J CONNECTION"

    if [ -z "$NEO4J_PASSWORD" ]; then
        print_error "NEO4J_PASSWORD not set. Please set the environment variable."
        echo "  export NEO4J_PASSWORD='your-password'"
        exit 1
    fi

    if docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1 AS test;" &> /dev/null; then
        print_success "Neo4J connection successful"
    else
        print_error "Failed to connect to Neo4J"
        exit 1
    fi
}

validate_neo4j_constraints() {
    print_header "2. VALIDATING NEO4J CONSTRAINTS"

    echo "Checking for entity_id_unique constraint..."
    CONSTRAINTS=$(docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "SHOW CONSTRAINTS;" 2>/dev/null | grep -i "entity_id_unique" | wc -l)

    if [ "$CONSTRAINTS" -ge 1 ]; then
        print_success "entity_id_unique constraint exists"
    else
        print_error "entity_id_unique constraint NOT FOUND"
        echo "  Run: init_neo4j_schema.cypher to create constraints"
        exit 1
    fi
}

validate_neo4j_indexes() {
    print_header "3. VALIDATING NEO4J INDEXES"

    EXPECTED_INDEXES=(
        "entity_type_index"
        "entity_chunk_id_index"
        "entity_document_id_index"
        "visa_type_text_index"
        "requirement_category_index"
        "document_type_text_index"
        "organization_text_index"
        "country_text_index"
        "entityTextIndex"
        "visaTypeIndex"
    )

    INDEXES_FOUND=0

    for INDEX_NAME in "${EXPECTED_INDEXES[@]}"; do
        COUNT=$(docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
            "SHOW INDEXES;" 2>/dev/null | grep -i "$INDEX_NAME" | wc -l)

        if [ "$COUNT" -ge 1 ]; then
            print_success "Index $INDEX_NAME exists"
            INDEXES_FOUND=$((INDEXES_FOUND + 1))
        else
            print_warning "Index $INDEX_NAME NOT FOUND"
        fi
    done

    echo ""
    echo "Indexes found: $INDEXES_FOUND / ${#EXPECTED_INDEXES[@]}"

    if [ "$INDEXES_FOUND" -lt 8 ]; then
        print_error "Missing critical indexes. Run init_neo4j_schema.cypher"
        exit 1
    fi
}

validate_neo4j_sample_data() {
    print_header "4. VALIDATING NEO4J SAMPLE DATA (Optional)"

    echo "Checking for sample entities..."
    NODE_COUNT=$(docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n) WHERE n.id CONTAINS '_sample_' RETURN count(n) AS count;" 2>/dev/null | grep -E "^[0-9]+$" | head -1)

    if [ -n "$NODE_COUNT" ] && [ "$NODE_COUNT" -gt 0 ]; then
        print_success "Found $NODE_COUNT sample entities"
    else
        print_warning "No sample data found (optional for production)"
    fi

    echo "Checking for sample relationships..."
    REL_COUNT=$(docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH ()-[r]->() RETURN count(r) AS count;" 2>/dev/null | grep -E "^[0-9]+$" | head -1)

    if [ -n "$REL_COUNT" ] && [ "$REL_COUNT" -gt 0 ]; then
        print_success "Found $REL_COUNT relationships"
    else
        print_warning "No relationships found (expected after sample data creation)"
    fi
}

validate_neo4j_graph_integrity() {
    print_header "5. VALIDATING NEO4J GRAPH INTEGRITY"

    echo "Checking for orphaned nodes..."
    ORPHANED=$(docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n:Entity) WHERE NOT (n)--() RETURN count(n) AS count;" 2>/dev/null | grep -E "^[0-9]+$" | head -1)

    if [ -n "$ORPHANED" ]; then
        if [ "$ORPHANED" -eq 0 ]; then
            print_success "No orphaned nodes found"
        else
            print_warning "Found $ORPHANED orphaned nodes (acceptable for new graph)"
        fi
    fi
}

validate_postgres_connection() {
    print_header "6. VALIDATING POSTGRESQL CONNECTION"

    if docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" &> /dev/null; then
        print_success "PostgreSQL connection successful"
    else
        print_error "Failed to connect to PostgreSQL"
        exit 1
    fi
}

validate_postgres_tables() {
    print_header "7. VALIDATING POSTGRESQL TABLES"

    EXPECTED_TABLES=(
        "graph_extraction_jobs"
        "graph_entity_mappings"
        "graph_query_audit"
        "graph_health_checks"
    )

    TABLES_FOUND=0

    for TABLE_NAME in "${EXPECTED_TABLES[@]}"; do
        EXISTS=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
            "SELECT 1 FROM information_schema.tables WHERE table_name = '$TABLE_NAME';" 2>/dev/null | grep -c "1")

        if [ "$EXISTS" -eq 1 ]; then
            print_success "Table $TABLE_NAME exists"
            TABLES_FOUND=$((TABLES_FOUND + 1))
        else
            print_error "Table $TABLE_NAME NOT FOUND"
        fi
    done

    echo ""
    echo "Tables found: $TABLES_FOUND / ${#EXPECTED_TABLES[@]}"

    if [ "$TABLES_FOUND" -ne ${#EXPECTED_TABLES[@]} ]; then
        print_error "Missing tables. Run migration 025_add_neo4j_integration_tables.sql"
        exit 1
    fi
}

validate_postgres_indexes() {
    print_header "8. VALIDATING POSTGRESQL INDEXES"

    INDEX_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM pg_indexes WHERE tablename LIKE 'graph_%';" 2>/dev/null | tr -d ' ')

    if [ -n "$INDEX_COUNT" ] && [ "$INDEX_COUNT" -ge 15 ]; then
        print_success "Found $INDEX_COUNT indexes (expected ~18)"
    else
        print_warning "Found only $INDEX_COUNT indexes (expected ~18)"
    fi
}

validate_postgres_rls() {
    print_header "9. VALIDATING POSTGRESQL ROW-LEVEL SECURITY"

    RLS_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM pg_policies WHERE tablename LIKE 'graph_%';" 2>/dev/null | tr -d ' ')

    if [ -n "$RLS_COUNT" ] && [ "$RLS_COUNT" -ge 4 ]; then
        print_success "Found $RLS_COUNT RLS policies (expected 4)"
    else
        print_warning "Found only $RLS_COUNT RLS policies (expected 4)"
    fi
}

validate_postgres_sample_data() {
    print_header "10. VALIDATING POSTGRESQL SAMPLE DATA (Optional)"

    JOB_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM graph_extraction_jobs;" 2>/dev/null | tr -d ' ')

    if [ -n "$JOB_COUNT" ] && [ "$JOB_COUNT" -gt 0 ]; then
        print_success "Found $JOB_COUNT extraction job(s)"
    else
        print_warning "No extraction jobs found (expected after sample data)"
    fi

    ENTITY_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT COUNT(*) FROM graph_entity_mappings;" 2>/dev/null | tr -d ' ')

    if [ -n "$ENTITY_COUNT" ] && [ "$ENTITY_COUNT" -gt 0 ]; then
        print_success "Found $ENTITY_COUNT entity mapping(s)"
    else
        print_warning "No entity mappings found (expected after sample data)"
    fi
}

generate_health_check_report() {
    print_header "11. GENERATING HEALTH CHECK REPORT"

    # Neo4J Statistics
    echo "Neo4J Graph Statistics:"
    docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n) RETURN labels(n) AS label, count(n) AS count ORDER BY count DESC;" 2>/dev/null | head -20

    echo ""
    echo "Neo4J Relationship Statistics:"
    docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC;" 2>/dev/null | head -20

    echo ""
    echo "PostgreSQL Table Row Counts:"
    docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "SELECT 'graph_extraction_jobs' AS table_name, COUNT(*) AS row_count FROM graph_extraction_jobs
         UNION ALL
         SELECT 'graph_entity_mappings', COUNT(*) FROM graph_entity_mappings
         UNION ALL
         SELECT 'graph_query_audit', COUNT(*) FROM graph_query_audit
         UNION ALL
         SELECT 'graph_health_checks', COUNT(*) FROM graph_health_checks;" 2>/dev/null
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Neo4J Graph Schema Validation - UK Immigration RAG System            ║${NC}"
    echo -e "${BLUE}║  Database Developer Python T2 Agent                                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"

    # Neo4J Validation
    validate_neo4j_connection
    validate_neo4j_constraints
    validate_neo4j_indexes
    validate_neo4j_sample_data
    validate_neo4j_graph_integrity

    # PostgreSQL Validation
    validate_postgres_connection
    validate_postgres_tables
    validate_postgres_indexes
    validate_postgres_rls
    validate_postgres_sample_data

    # Health Check Report
    generate_health_check_report

    print_header "VALIDATION COMPLETE"
    print_success "All critical schema components validated successfully"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "  1. Remove sample data: docker exec $NEO4J_CONTAINER cypher-shell -u $NEO4J_USER -p \$NEO4J_PASSWORD \"MATCH (n) WHERE n.id CONTAINS '_sample_' DETACH DELETE n;\""
    echo "  2. Trigger initial extraction: curl -X POST https://vectorgov.poview.ai/api/rag/graph/extract"
    echo "  3. Monitor progress: curl https://vectorgov.poview.ai/api/rag/graph/stats"
    echo ""
}

# Run main function
main

# Exit successfully
exit 0
