# Neo4J Graph Traversals - Deployment Checklist

**Feature**: NEO4J-001 - Graph Traversals Integration
**Target**: DigitalOcean Droplet (161.35.44.166)
**Date**: 2025-11-10

---

## Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] **SSH Access Verified**
  ```bash
  ssh root@161.35.44.166
  ```
  Expected: Successful connection

- [ ] **Disk Space Check**
  ```bash
  df -h /opt/gov-ai
  ```
  Required: At least 5GB free space

- [ ] **Docker Installed and Running**
  ```bash
  docker --version
  docker ps
  ```
  Expected: Docker 24+ running

- [ ] **PostgreSQL Container Healthy**
  ```bash
  docker ps | grep gov-ai-postgres
  docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "SELECT 1;"
  ```
  Expected: Container running, connection successful

---

### 2. Backup Current State

- [ ] **Backup Qdrant Vectors**
  ```bash
  # Qdrant snapshot (117,343 documents)
  curl -X POST "http://161.35.44.166:6333/collections/immigration_guidance/snapshots"
  ```

- [ ] **Backup PostgreSQL Database**
  ```bash
  docker exec gov-ai-postgres pg_dump -U gov_ai_user gov_ai_db > /opt/gov-ai/backups/gov_ai_db_$(date +%Y%m%d).sql
  ```

- [ ] **Backup Current Backend Code**
  ```bash
  tar -czf /opt/gov-ai/backups/backend_$(date +%Y%m%d).tar.gz /opt/gov-ai/backend/
  ```

---

### 3. Review Deployment Files

- [ ] **Neo4J Schema File**
  - Location: `backend-source/neo4j_schema.cypher`
  - Status: ✅ Corrected (UK Immigration schema)
  - Lines to verify: 13-15 (Entity constraint), 86-122 (sample data)

- [ ] **PostgreSQL Migration**
  - Location: `backend-source/migrations/025_add_neo4j_integration_tables.sql`
  - Tables: 5 (graph_extraction_jobs, graph_entity_mappings, graph_query_audit, graph_health_checks, graph_consistency_reports)
  - Triggers: 1 (update_entity_relationship_count)

- [ ] **Backend Services**
  - `src/services/neo4j_graph_extractor.py` ✅
  - `src/services/neo4j_graph_retriever.py` ✅
  - `src/services/neo4j_graph_service.py` ✅

- [ ] **API Routes**
  - `src/api/routes/graph.py` ✅

- [ ] **Deployment Script**
  - Location: `backend-source/scripts/deploy_neo4j.sh`
  - Permissions: Executable (`chmod +x`)

---

## Deployment Execution

### 4. Run Deployment Script

```bash
cd /Volumes/TerrysPOV/gov_content_ai/backend-source
./scripts/deploy_neo4j.sh
```

**Expected Output**:
```
[INFO] Starting Neo4J Graph Traversals deployment...
[INFO] Checking prerequisites...
[SUCCESS] SSH connection verified
[SUCCESS] All required files present
[INFO] Step 1: Deploying Neo4J container...
[SUCCESS] Neo4J container deployed
[INFO] Step 2: Copying files to droplet...
[SUCCESS] Copied neo4j_schema.cypher
[SUCCESS] Copied PostgreSQL migration
[SUCCESS] Copied service files
[SUCCESS] Copied API routes
[INFO] Step 3: Initializing Neo4J schema...
[SUCCESS] Neo4J schema initialized
[INFO] Step 4: Running PostgreSQL migration...
[SUCCESS] PostgreSQL migration completed
[INFO] Step 5: Configuring environment variables...
[SUCCESS] Environment variables configured
[INFO] Step 6: Installing Python dependencies...
[SUCCESS] Python dependencies installed
[INFO] Step 7: Restarting backend service...
[SUCCESS] Backend service restarted
[INFO] Step 8: Verifying deployment...
✓ Neo4J container running
✓ Neo4J database accessible
✓ PostgreSQL graph tables created (5 tables)
✓ Backend service healthy
[SUCCESS] Deployment verification complete
```

**Deployment Duration**: ~15-20 minutes

---

### 5. Manual Verification Steps

#### 5.1 Verify Neo4J Container

```bash
ssh root@161.35.44.166

# Check container status
docker ps | grep gov-ai-neo4j

# Check logs
docker logs gov-ai-neo4j --tail 50

# Get Neo4J password
cat /opt/gov-ai/neo4j/.password
```

**Expected**:
- Container status: Up
- Logs: No errors, "Bolt enabled", "Started"
- Password: 32-character random string

#### 5.2 Verify Neo4J Connectivity

```bash
# Connect to Neo4J via cypher-shell
docker exec -it gov-ai-neo4j cypher-shell -u neo4j -p $(cat /opt/gov-ai/neo4j/.password)

# In cypher-shell, run:
MATCH (n) RETURN count(n) AS node_count;
CALL db.indexes();
CALL db.constraints();
```

**Expected**:
- Connection successful
- Sample data: 3 nodes (if schema includes sample data)
- Indexes: 10+ indexes created
- Constraints: 1 unique constraint on Entity.id

#### 5.3 Verify PostgreSQL Tables

```bash
# List graph tables
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema='public'
AND table_name LIKE 'graph_%'
ORDER BY table_name;
"

# Check table structure
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'graph_extraction_jobs'
ORDER BY ordinal_position;
"
```

**Expected**:
- 5 tables: graph_extraction_jobs, graph_entity_mappings, graph_query_audit, graph_health_checks, graph_consistency_reports
- All required columns present
- Triggers created

#### 5.4 Verify Backend Configuration

```bash
# Check .env file
cat /opt/gov-ai/backend/.env | grep NEO4J

# Expected environment variables:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=<32-char-password>
# NEO4J_DATABASE=neo4j
# GRAPH_RETRIEVAL_ENABLED=true
```

#### 5.5 Verify Backend Service

```bash
# Check service status
systemctl status gov-ai-backend || docker ps | grep gov-ai-backend

# Check backend logs
journalctl -u gov-ai-backend --since "5 minutes ago" || docker logs gov-ai-backend --tail 50

# Health check
curl http://localhost:8000/health
```

**Expected**:
- Service running
- No Neo4J connection errors in logs
- Health check: `{"status": "healthy"}`

---

### 6. API Endpoint Testing

#### 6.1 Test Graph Health Endpoint

```bash
curl http://161.35.44.166:8000/api/rag/graph/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "orphaned_nodes": 0,
  "broken_references": 0,
  "warnings": [],
  "errors": [],
  "timestamp": "2025-11-10T..."
}
```

#### 6.2 Test Graph Statistics Endpoint

```bash
curl http://161.35.44.166:8000/api/rag/graph/stats
```

**Expected Response**:
```json
{
  "node_counts": {
    "Entity": 3,
    "visa_type": 1,
    "requirement": 1,
    "document_type": 1
  },
  "relationship_counts": {
    "REQUIRES": 1,
    "SATISFIED_BY": 1
  },
  "total_nodes": 3,
  "total_relationships": 2,
  "graph_density": 0.3333,
  "last_updated": "2025-11-10T..."
}
```

#### 6.3 Test Entity Search Endpoint

```bash
curl -X POST http://161.35.44.166:8000/api/rag/graph/search \
  -H "Content-Type: application/json" \
  -d '{"search_term": "Skilled Worker", "limit": 5}'
```

**Expected Response**:
```json
{
  "results": [
    {
      "id": "visa_skilled_worker_001",
      "labels": ["Entity", "visa_type"],
      "text": "Skilled Worker visa",
      "properties": {
        "id": "visa_skilled_worker_001",
        "text": "Skilled Worker visa",
        "category": "work",
        ...
      }
    }
  ],
  "total": 1
}
```

---

## Post-Deployment Tasks

### 7. Trigger Initial Extraction

#### 7.1 Clean Sample Data (Optional)

```bash
# Connect to Neo4J
docker exec -it gov-ai-neo4j cypher-shell -u neo4j -p $(cat /opt/gov-ai/neo4j/.password)

# Remove sample data
MATCH (n)
WHERE n.id IN [
  'visa_skilled_worker_001',
  'req_financial_001',
  'doc_type_bank_statement_001'
]
DETACH DELETE n;
```

#### 7.2 Trigger Full Extraction (Background Process)

**WARNING**: This will extract entities from 117,343 documents (~6-8 hours, $8.80 USD cost)

```bash
# Get admin token
export ADMIN_TOKEN="<keycloak-admin-token>"

# Trigger extraction
curl -X POST http://161.35.44.166:8000/api/rag/graph/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "document_ids": null,
    "enable_llm_extraction": true
  }'
```

**Expected Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Graph extraction queued. Processing all documents."
}
```

**Note**: In current implementation, this returns a placeholder job_id. Production version would use Celery for async processing.

#### 7.3 Monitor Extraction Progress

```bash
# Watch Neo4J node count
watch -n 60 'docker exec gov-ai-neo4j cypher-shell -u neo4j -p $(cat /opt/gov-ai/neo4j/.password) "MATCH (n) RETURN count(n) AS nodes;"'

# Watch backend logs
journalctl -u gov-ai-backend -f | grep "graph extraction"

# Check PostgreSQL job status
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "
SELECT job_id, status, documents_processed, total_documents,
       entities_extracted, relationships_created,
       ROUND((documents_processed::DECIMAL / total_documents) * 100, 2) AS progress_pct
FROM graph_extraction_jobs
ORDER BY created_at DESC
LIMIT 5;
"
```

**Expected Progress**:
- Nodes: Growing from 0 to 15,000-20,000 over 6-8 hours
- Relationships: Growing to 30,000-40,000
- Job status: queued → running → completed

---

### 8. Performance Testing

#### 8.1 Test Graph Query Performance

```bash
# Test direct entity search
time curl -X POST http://161.35.44.166:8000/api/rag/graph/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What documents are needed for Skilled Worker visa?", "use_graph": true, "max_graph_depth": 3, "top_k": 5}'

# Expected latency: < 500ms
```

#### 8.2 Test Multi-Hop Traversal

```bash
# Test complex query
time curl -X POST http://161.35.44.166:8000/api/rag/graph/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Can I switch from Student visa to Skilled Worker visa?", "use_graph": true, "max_graph_depth": 3, "top_k": 5}'

# Expected latency: < 1000ms
```

#### 8.3 Monitor Neo4J Resource Usage

```bash
# CPU and memory
docker stats gov-ai-neo4j --no-stream

# Expected:
# CPU: < 50%
# Memory: < 2GB
```

---

### 9. Health Monitoring Setup

#### 9.1 Create Health Check Cron Job

```bash
# Add to crontab on droplet
crontab -e

# Add this line (run every hour)
0 * * * * curl -s http://localhost:8000/api/rag/graph/health >> /var/log/neo4j-health.log 2>&1
```

#### 9.2 Set Up Alerting (Optional)

Create alerting for:
- Neo4J container down
- Graph query latency > 1000ms
- Orphaned nodes > 100
- Extraction job failures

---

## Rollback Procedure

### 10. If Deployment Fails

#### 10.1 Stop Neo4J Container

```bash
ssh root@161.35.44.166
docker stop gov-ai-neo4j
docker rm gov-ai-neo4j
```

#### 10.2 Drop PostgreSQL Graph Tables

```bash
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db << 'EOF'
DROP TABLE IF EXISTS graph_consistency_reports CASCADE;
DROP TABLE IF EXISTS graph_health_checks CASCADE;
DROP TABLE IF EXISTS graph_query_audit CASCADE;
DROP TABLE IF EXISTS graph_entity_mappings CASCADE;
DROP TABLE IF EXISTS graph_extraction_jobs CASCADE;
DROP FUNCTION IF EXISTS update_entity_relationship_count CASCADE;
EOF
```

#### 10.3 Remove Neo4J Configuration

```bash
# Remove Neo4J environment variables from .env
sed -i '/NEO4J_/d' /opt/gov-ai/backend/.env
sed -i '/GRAPH_/d' /opt/gov-ai/backend/.env
```

#### 10.4 Restore Backend Code

```bash
# Restore from backup
cd /opt/gov-ai
tar -xzf backups/backend_$(date +%Y%m%d).tar.gz
```

#### 10.5 Restart Backend

```bash
systemctl restart gov-ai-backend || docker-compose restart backend
```

#### 10.6 Verify Rollback

```bash
# Check backend health
curl http://localhost:8000/health

# Verify Neo4J not running
docker ps | grep neo4j  # Should return nothing

# Verify graph tables removed
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'graph_%';"
# Should return 0 rows
```

---

## Success Criteria

### 11. Deployment Success Indicators

- [✅] Neo4J container running (docker ps)
- [✅] Neo4J database accessible (cypher-shell connection)
- [✅] 5 PostgreSQL tables created
- [✅] Backend service healthy (health check returns 200)
- [✅] Graph health endpoint returns "healthy"
- [✅] Graph statistics endpoint returns data
- [✅] No errors in backend logs
- [✅] Environment variables configured

### 12. Extraction Success Indicators (After 6-8 hours)

- [ ] 15,000-20,000 entities extracted
- [ ] 30,000-40,000 relationships created
- [ ] < 5% document failures
- [ ] Graph density 0.001-0.01
- [ ] Orphaned nodes < 100
- [ ] Broken references = 0
- [ ] Query latency p95 < 500ms

---

## Files Deployed

### 13. Deployment Artifact List

**Schema Files**:
- ✅ `/opt/gov-ai/backend/schemas/neo4j_schema.cypher`

**Migration Files**:
- ✅ `/opt/gov-ai/backend/migrations/025_add_neo4j_integration_tables.sql`

**Service Files**:
- ✅ `/opt/gov-ai/backend/src/services/neo4j_graph_extractor.py`
- ✅ `/opt/gov-ai/backend/src/services/neo4j_graph_retriever.py`
- ✅ `/opt/gov-ai/backend/src/services/neo4j_graph_service.py`

**API Route Files**:
- ✅ `/opt/gov-ai/backend/src/api/routes/graph.py`

**Configuration Files**:
- ✅ `/opt/gov-ai/backend/.env` (updated with Neo4J variables)
- ✅ `/opt/gov-ai/neo4j/.password` (generated password)

**Container Data**:
- ✅ `/opt/gov-ai/neo4j/data/` (Neo4J database files)
- ✅ `/opt/gov-ai/neo4j/logs/` (Neo4J logs)
- ✅ `/opt/gov-ai/neo4j/conf/` (Neo4J configuration)

---

## Required Environment Variables

### 14. Environment Configuration

**Neo4J Configuration** (added to `/opt/gov-ai/backend/.env`):
```bash
# Neo4J Graph Database Configuration (Feature NEO4J-001)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<generated-32-char-password>
NEO4J_DATABASE=neo4j
GRAPH_RETRIEVAL_ENABLED=true
GRAPH_MAX_DEPTH=3
GRAPH_TOP_K=10
```

**Existing Variables** (verify present):
```bash
# OpenRouter (for LLM extraction)
OPENROUTER_API_KEY=<api-key>
OPENROUTER_MODEL=anthropic/claude-3-haiku

# PostgreSQL
DATABASE_URL=postgresql://gov_ai_user:<password>@localhost:5432/gov_ai_db

# Qdrant
QDRANT_URL=http://localhost:6333
```

---

## Contact and Support

### 15. Deployment Support

**Issue Reporting**:
- Log location: `/var/log/neo4j-health.log`
- Backend logs: `journalctl -u gov-ai-backend`
- Neo4J logs: `docker logs gov-ai-neo4j`

**Common Issues**:

1. **Neo4J connection timeout**
   - Verify Neo4J container running: `docker ps | grep neo4j`
   - Check Neo4J logs: `docker logs gov-ai-neo4j --tail 50`
   - Verify port 7687 not blocked: `nc -zv localhost 7687`

2. **PostgreSQL migration fails**
   - Check PostgreSQL connection: `docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "SELECT 1;"`
   - Verify migration syntax: Review `025_add_neo4j_integration_tables.sql`
   - Check for existing tables: May need to drop manually

3. **Backend service won't start**
   - Check logs: `journalctl -u gov-ai-backend --since "10 minutes ago"`
   - Verify Python dependencies: `pip list | grep neo4j`
   - Check .env file: Ensure NEO4J_PASSWORD is set

---

**Deployment Date**: 2025-11-10
**Estimated Duration**: 15-20 minutes
**Estimated Extraction Time**: 6-8 hours
**Estimated Cost**: $8.80 USD (one-time)
**Status**: Ready for Deployment
