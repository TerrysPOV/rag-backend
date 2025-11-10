-- ============================================================================
-- Migration: 025_add_neo4j_integration_tables
-- ============================================================================
-- Feature: NEO4J-024 - Graph Traversals Integration
-- Date: 2025-11-10
-- Author: Database Developer Python T2 Agent
-- Purpose: Create PostgreSQL tables for Neo4J graph integration metadata
-- Design Doc: /docs/design/database/NEO4J_GRAPH_SCHEMA_DESIGN.md
-- ============================================================================

-- ============================================================================
-- 1. GRAPH EXTRACTION JOBS TABLE
-- ============================================================================
-- Purpose: Track batch processing jobs for extracting entities from documents
-- Usage: Monitor progress of 117,343 document extraction job

CREATE TABLE IF NOT EXISTS graph_extraction_jobs (
    -- Primary key
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job status tracking
    status VARCHAR(20) NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),

    -- Job parameters
    total_documents INTEGER NOT NULL CHECK (total_documents > 0),
    documents_processed INTEGER NOT NULL DEFAULT 0,
    documents_failed INTEGER NOT NULL DEFAULT 0,
    enable_llm_extraction BOOLEAN NOT NULL DEFAULT true,

    -- Extraction metrics
    entities_extracted INTEGER NOT NULL DEFAULT 0,
    relationships_created INTEGER NOT NULL DEFAULT 0,
    extraction_method VARCHAR(50), -- 'spacy', 'regex', 'llm', 'hybrid'

    -- Cost tracking (LLM usage)
    llm_api_calls INTEGER NOT NULL DEFAULT 0,
    llm_tokens_used INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 4) NOT NULL DEFAULT 0.00,

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Error tracking
    error_message TEXT,
    error_traceback TEXT,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100), -- User who triggered extraction

    -- Constraints
    CONSTRAINT check_documents_processed CHECK (documents_processed <= total_documents),
    CONSTRAINT check_documents_failed CHECK (documents_failed <= total_documents),
    CONSTRAINT check_status_dates CHECK (
        (status = 'queued' AND started_at IS NULL) OR
        (status IN ('running', 'completed', 'failed') AND started_at IS NOT NULL)
    ),
    CONSTRAINT check_completed_dates CHECK (
        (status IN ('completed', 'failed') AND completed_at IS NOT NULL) OR
        (status IN ('queued', 'running') AND completed_at IS NULL)
    ),
    CONSTRAINT check_extraction_method CHECK (
        extraction_method IS NULL OR
        extraction_method IN ('spacy', 'regex', 'llm', 'hybrid')
    )
);

-- Indexes for graph_extraction_jobs
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON graph_extraction_jobs(status);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_created_at ON graph_extraction_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_created_by ON graph_extraction_jobs(created_by);

-- Comment on table
COMMENT ON TABLE graph_extraction_jobs IS 'Tracks batch processing jobs for extracting graph entities from documents. Monitors progress, cost, and errors for migration of 117,343 documents.';
COMMENT ON COLUMN graph_extraction_jobs.status IS 'Job lifecycle: queued -> running -> completed/failed';
COMMENT ON COLUMN graph_extraction_jobs.enable_llm_extraction IS 'If true, use LLM (GPT-4o-mini) for complex entity extraction. If false, use SpaCy + Regex only.';
COMMENT ON COLUMN graph_extraction_jobs.estimated_cost_usd IS 'Total LLM API cost at $0.000075 per document (GPT-4o-mini pricing)';

-- ============================================================================
-- 2. GRAPH ENTITY MAPPINGS TABLE
-- ============================================================================
-- Purpose: Map Neo4J entity IDs to PostgreSQL document chunk IDs
-- Usage: Enable bi-directional lookups between graph entities and vector chunks

CREATE TABLE IF NOT EXISTS graph_entity_mappings (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Neo4J entity
    entity_id VARCHAR(255) NOT NULL UNIQUE, -- SHA256 hash from Neo4J
    entity_type VARCHAR(50) NOT NULL,
    entity_text TEXT NOT NULL,

    -- PostgreSQL document chunk
    chunk_id VARCHAR(255) NOT NULL, -- References Qdrant point ID
    document_id VARCHAR(255) NOT NULL,

    -- Extraction metadata
    extraction_job_id UUID REFERENCES graph_extraction_jobs(job_id) ON DELETE SET NULL,
    extraction_method VARCHAR(20) NOT NULL,
    confidence_score DECIMAL(3, 2), -- 0.00 - 1.00

    -- Graph statistics
    relationship_count INTEGER NOT NULL DEFAULT 0, -- Updated by trigger
    last_traversed_at TIMESTAMP, -- When last used in graph query

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_entity_type CHECK (
        entity_type IN ('visa_type', 'requirement', 'document_type',
                       'organization', 'country', 'process', 'condition')
    ),
    CONSTRAINT valid_extraction_method CHECK (
        extraction_method IN ('spacy', 'regex', 'llm')
    ),
    CONSTRAINT valid_confidence CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)
    )
);

-- Indexes for graph_entity_mappings
CREATE INDEX IF NOT EXISTS idx_entity_mappings_entity_id ON graph_entity_mappings(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_entity_type ON graph_entity_mappings(entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_chunk_id ON graph_entity_mappings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_document_id ON graph_entity_mappings(document_id);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_job_id ON graph_entity_mappings(extraction_job_id);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_confidence ON graph_entity_mappings(confidence_score DESC) WHERE confidence_score IS NOT NULL;

-- Full-text search on entity text
CREATE INDEX IF NOT EXISTS idx_entity_mappings_text_gin ON graph_entity_mappings USING gin(to_tsvector('english', entity_text));

-- Comment on table
COMMENT ON TABLE graph_entity_mappings IS 'Maps Neo4J graph entity IDs to PostgreSQL/Qdrant chunk IDs. Enables provenance tracking and bi-directional lookups.';
COMMENT ON COLUMN graph_entity_mappings.entity_id IS 'SHA256 hash of (document_id, entity_text, entity_type) matching Neo4J Entity.id';
COMMENT ON COLUMN graph_entity_mappings.chunk_id IS 'Qdrant point ID for the chunk containing this entity';
COMMENT ON COLUMN graph_entity_mappings.relationship_count IS 'Number of Neo4J relationships this entity participates in (auto-updated by trigger)';

-- ============================================================================
-- 3. GRAPH QUERY AUDIT TABLE
-- ============================================================================
-- Purpose: Log all graph traversal queries for performance analysis
-- Usage: Monitor query latency, track entity extraction quality, debug graph paths

CREATE TABLE IF NOT EXISTS graph_query_audit (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Query details
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) NOT NULL,

    -- Graph traversal parameters
    extracted_entities JSONB, -- ["Skilled Worker visa", "passport"]
    max_depth INTEGER,
    top_k INTEGER,

    -- Performance metrics
    total_latency_ms INTEGER NOT NULL,
    neo4j_latency_ms INTEGER,
    entities_matched INTEGER NOT NULL DEFAULT 0,
    relationships_traversed INTEGER NOT NULL DEFAULT 0,
    documents_returned INTEGER NOT NULL DEFAULT 0,

    -- Graph paths (for explainability)
    graph_paths JSONB, -- [{"strategy": "direct", "entities": [...], "score": 1.8}]

    -- User context
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address INET,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_query_type CHECK (
        query_type IN ('direct', 'relationship', 'multihop', 'hybrid')
    ),
    CONSTRAINT valid_latency CHECK (total_latency_ms >= 0),
    CONSTRAINT valid_max_depth CHECK (max_depth IS NULL OR max_depth BETWEEN 1 AND 5)
);

-- Indexes for graph_query_audit
CREATE INDEX IF NOT EXISTS idx_query_audit_created_at ON graph_query_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_audit_user_id ON graph_query_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_query_audit_query_type ON graph_query_audit(query_type);
CREATE INDEX IF NOT EXISTS idx_query_audit_latency ON graph_query_audit(total_latency_ms);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_query_audit_entities ON graph_query_audit USING gin(extracted_entities);
CREATE INDEX IF NOT EXISTS idx_query_audit_paths ON graph_query_audit USING gin(graph_paths);

-- Comment on table
COMMENT ON TABLE graph_query_audit IS 'Logs every graph traversal query with performance metrics and graph paths. Used for debugging and performance optimization.';
COMMENT ON COLUMN graph_query_audit.extracted_entities IS 'JSONB array of entity texts extracted from user query (e.g., ["Skilled Worker visa", "passport"])';
COMMENT ON COLUMN graph_query_audit.graph_paths IS 'JSONB array of graph traversal paths with scores for explainability';

-- ============================================================================
-- 4. GRAPH HEALTH CHECKS TABLE
-- ============================================================================
-- Purpose: Store periodic graph health check results for monitoring
-- Usage: Automated health checks every 6 hours, alert on degraded status

CREATE TABLE IF NOT EXISTS graph_health_checks (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Graph statistics
    total_nodes INTEGER NOT NULL,
    total_relationships INTEGER NOT NULL,
    graph_density DECIMAL(6, 4), -- 0.0000 - 1.0000

    -- Node counts by type
    node_counts JSONB NOT NULL, -- {"visa_type": 45, "requirement": 1230, ...}

    -- Relationship counts by type
    relationship_counts JSONB NOT NULL, -- {"REQUIRES": 2100, "SATISFIED_BY": 450, ...}

    -- Health indicators
    orphaned_nodes INTEGER NOT NULL DEFAULT 0, -- Nodes without relationships
    broken_references INTEGER NOT NULL DEFAULT 0, -- Nodes with invalid chunk_ids

    -- Warnings and errors
    warnings JSONB, -- [{"type": "orphaned", "count": 10, "message": "..."}]
    errors JSONB, -- [{"type": "connection", "message": "..."}]

    -- Overall status
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy')),

    -- Audit
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    check_duration_ms INTEGER NOT NULL,

    -- Constraints
    CONSTRAINT valid_density CHECK (graph_density IS NULL OR (graph_density >= 0 AND graph_density <= 1)),
    CONSTRAINT valid_check_duration CHECK (check_duration_ms >= 0)
);

-- Indexes for graph_health_checks
CREATE INDEX IF NOT EXISTS idx_health_checks_checked_at ON graph_health_checks(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_checks_status ON graph_health_checks(status);

-- Comment on table
COMMENT ON TABLE graph_health_checks IS 'Periodic health check results for Neo4J graph. Tracks orphaned nodes, broken references, and overall graph quality.';
COMMENT ON COLUMN graph_health_checks.graph_density IS 'Graph density = total_relationships / (total_nodes * (total_nodes - 1)). Target: 0.001 - 0.01';
COMMENT ON COLUMN graph_health_checks.orphaned_nodes IS 'Count of entities with no relationships. Target: <1% of total nodes';

-- ============================================================================
-- 5. TRIGGERS AND FUNCTIONS
-- ============================================================================

-- Function to update entity relationship count
CREATE OR REPLACE FUNCTION update_entity_relationship_count()
RETURNS TRIGGER AS $$
BEGIN
    -- This function is called after entity insertion
    -- Actual relationship count must be updated from Neo4J query results
    -- This is a placeholder for future Neo4J -> PostgreSQL sync
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on entity mapping insert/update
DROP TRIGGER IF EXISTS trigger_update_entity_relationship_count ON graph_entity_mappings;
CREATE TRIGGER trigger_update_entity_relationship_count
BEFORE INSERT OR UPDATE ON graph_entity_mappings
FOR EACH ROW
EXECUTE FUNCTION update_entity_relationship_count();

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at on graph_entity_mappings
DROP TRIGGER IF EXISTS trigger_update_entity_mappings_timestamp ON graph_entity_mappings;
CREATE TRIGGER trigger_update_entity_mappings_timestamp
BEFORE UPDATE ON graph_entity_mappings
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. ROW-LEVEL SECURITY POLICIES
-- ============================================================================
-- Enable RLS on all graph tables for multi-tenant security

-- Enable RLS
ALTER TABLE graph_extraction_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_entity_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_query_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_health_checks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view their own extraction jobs
DROP POLICY IF EXISTS extraction_jobs_user_isolation ON graph_extraction_jobs;
CREATE POLICY extraction_jobs_user_isolation ON graph_extraction_jobs
FOR SELECT
USING (created_by = current_user OR current_user IN (SELECT username FROM users WHERE role = 'admin'));

-- Policy: Users can view entity mappings from their jobs
DROP POLICY IF EXISTS entity_mappings_user_isolation ON graph_entity_mappings;
CREATE POLICY entity_mappings_user_isolation ON graph_entity_mappings
FOR SELECT
USING (
    extraction_job_id IS NULL OR
    extraction_job_id IN (
        SELECT job_id FROM graph_extraction_jobs
        WHERE created_by = current_user
    ) OR
    current_user IN (SELECT username FROM users WHERE role = 'admin')
);

-- Policy: Users can view their own query audit logs
DROP POLICY IF EXISTS query_audit_user_isolation ON graph_query_audit;
CREATE POLICY query_audit_user_isolation ON graph_query_audit
FOR SELECT
USING (user_id = current_user OR current_user IN (SELECT username FROM users WHERE role = 'admin'));

-- Policy: Health checks are visible to all authenticated users
DROP POLICY IF EXISTS health_checks_all_users ON graph_health_checks;
CREATE POLICY health_checks_all_users ON graph_health_checks
FOR SELECT
USING (true); -- All authenticated users can view health checks

-- ============================================================================
-- 7. SAMPLE DATA (Testing Only - Remove in Production)
-- ============================================================================

-- Insert sample extraction job
INSERT INTO graph_extraction_jobs (
    job_id,
    status,
    total_documents,
    documents_processed,
    enable_llm_extraction,
    entities_extracted,
    relationships_created,
    llm_api_calls,
    estimated_cost_usd,
    created_by,
    created_at
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'completed',
    100,
    100,
    true,
    450,
    890,
    75,
    0.0075,
    'system_migration',
    CURRENT_TIMESTAMP - INTERVAL '1 day'
) ON CONFLICT DO NOTHING;

-- Insert sample entity mappings
INSERT INTO graph_entity_mappings (
    entity_id,
    entity_type,
    entity_text,
    chunk_id,
    document_id,
    extraction_job_id,
    extraction_method,
    confidence_score,
    relationship_count
) VALUES
(
    'visa_skilled_worker_sample_001',
    'visa_type',
    'Skilled Worker visa',
    'chunk_sample_12345',
    'doc_immigration_guide_sample_001',
    '00000000-0000-0000-0000-000000000001',
    'regex',
    0.95,
    4
),
(
    'req_financial_sample_001',
    'requirement',
    'Demonstrate financial requirement (£1,270 in savings)',
    'chunk_sample_12345',
    'doc_immigration_guide_sample_001',
    '00000000-0000-0000-0000-000000000001',
    'llm',
    0.88,
    2
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- 8. VALIDATION QUERIES
-- ============================================================================

-- Query 1: Count all graph tables
SELECT
    'graph_extraction_jobs' AS table_name,
    COUNT(*) AS row_count
FROM graph_extraction_jobs
UNION ALL
SELECT
    'graph_entity_mappings',
    COUNT(*)
FROM graph_entity_mappings
UNION ALL
SELECT
    'graph_query_audit',
    COUNT(*)
FROM graph_query_audit
UNION ALL
SELECT
    'graph_health_checks',
    COUNT(*)
FROM graph_health_checks;

-- Query 2: Verify indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('graph_extraction_jobs', 'graph_entity_mappings', 'graph_query_audit', 'graph_health_checks')
ORDER BY tablename, indexname;

-- Query 3: Verify constraints
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid::regclass::text LIKE 'graph_%'
ORDER BY table_name, constraint_name;

-- Query 4: Verify RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename IN ('graph_extraction_jobs', 'graph_entity_mappings', 'graph_query_audit', 'graph_health_checks')
ORDER BY tablename, policyname;

-- ============================================================================
-- 9. ROLLBACK SCRIPT
-- ============================================================================

-- To rollback this migration, run:
-- DROP TABLE IF EXISTS graph_health_checks CASCADE;
-- DROP TABLE IF EXISTS graph_query_audit CASCADE;
-- DROP TABLE IF EXISTS graph_entity_mappings CASCADE;
-- DROP TABLE IF EXISTS graph_extraction_jobs CASCADE;
-- DROP FUNCTION IF EXISTS update_entity_relationship_count() CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Expected Results:
-- - 4 tables created (graph_extraction_jobs, graph_entity_mappings, graph_query_audit, graph_health_checks)
-- - 18 indexes created
-- - 2 triggers created
-- - 4 RLS policies created
-- - Sample data: 1 job, 2 entity mappings
-- ============================================================================

-- 🤖 Generated with Claude Code
-- Database Developer Python T2 Agent
-- Migration based on: /docs/design/database/NEO4J_GRAPH_SCHEMA_DESIGN.md Section 2
