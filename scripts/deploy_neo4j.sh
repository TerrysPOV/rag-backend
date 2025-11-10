#!/bin/bash
# ============================================================================
# Neo4J Graph Traversals Deployment Script
# Feature: NEO4J-001 - Graph Traversals Integration
# Target: DigitalOcean Droplet (161.35.44.166)
# Date: 2025-11-10
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
DROPLET_IP="161.35.44.166"
DROPLET_USER="root"
REMOTE_DIR="/opt/gov-ai/backend"
NEO4J_VERSION="5.14.0"
NEO4J_PORT="7687"
NEO4J_HTTP_PORT="7474"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check SSH connection
    if ! ssh -q -o ConnectTimeout=5 ${DROPLET_USER}@${DROPLET_IP} exit; then
        log_error "Cannot connect to droplet ${DROPLET_IP}"
        exit 1
    fi
    log_success "SSH connection verified"

    # Check required files exist
    local required_files=(
        "neo4j_schema.cypher"
        "migrations/025_add_neo4j_integration_tables.sql"
        "src/services/neo4j_graph_extractor.py"
        "src/services/neo4j_graph_retriever.py"
        "src/services/neo4j_graph_service.py"
        "src/api/routes/graph.py"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    log_success "All required files present"
}

# Step 1: Deploy Neo4J container
deploy_neo4j_container() {
    log_info "Step 1: Deploying Neo4J container..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        # Check if Neo4J is already running
        if docker ps | grep -q gov-ai-neo4j; then
            echo "Neo4J container already running"
        else
            # Create Neo4J data directory
            mkdir -p /opt/gov-ai/neo4j/data
            mkdir -p /opt/gov-ai/neo4j/logs
            mkdir -p /opt/gov-ai/neo4j/conf

            # Generate strong password if not already set
            if [ -z "${NEO4J_PASSWORD:-}" ]; then
                export NEO4J_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
                echo "Generated Neo4J password: ${NEO4J_PASSWORD}" > /opt/gov-ai/neo4j/.password
                chmod 600 /opt/gov-ai/neo4j/.password
            fi

            # Start Neo4J container
            docker run -d \
                --name gov-ai-neo4j \
                --restart unless-stopped \
                -p 7687:7687 \
                -p 7474:7474 \
                -v /opt/gov-ai/neo4j/data:/data \
                -v /opt/gov-ai/neo4j/logs:/logs \
                -v /opt/gov-ai/neo4j/conf:/conf \
                -e NEO4J_AUTH=neo4j/${NEO4J_PASSWORD} \
                -e NEO4J_dbms_security_auth__minimum__password__length=16 \
                -e NEO4J_dbms_memory_heap_initial__size=512m \
                -e NEO4J_dbms_memory_heap_max__size=2g \
                -e NEO4J_apoc_export_file_enabled=true \
                -e NEO4J_apoc_import_file_enabled=true \
                -e NEO4J_apoc_import_file_use__neo4j__config=true \
                -e NEO4J_PLUGINS='["apoc"]' \
                neo4j:5.14.0

            echo "Waiting for Neo4J to start (60 seconds)..."
            sleep 60
        fi
ENDSSH

    log_success "Neo4J container deployed"
}

# Step 2: Copy files to droplet
copy_files_to_droplet() {
    log_info "Step 2: Copying files to droplet..."

    # Create remote directories
    ssh ${DROPLET_USER}@${DROPLET_IP} "mkdir -p ${REMOTE_DIR}/src/services ${REMOTE_DIR}/src/api/routes ${REMOTE_DIR}/migrations ${REMOTE_DIR}/schemas"

    # Copy schema file
    scp neo4j_schema.cypher ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/schemas/
    log_success "Copied neo4j_schema.cypher"

    # Copy PostgreSQL migration
    scp migrations/025_add_neo4j_integration_tables.sql ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/migrations/
    log_success "Copied PostgreSQL migration"

    # Copy service files
    scp src/services/neo4j_graph_extractor.py ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/src/services/
    scp src/services/neo4j_graph_retriever.py ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/src/services/
    scp src/services/neo4j_graph_service.py ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/src/services/
    log_success "Copied service files"

    # Copy API routes
    scp src/api/routes/graph.py ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/src/api/routes/
    log_success "Copied API routes"
}

# Step 3: Initialize Neo4J schema
initialize_neo4j_schema() {
    log_info "Step 3: Initializing Neo4J schema..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        # Get Neo4J password
        NEO4J_PASSWORD=$(cat /opt/gov-ai/neo4j/.password 2>/dev/null || echo "")

        if [ -z "${NEO4J_PASSWORD}" ]; then
            echo "ERROR: Neo4J password not found"
            exit 1
        fi

        # Initialize schema
        cat /opt/gov-ai/backend/schemas/neo4j_schema.cypher | \
            docker exec -i gov-ai-neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" --format plain

        if [ $? -eq 0 ]; then
            echo "Neo4J schema initialized successfully"
        else
            echo "ERROR: Failed to initialize Neo4J schema"
            exit 1
        fi
ENDSSH

    log_success "Neo4J schema initialized"
}

# Step 4: Run PostgreSQL migration
run_postgresql_migration() {
    log_info "Step 4: Running PostgreSQL migration..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        # Run migration
        docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -f /opt/gov-ai/backend/migrations/025_add_neo4j_integration_tables.sql

        if [ $? -eq 0 ]; then
            echo "PostgreSQL migration completed successfully"
        else
            echo "ERROR: PostgreSQL migration failed"
            exit 1
        fi
ENDSSH

    log_success "PostgreSQL migration completed"
}

# Step 5: Configure environment variables
configure_environment() {
    log_info "Step 5: Configuring environment variables..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        # Get Neo4J password
        NEO4J_PASSWORD=$(cat /opt/gov-ai/neo4j/.password 2>/dev/null || echo "")

        # Update .env file
        if [ ! -f /opt/gov-ai/backend/.env ]; then
            echo "ERROR: .env file not found"
            exit 1
        fi

        # Add Neo4J configuration
        if ! grep -q "NEO4J_URI" /opt/gov-ai/backend/.env; then
            cat >> /opt/gov-ai/backend/.env << EOF

# Neo4J Graph Database Configuration (Feature NEO4J-001)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=${NEO4J_PASSWORD}
NEO4J_DATABASE=neo4j
GRAPH_RETRIEVAL_ENABLED=true
GRAPH_MAX_DEPTH=3
GRAPH_TOP_K=10
EOF
            echo "Neo4J environment variables added to .env"
        else
            echo "Neo4J configuration already exists in .env"
        fi
ENDSSH

    log_success "Environment variables configured"
}

# Step 6: Install Python dependencies
install_dependencies() {
    log_info "Step 6: Installing Python dependencies..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        cd /opt/gov-ai/backend

        # Activate virtual environment
        source venv/bin/activate

        # Install Neo4J driver and SpaCy
        pip install neo4j>=5.14.0 spacy>=3.7.0

        # Download SpaCy large English model
        python -m spacy download en_core_web_lg

        echo "Python dependencies installed"
ENDSSH

    log_success "Python dependencies installed"
}

# Step 7: Restart backend service
restart_backend() {
    log_info "Step 7: Restarting backend service..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        # Restart FastAPI backend
        systemctl restart gov-ai-backend || docker-compose -f /opt/gov-ai/docker-compose.yml restart backend

        echo "Backend service restarted"
ENDSSH

    log_success "Backend service restarted"
}

# Step 8: Verify deployment
verify_deployment() {
    log_info "Step 8: Verifying deployment..."

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        # Check Neo4J container status
        if ! docker ps | grep -q gov-ai-neo4j; then
            echo "ERROR: Neo4J container not running"
            exit 1
        fi
        echo "✓ Neo4J container running"

        # Check Neo4J connectivity
        NEO4J_PASSWORD=$(cat /opt/gov-ai/neo4j/.password 2>/dev/null || echo "")
        docker exec gov-ai-neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "MATCH (n) RETURN count(n) AS node_count;" --format plain > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✓ Neo4J database accessible"
        else
            echo "ERROR: Cannot connect to Neo4J database"
            exit 1
        fi

        # Check PostgreSQL tables
        TABLE_COUNT=$(docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'graph_%';")
        if [ "${TABLE_COUNT}" -ge 5 ]; then
            echo "✓ PostgreSQL graph tables created (${TABLE_COUNT} tables)"
        else
            echo "ERROR: PostgreSQL graph tables not found"
            exit 1
        fi

        # Check backend service
        sleep 5  # Give backend time to restart
        if curl -s http://localhost:8000/health | grep -q "healthy"; then
            echo "✓ Backend service healthy"
        else
            echo "WARNING: Backend health check failed"
        fi
ENDSSH

    log_success "Deployment verification complete"
}

# Step 9: Display deployment summary
display_summary() {
    log_info "=========================================="
    log_info "Neo4J Graph Traversals Deployment Summary"
    log_info "=========================================="

    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        NEO4J_PASSWORD=$(cat /opt/gov-ai/neo4j/.password 2>/dev/null || echo "NOT_SET")

        echo ""
        echo "Neo4J Configuration:"
        echo "  - URI: bolt://localhost:7687"
        echo "  - HTTP UI: http://161.35.44.166:7474"
        echo "  - User: neo4j"
        echo "  - Password: ${NEO4J_PASSWORD}"
        echo ""
        echo "API Endpoints:"
        echo "  - GET  /api/rag/graph/stats       - Graph statistics"
        echo "  - GET  /api/rag/graph/health      - Health check"
        echo "  - POST /api/rag/graph/extract     - Trigger extraction"
        echo "  - POST /api/rag/graph/query       - Graph-augmented query"
        echo "  - GET  /api/rag/graph/entity/{id} - Entity details"
        echo ""
        echo "PostgreSQL Tables:"
        docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'graph_%' ORDER BY table_name;"
        echo ""
        echo "Next Steps:"
        echo "  1. Access Neo4J Browser: http://161.35.44.166:7474"
        echo "  2. Test API health: curl http://161.35.44.166:8000/api/rag/graph/health"
        echo "  3. Trigger extraction: curl -X POST http://161.35.44.166:8000/api/rag/graph/extract"
        echo ""
ENDSSH
}

# Main deployment flow
main() {
    log_info "Starting Neo4J Graph Traversals deployment..."
    echo ""

    check_prerequisites
    deploy_neo4j_container
    copy_files_to_droplet
    initialize_neo4j_schema
    run_postgresql_migration
    configure_environment
    install_dependencies
    restart_backend
    verify_deployment
    display_summary

    echo ""
    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"
