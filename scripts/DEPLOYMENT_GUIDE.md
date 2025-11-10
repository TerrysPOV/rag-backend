# Neo4J Graph Traversals - Deployment Guide
**UK Immigration RAG System - Database Deployment Scripts**

**Feature**: NEO4J-024 - Graph Traversals Integration
**Date**: 2025-11-10
**Author**: Database Developer Python T2 Agent

---

## Overview

This guide provides step-by-step instructions for deploying the Neo4J graph traversals integration for the UK Immigration RAG system.

**Deliverables**:
1. ✅ `init_neo4j_schema.cypher` - Neo4J schema initialization (UK Immigration domain)
2. ✅ `025_add_neo4j_integration_tables.sql` - PostgreSQL integration tables
3. ✅ `validate_graph_schema.sh` - Schema validation script
4. ✅ `backup_before_neo4j.sh` - Pre-migration backup script
5. ✅ `migration_metrics.md` - Migration estimates and metrics

---

## Quick Start

**Prerequisites**:
- Neo4J container running (`gov-ai-neo4j`)
- PostgreSQL container running (`gov-ai-postgres`)
- Neo4J password set in environment (`NEO4J_PASSWORD`)
- SSH access to DigitalOcean droplet (161.35.44.166)

**Deployment Commands** (Run on Droplet):

```bash
# 1. Set Neo4J password
export NEO4J_PASSWORD='your-secure-password-here'

# 2. Run backup
./scripts/backup_before_neo4j.sh

# 3. Deploy PostgreSQL migration
docker exec -i gov-ai-postgres psql -U gov_ai_user -d gov_ai_db < migrations/025_add_neo4j_integration_tables.sql

# 4. Deploy Neo4J schema
cat scripts/init_neo4j_schema.cypher | docker exec -i gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD

# 5. Validate deployment
./scripts/validate_graph_schema.sh

# 6. Review migration metrics
cat scripts/migration_metrics.md
```

**Estimated Time**: 45 minutes for deployment, 6-8 hours for data extraction

---

## Detailed Deployment Steps

### Step 1: Pre-Deployment Review

**Action**: Review the design document and migration metrics

```bash
# Read the design document
cat docs/design/database/NEO4J_GRAPH_SCHEMA_DESIGN.md

# Read the migration metrics
cat scripts/migration_metrics.md
```

**Key Metrics to Review**:
- **Documents to Process**: 1,209 chunks (corrected from initial 117,343)
- **Expected Entities**: 7,000-9,000 entities
- **Expected Relationships**: 7,000-10,000 relationships
- **Estimated Cost**: $0.40 USD (LLM API calls)
- **Estimated Duration**: 6-8 hours
- **Expected Graph Size**: 2-3 MB (much smaller than initial estimate)

**Checklist**:
- [ ] Design document reviewed
- [ ] Migration metrics reviewed
- [ ] Droplet disk space verified (need 200 MB free)
- [ ] Neo4J password secured (32 characters recommended)

---

### Step 2: Backup Existing Data

**Action**: Backup Neo4J, PostgreSQL, and Qdrant metadata

```bash
# SSH to droplet
ssh root@161.35.44.166

# Set Neo4J password
export NEO4J_PASSWORD='your-secure-password-here'

# Run backup script
./scripts/backup_before_neo4j.sh
```

**Expected Output**:
```
============================================================================
BACKUP COMPLETE
============================================================================
✓ All databases backed up successfully

Backup Location: /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_20251110_184900
Archive: /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_20251110_184900.tar.gz
Manifest: /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_20251110_184900/MANIFEST.md
Rollback Script: /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_20251110_184900/rollback.sh
```

**Verification**:
```bash
# Check backup files exist
ls -lh /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_*/

# Review backup manifest
cat /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_*/MANIFEST.md
```

**Checklist**:
- [ ] Backup directory created
- [ ] PostgreSQL dump exists and is > 1KB
- [ ] Neo4J schema exported
- [ ] Rollback script created
- [ ] Backup manifest reviewed

---

### Step 3: Deploy PostgreSQL Migration

**Action**: Create graph integration tables in PostgreSQL

```bash
# Run PostgreSQL migration
docker exec -i gov-ai-postgres psql -U gov_ai_user -d gov_ai_db < migrations/025_add_neo4j_integration_tables.sql
```

**Expected Output**:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
...
INSERT 0 1
INSERT 0 2
(4 rows)
```

**Verification**:
```bash
# Verify tables created
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c \
  "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'graph_%';"

# Expected output:
#  graph_extraction_jobs
#  graph_entity_mappings
#  graph_query_audit
#  graph_health_checks
```

**Checklist**:
- [ ] 4 tables created
- [ ] 18 indexes created
- [ ] 2 triggers created
- [ ] 4 RLS policies created
- [ ] Sample data inserted (1 job, 2 entity mappings)

---

### Step 4: Deploy Neo4J Schema

**Action**: Initialize Neo4J graph schema for UK Immigration

```bash
# Deploy Neo4J schema
cat scripts/init_neo4j_schema.cypher | docker exec -i gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD
```

**Expected Output**:
```
0 rows available after 15 ms, consumed after another 0 ms
Added 1 constraints
0 rows available after 10 ms, consumed after another 0 ms
Added 1 indexes
...
Added 9 nodes, Created 7 relationships, Set 45 properties
```

**Verification**:
```bash
# Verify constraints
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "SHOW CONSTRAINTS;"

# Verify indexes
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "SHOW INDEXES;"

# Expected:
# - 1 unique constraint (entity_id_unique)
# - 15 B-tree indexes
# - 3 full-text indexes
```

**Checklist**:
- [ ] 1 unique constraint created
- [ ] 15 B-tree indexes created
- [ ] 3 full-text indexes created
- [ ] 9 sample entities created
- [ ] 7 sample relationships created

---

### Step 5: Validate Deployment

**Action**: Run automated validation script

```bash
# Run validation script
./scripts/validate_graph_schema.sh
```

**Expected Output**:
```
============================================================================
1. VALIDATING NEO4J CONNECTION
============================================================================
✓ Neo4J connection successful

============================================================================
2. VALIDATING NEO4J CONSTRAINTS
============================================================================
✓ entity_id_unique constraint exists

...

============================================================================
VALIDATION COMPLETE
============================================================================
✓ All critical schema components validated successfully
```

**Checklist**:
- [ ] Neo4J connection successful
- [ ] All constraints exist
- [ ] All indexes exist (at least 15)
- [ ] Sample data found
- [ ] PostgreSQL connection successful
- [ ] All tables exist
- [ ] All indexes exist
- [ ] RLS policies exist

---

### Step 6: Remove Sample Data (Optional)

**Action**: Remove sample data after validation

```bash
# Remove Neo4J sample data
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n) WHERE n.id CONTAINS '_sample_' DETACH DELETE n;"

# Remove PostgreSQL sample data
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c \
  "DELETE FROM graph_entity_mappings WHERE entity_id LIKE '%_sample_%';
   DELETE FROM graph_extraction_jobs WHERE job_id = '00000000-0000-0000-0000-000000000001';"
```

**Verification**:
```bash
# Verify sample data removed
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n) WHERE n.id CONTAINS '_sample_' RETURN count(n);"

# Expected: count(n) = 0
```

**Checklist**:
- [ ] Neo4J sample data removed (0 nodes)
- [ ] PostgreSQL sample data removed (0 rows)
- [ ] Schema still intact (constraints/indexes remain)

---

## Post-Deployment

### Next Steps

1. **Trigger Initial Extraction** (via backend API):
   ```bash
   curl -X POST https://vectorgov.poview.ai/api/rag/graph/extract \
     -H "Authorization: Bearer <admin-token>" \
     -H "Content-Type: application/json" \
     -d '{
       "enable_llm_extraction": true,
       "batch_size": 50,
       "max_workers": 4
     }'
   ```

2. **Monitor Extraction Progress**:
   ```bash
   # Watch extraction job progress
   watch -n 60 'curl -s https://vectorgov.poview.ai/api/rag/graph/stats | jq'
   ```

3. **Review Extraction Logs**:
   ```bash
   # Check backend logs for errors
   docker logs -f gov-ai-backend | grep -i "graph"
   ```

4. **Validate Graph Quality**:
   ```bash
   # Run health check
   curl https://vectorgov.poview.ai/api/rag/graph/health | jq
   ```

---

## Troubleshooting

### Issue 1: Neo4J Connection Failed

**Symptom**: `validate_graph_schema.sh` reports "Failed to connect to Neo4J"

**Solution**:
```bash
# Check Neo4J container is running
docker ps | grep neo4j

# Check Neo4J logs
docker logs gov-ai-neo4j | tail -50

# Verify password is correct
echo $NEO4J_PASSWORD

# Test connection manually
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1;"
```

---

### Issue 2: PostgreSQL Migration Failed

**Symptom**: `psql` reports errors during migration

**Solution**:
```bash
# Check PostgreSQL logs
docker logs gov-ai-postgres | tail -50

# Verify database exists
docker exec gov-ai-postgres psql -U gov_ai_user -l

# Check for conflicting tables
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c \
  "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'graph_%';"

# Rollback if needed
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db <<'EOF'
DROP TABLE IF EXISTS graph_health_checks CASCADE;
DROP TABLE IF EXISTS graph_query_audit CASCADE;
DROP TABLE IF EXISTS graph_entity_mappings CASCADE;
DROP TABLE IF EXISTS graph_extraction_jobs CASCADE;
EOF
```

---

### Issue 3: Validation Script Fails

**Symptom**: `validate_graph_schema.sh` reports missing indexes or constraints

**Solution**:
```bash
# Re-run Neo4J schema initialization
cat scripts/init_neo4j_schema.cypher | docker exec -i gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Verify indexes manually
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "SHOW INDEXES;"

# If indexes are missing, create them individually (see init_neo4j_schema.cypher for commands)
```

---

### Issue 4: Extraction Job Fails

**Symptom**: Extraction job status = 'failed' with error message

**Common Causes**:
1. **LLM API Rate Limit**: Reduce batch size, add delays between batches
2. **Neo4J Connection Timeout**: Increase connection pool size
3. **Memory Exhaustion**: Reduce number of workers from 4 to 2
4. **Invalid Chunk References**: Run consistency check before extraction

**Solution**:
```sql
-- Check extraction job errors
SELECT job_id, status, error_message, error_traceback
FROM graph_extraction_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 1;

-- Reset failed job for retry
UPDATE graph_extraction_jobs
SET status = 'queued', started_at = NULL, error_message = NULL
WHERE job_id = '<failed-job-id>';
```

---

## Rollback Instructions

### Full Rollback (Restore from Backup)

```bash
# Navigate to backup directory
cd /opt/gov-ai/backups/neo4j-migration/neo4j_migration_backup_<timestamp>/

# Run rollback script
./rollback.sh

# Verify restoration
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c \
  "SELECT COUNT(*) FROM graph_extraction_jobs;"

# Expected: 0 rows (or sample data count)
```

### Partial Rollback (Remove Extraction Data Only)

```bash
# Delete extracted entities from Neo4J
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n:Entity) DETACH DELETE n;"

# Delete metadata from PostgreSQL
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db <<'EOF'
DELETE FROM graph_entity_mappings;
DELETE FROM graph_extraction_jobs;
DELETE FROM graph_query_audit;
DELETE FROM graph_health_checks;
EOF
```

---

## File Reference

### Scripts

| File | Purpose | Location |
|------|---------|----------|
| **init_neo4j_schema.cypher** | Neo4J schema initialization | `/backend-source/scripts/` |
| **validate_graph_schema.sh** | Schema validation | `/backend-source/scripts/` |
| **backup_before_neo4j.sh** | Pre-migration backup | `/backend-source/scripts/` |
| **migration_metrics.md** | Migration estimates | `/backend-source/scripts/` |

### Migrations

| File | Purpose | Location |
|------|---------|----------|
| **025_add_neo4j_integration_tables.sql** | PostgreSQL integration tables | `/backend-source/migrations/` |

### Documentation

| File | Purpose | Location |
|------|---------|----------|
| **NEO4J_GRAPH_SCHEMA_DESIGN.md** | Complete design document | `/docs/design/database/` |
| **DEPLOYMENT_GUIDE.md** | This file | `/backend-source/scripts/` |

---

## Success Criteria

Deployment is successful when:

1. ✅ **Neo4J Schema**:
   - 1 unique constraint exists
   - 15 B-tree indexes exist
   - 3 full-text indexes exist
   - Sample queries return results

2. ✅ **PostgreSQL Tables**:
   - 4 tables created
   - 18 indexes created
   - 2 triggers created
   - 4 RLS policies created

3. ✅ **Validation**:
   - `validate_graph_schema.sh` passes all checks
   - No errors in logs
   - Sample data queries work

4. ✅ **Extraction** (after deployment):
   - 7,000-9,000 entities extracted
   - 7,000-10,000 relationships created
   - Extraction success rate > 95%
   - Query latency p95 < 500ms

---

## Support

**Questions or Issues?**
- Review design document: `/docs/design/database/NEO4J_GRAPH_SCHEMA_DESIGN.md`
- Check migration metrics: `/backend-source/scripts/migration_metrics.md`
- Create GitHub issue with tag `neo4j-integration`

**Useful Commands**:
```bash
# Check Neo4J health
docker exec gov-ai-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL dbms.components() YIELD name, versions, edition;"

# Check PostgreSQL health
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c "SELECT version();"

# Check extraction job status
docker exec gov-ai-postgres psql -U gov_ai_user -d gov_ai_db -c \
  "SELECT job_id, status, documents_processed, total_documents, entities_extracted FROM graph_extraction_jobs ORDER BY created_at DESC LIMIT 5;"
```

---

**Document Metadata**

**Author**: Database Developer Python T2 Agent
**Created**: 2025-11-10
**Version**: 1.0.0
**Status**: Production Ready

---

🤖 Generated with Claude Code
Database Developer Python T2 Agent
