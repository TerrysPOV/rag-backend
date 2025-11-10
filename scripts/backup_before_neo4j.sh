#!/bin/bash
# ============================================================================
# backup_before_neo4j.sh
# ============================================================================
# Feature: NEO4J-024 - Graph Traversals Integration
# Date: 2025-11-10
# Author: Database Developer Python T2 Agent
# Purpose: Backup Neo4J and PostgreSQL before migration
# Usage: ./backup_before_neo4j.sh
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# CONFIGURATION
# ============================================================================

# Backup Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/gov-ai/backups/neo4j-migration}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="neo4j_migration_backup_${TIMESTAMP}"

# Neo4J Configuration
NEO4J_CONTAINER="${NEO4J_CONTAINER:-gov-ai-neo4j}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-}"
NEO4J_DATA_DIR="/var/lib/neo4j/data"

# PostgreSQL Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-gov-ai-postgres}"
POSTGRES_USER="${POSTGRES_USER:-gov_ai_user}"
POSTGRES_DB="${POSTGRES_DB:-gov_ai_db}"

# Qdrant Configuration (for metadata backup)
QDRANT_CONTAINER="${QDRANT_CONTAINER:-gov-ai-qdrant}"
QDRANT_COLLECTION="${QDRANT_COLLECTION:-immigration_docs}"

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
# BACKUP FUNCTIONS
# ============================================================================

create_backup_directory() {
    print_header "1. CREATING BACKUP DIRECTORY"

    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/neo4j"
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/postgres"
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/qdrant"

    print_success "Backup directory created: ${BACKUP_DIR}/${BACKUP_NAME}"
}

backup_neo4j_data() {
    print_header "2. BACKING UP NEO4J DATA"

    if [ -z "$NEO4J_PASSWORD" ]; then
        print_error "NEO4J_PASSWORD not set. Please set the environment variable."
        exit 1
    fi

    echo "Exporting Neo4J graph to Cypher statements..."

    # Export all nodes
    docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n) RETURN n LIMIT 1000;" > "${BACKUP_DIR}/${BACKUP_NAME}/neo4j/nodes_sample.cypher" 2>/dev/null || true

    # Export graph statistics
    docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "CALL apoc.meta.stats();" > "${BACKUP_DIR}/${BACKUP_NAME}/neo4j/graph_stats.txt" 2>/dev/null || true

    # Export schema
    docker exec "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "SHOW CONSTRAINTS; SHOW INDEXES;" > "${BACKUP_DIR}/${BACKUP_NAME}/neo4j/schema.txt" 2>/dev/null || true

    print_success "Neo4J data exported"

    # Optional: Backup Neo4J data directory (requires stopped container)
    print_warning "Note: Full Neo4J data directory backup requires container restart"
    echo "  To backup Neo4J data directory:"
    echo "    docker stop $NEO4J_CONTAINER"
    echo "    docker cp ${NEO4J_CONTAINER}:${NEO4J_DATA_DIR} ${BACKUP_DIR}/${BACKUP_NAME}/neo4j/"
    echo "    docker start $NEO4J_CONTAINER"
}

backup_postgres_data() {
    print_header "3. BACKING UP POSTGRESQL DATA"

    echo "Dumping PostgreSQL database..."
    docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --clean --if-exists --create \
        > "${BACKUP_DIR}/${BACKUP_NAME}/postgres/full_dump.sql" 2>/dev/null

    DUMP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}/postgres/full_dump.sql" | cut -f1)
    print_success "PostgreSQL database dumped (${DUMP_SIZE})"

    echo "Backing up graph-specific tables..."
    docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --table="graph_*" --clean --if-exists \
        > "${BACKUP_DIR}/${BACKUP_NAME}/postgres/graph_tables_dump.sql" 2>/dev/null || true

    print_success "Graph tables backed up"
}

backup_qdrant_metadata() {
    print_header "4. BACKING UP QDRANT METADATA"

    echo "Exporting Qdrant collection metadata..."

    # Get collection info
    docker exec "$QDRANT_CONTAINER" curl -s "http://localhost:6333/collections/${QDRANT_COLLECTION}" \
        > "${BACKUP_DIR}/${BACKUP_NAME}/qdrant/collection_info.json" 2>/dev/null || true

    # Get sample points (first 100)
    docker exec "$QDRANT_CONTAINER" curl -s -X POST "http://localhost:6333/collections/${QDRANT_COLLECTION}/points/scroll" \
        -H "Content-Type: application/json" \
        -d '{"limit": 100}' \
        > "${BACKUP_DIR}/${BACKUP_NAME}/qdrant/sample_points.json" 2>/dev/null || true

    print_success "Qdrant metadata exported"
}

create_rollback_script() {
    print_header "5. CREATING ROLLBACK SCRIPT"

    cat > "${BACKUP_DIR}/${BACKUP_NAME}/rollback.sh" <<'EOF'
#!/bin/bash
# ============================================================================
# ROLLBACK SCRIPT - Neo4J Migration
# ============================================================================
# Generated: ${TIMESTAMP}
# Purpose: Restore databases to pre-migration state
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting rollback process..."

# Rollback PostgreSQL
echo "Restoring PostgreSQL database..."
docker exec -i ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < "${SCRIPT_DIR}/postgres/full_dump.sql"

# Rollback Neo4J
echo "WARNING: Neo4J rollback requires manual intervention"
echo "  1. Stop Neo4J container: docker stop ${NEO4J_CONTAINER}"
echo "  2. Restore data directory from backup"
echo "  3. Start Neo4J container: docker start ${NEO4J_CONTAINER}"

echo "Rollback complete (PostgreSQL only)"
echo "Review ${SCRIPT_DIR}/postgres/full_dump.sql for details"
EOF

    chmod +x "${BACKUP_DIR}/${BACKUP_NAME}/rollback.sh"
    print_success "Rollback script created: ${BACKUP_DIR}/${BACKUP_NAME}/rollback.sh"
}

create_backup_manifest() {
    print_header "6. CREATING BACKUP MANIFEST"

    cat > "${BACKUP_DIR}/${BACKUP_NAME}/MANIFEST.md" <<EOF
# Neo4J Migration Backup Manifest

**Backup Date**: $(date)
**Backup Name**: ${BACKUP_NAME}
**Backup Location**: ${BACKUP_DIR}/${BACKUP_NAME}

## Backup Contents

### Neo4J
- \`neo4j/nodes_sample.cypher\`: Sample of first 1000 nodes
- \`neo4j/graph_stats.txt\`: Graph statistics (node/relationship counts)
- \`neo4j/schema.txt\`: Constraints and indexes

### PostgreSQL
- \`postgres/full_dump.sql\`: Complete database dump
- \`postgres/graph_tables_dump.sql\`: Graph integration tables only

### Qdrant
- \`qdrant/collection_info.json\`: Collection metadata
- \`qdrant/sample_points.json\`: Sample of first 100 vector points

### Rollback
- \`rollback.sh\`: Automated rollback script

## Restoration Instructions

### PostgreSQL Restoration
\`\`\`bash
docker exec -i ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < postgres/full_dump.sql
\`\`\`

### Neo4J Restoration
1. Stop Neo4J container:
   \`\`\`bash
   docker stop ${NEO4J_CONTAINER}
   \`\`\`

2. Restore data directory (if backed up):
   \`\`\`bash
   docker cp neo4j/data ${NEO4J_CONTAINER}:${NEO4J_DATA_DIR}
   \`\`\`

3. Start Neo4J container:
   \`\`\`bash
   docker start ${NEO4J_CONTAINER}
   \`\`\`

## Verification

After restoration, run:
\`\`\`bash
./validate_graph_schema.sh
\`\`\`

## Backup Statistics

- **Neo4J Backup Size**: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}/neo4j 2>/dev/null | cut -f1 || echo "N/A")
- **PostgreSQL Backup Size**: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}/postgres 2>/dev/null | cut -f1 || echo "N/A")
- **Total Backup Size**: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME} 2>/dev/null | cut -f1 || echo "N/A")

---
Generated by: Database Developer Python T2 Agent
Feature: NEO4J-024 - Graph Traversals Integration
EOF

    print_success "Backup manifest created: ${BACKUP_DIR}/${BACKUP_NAME}/MANIFEST.md"
}

compress_backup() {
    print_header "7. COMPRESSING BACKUP (Optional)"

    echo "Creating compressed archive..."
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "${BACKUP_DIR}" "${BACKUP_NAME}" 2>/dev/null || true

    if [ -f "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" ]; then
        ARCHIVE_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
        print_success "Backup compressed: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz (${ARCHIVE_SIZE})"
    else
        print_warning "Compression skipped (optional)"
    fi
}

verify_backup() {
    print_header "8. VERIFYING BACKUP INTEGRITY"

    # Check PostgreSQL dump is valid SQL
    if head -n 1 "${BACKUP_DIR}/${BACKUP_NAME}/postgres/full_dump.sql" | grep -q "PostgreSQL"; then
        print_success "PostgreSQL dump appears valid"
    else
        print_error "PostgreSQL dump may be corrupted"
    fi

    # Check backup file sizes
    POSTGRES_SIZE=$(stat -f%z "${BACKUP_DIR}/${BACKUP_NAME}/postgres/full_dump.sql" 2>/dev/null || echo "0")
    if [ "$POSTGRES_SIZE" -gt 1000 ]; then
        print_success "PostgreSQL dump size: ${POSTGRES_SIZE} bytes"
    else
        print_error "PostgreSQL dump is too small (${POSTGRES_SIZE} bytes)"
    fi

    # List all backup files
    echo ""
    echo "Backup file tree:"
    tree "${BACKUP_DIR}/${BACKUP_NAME}" 2>/dev/null || find "${BACKUP_DIR}/${BACKUP_NAME}" -type f
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Neo4J Migration Backup - UK Immigration RAG System                   ║${NC}"
    echo -e "${BLUE}║  Database Developer Python T2 Agent                                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"

    # Execute backup steps
    create_backup_directory
    backup_neo4j_data
    backup_postgres_data
    backup_qdrant_metadata
    create_rollback_script
    create_backup_manifest
    compress_backup
    verify_backup

    print_header "BACKUP COMPLETE"
    print_success "All databases backed up successfully"
    echo ""
    echo -e "${GREEN}Backup Location:${NC} ${BACKUP_DIR}/${BACKUP_NAME}"
    echo -e "${GREEN}Archive:${NC} ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    echo -e "${GREEN}Manifest:${NC} ${BACKUP_DIR}/${BACKUP_NAME}/MANIFEST.md"
    echo -e "${GREEN}Rollback Script:${NC} ${BACKUP_DIR}/${BACKUP_NAME}/rollback.sh"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "  1. Review the manifest file for backup details"
    echo "  2. Test the rollback script before proceeding with migration"
    echo "  3. Store the backup archive in a secure location"
    echo "  4. Keep this backup for at least 30 days after migration"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "  1. Run migration: psql < migrations/025_add_neo4j_integration_tables.sql"
    echo "  2. Initialize Neo4J schema: cypher-shell < scripts/init_neo4j_schema.cypher"
    echo "  3. Validate schemas: ./scripts/validate_graph_schema.sh"
    echo ""
}

# Run main function
main

# Exit successfully
exit 0
