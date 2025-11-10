// ============================================================================
// UK IMMIGRATION GRAPH SCHEMA - DEPLOYMENT SCRIPT
// ============================================================================
// Feature: NEO4J-024 - Graph Traversals Integration
// Date: 2025-11-10
// Database: Neo4J Community Edition 5.14+
// Purpose: Initialize UK Immigration graph schema for RAG system
// Deployment Target: DigitalOcean Droplet (161.35.44.166)
// ============================================================================

// ============================================================================
// 1. CONSTRAINTS (Data Integrity)
// ============================================================================
// These constraints ensure data integrity and prevent duplicate entities

// Entity ID uniqueness constraint (applies to all entity types)
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity)
REQUIRE e.id IS UNIQUE;

// ============================================================================
// 2. PROPERTY EXISTENCE CONSTRAINTS (Neo4J Enterprise only - commented out)
// ============================================================================
// Uncomment if using Neo4J Enterprise Edition for additional validation

// CREATE CONSTRAINT entity_id_exists IF NOT EXISTS
// FOR (e:Entity)
// REQUIRE e.id IS NOT NULL;

// CREATE CONSTRAINT entity_text_exists IF NOT EXISTS
// FOR (e:Entity)
// REQUIRE e.text IS NOT NULL;

// ============================================================================
// 3. INDEXES (Query Performance)
// ============================================================================
// These indexes optimize common query patterns for UK Immigration use cases

// -------------------------------
// Entity base indexes
// -------------------------------
CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_chunk_id_index IF NOT EXISTS
FOR (e:Entity) ON (e.chunk_id);

CREATE INDEX entity_document_id_index IF NOT EXISTS
FOR (e:Entity) ON (e.document_id);

// -------------------------------
// visa_type indexes
// -------------------------------
CREATE INDEX visa_type_text_index IF NOT EXISTS
FOR (v:visa_type) ON (v.text);

CREATE INDEX visa_type_category_index IF NOT EXISTS
FOR (v:visa_type) ON (v.category);

// -------------------------------
// requirement indexes
// -------------------------------
CREATE INDEX requirement_category_index IF NOT EXISTS
FOR (r:requirement) ON (r.category);

CREATE INDEX requirement_mandatory_index IF NOT EXISTS
FOR (r:requirement) ON (r.mandatory);

// Composite index for filtering mandatory requirements by category
CREATE INDEX requirement_mandatory_category IF NOT EXISTS
FOR (r:requirement) ON (r.mandatory, r.category);

// -------------------------------
// document_type indexes
// -------------------------------
CREATE INDEX document_type_text_index IF NOT EXISTS
FOR (d:document_type) ON (d.text);

// -------------------------------
// organization indexes
// -------------------------------
CREATE INDEX organization_text_index IF NOT EXISTS
FOR (o:organization) ON (o.text);

// -------------------------------
// country indexes
// -------------------------------
CREATE INDEX country_text_index IF NOT EXISTS
FOR (c:country) ON (c.text);

// -------------------------------
// process indexes
// -------------------------------
CREATE INDEX process_step_number_index IF NOT EXISTS
FOR (p:process) ON (p.step_number);

// ============================================================================
// 4. FULL-TEXT SEARCH INDEXES
// ============================================================================
// These indexes enable semantic search across entity text fields

// Full-text search on all entity text (supports fuzzy matching)
CREATE FULLTEXT INDEX entityTextIndex IF NOT EXISTS
FOR (e:Entity) ON EACH [e.text];

// Full-text search on visa types (supports "Student visa" -> "Tier 4 visa")
CREATE FULLTEXT INDEX visaTypeIndex IF NOT EXISTS
FOR (v:visa_type) ON EACH [v.text];

// Full-text search on requirements (supports keyword-based filtering)
CREATE FULLTEXT INDEX requirementIndex IF NOT EXISTS
FOR (r:requirement) ON EACH [r.text];

// ============================================================================
// 5. RELATIONSHIP INDEXES (Optional - for large graphs)
// ============================================================================
// These indexes optimize relationship traversal queries

// Index on REQUIRES relationship mandatory property
CREATE INDEX requires_mandatory IF NOT EXISTS
FOR ()-[r:REQUIRES]-() ON (r.mandatory);

// Index on SATISFIED_BY relationships (for document lookup)
CREATE INDEX satisfied_by_created_at IF NOT EXISTS
FOR ()-[r:SATISFIED_BY]-() ON (r.created_at);

// ============================================================================
// 6. SAMPLE DATA (Testing Only)
// ============================================================================
// Sample entities and relationships for schema validation
// REMOVE IN PRODUCTION after validation completes

// Create sample visa type: Skilled Worker visa
CREATE (v:Entity:visa_type {
  id: 'visa_skilled_worker_sample_001',
  text: 'Skilled Worker visa',
  category: 'work',
  chunk_id: 'chunk_sample_12345',
  document_id: 'doc_immigration_guide_sample_001',
  created_at: datetime()
});

// Create sample requirement: Financial requirement
CREATE (r1:Entity:requirement {
  id: 'req_financial_sample_001',
  text: 'Demonstrate financial requirement (£1,270 in savings)',
  category: 'financial',
  mandatory: true,
  chunk_id: 'chunk_sample_12345',
  document_id: 'doc_immigration_guide_sample_001',
  created_at: datetime()
});

// Create sample requirement: Sponsorship requirement
CREATE (r2:Entity:requirement {
  id: 'req_sponsorship_sample_001',
  text: 'Obtain sponsorship from licensed UK employer',
  category: 'sponsorship',
  mandatory: true,
  chunk_id: 'chunk_sample_12346',
  document_id: 'doc_immigration_guide_sample_001',
  created_at: datetime()
});

// Create sample document type: Bank statement
CREATE (d1:Entity:document_type {
  id: 'doc_type_bank_statement_sample_001',
  text: 'bank statement',
  chunk_id: 'chunk_sample_12347',
  document_id: 'doc_immigration_guide_sample_002',
  created_at: datetime()
});

// Create sample document type: Certificate of Sponsorship
CREATE (d2:Entity:document_type {
  id: 'doc_type_cos_sample_001',
  text: 'Certificate of Sponsorship (CoS)',
  chunk_id: 'chunk_sample_12348',
  document_id: 'doc_immigration_guide_sample_002',
  created_at: datetime()
});

// Create sample organization: Home Office
CREATE (o:Entity:organization {
  id: 'org_home_office_sample_001',
  text: 'UK Home Office',
  chunk_id: 'chunk_sample_12349',
  document_id: 'doc_immigration_guide_sample_003',
  created_at: datetime()
});

// Create sample country: United Kingdom
CREATE (c:Entity:country {
  id: 'country_uk_sample_001',
  text: 'United Kingdom',
  chunk_id: 'chunk_sample_12350',
  document_id: 'doc_immigration_guide_sample_003',
  created_at: datetime()
});

// Create sample process step
CREATE (p:Entity:process {
  id: 'process_apply_sample_001',
  text: 'Submit online application via gov.uk',
  step_number: 1,
  chunk_id: 'chunk_sample_12351',
  document_id: 'doc_immigration_guide_sample_004',
  created_at: datetime()
});

// Create sample condition
CREATE (cond:Entity:condition {
  id: 'condition_uk_degree_sample_001',
  text: 'If applicant has UK degree, English language requirement waived',
  applies_when: 'uk_degree_holder',
  chunk_id: 'chunk_sample_12352',
  document_id: 'doc_immigration_guide_sample_004',
  created_at: datetime()
});

// ============================================================================
// 7. SAMPLE RELATIONSHIPS
// ============================================================================
// Create relationships between sample entities for testing graph traversals

// Skilled Worker visa REQUIRES financial requirement (mandatory)
MATCH (v:visa_type {id: 'visa_skilled_worker_sample_001'}),
      (r:requirement {id: 'req_financial_sample_001'})
CREATE (v)-[:REQUIRES {mandatory: true, created_at: datetime()}]->(r);

// Skilled Worker visa REQUIRES sponsorship requirement (mandatory)
MATCH (v:visa_type {id: 'visa_skilled_worker_sample_001'}),
      (r:requirement {id: 'req_sponsorship_sample_001'})
CREATE (v)-[:REQUIRES {mandatory: true, created_at: datetime()}]->(r);

// Financial requirement SATISFIED_BY bank statement
MATCH (r:requirement {id: 'req_financial_sample_001'}),
      (d:document_type {id: 'doc_type_bank_statement_sample_001'})
CREATE (r)-[:SATISFIED_BY {created_at: datetime()}]->(d);

// Sponsorship requirement SATISFIED_BY Certificate of Sponsorship
MATCH (r:requirement {id: 'req_sponsorship_sample_001'}),
      (d:document_type {id: 'doc_type_cos_sample_001'})
CREATE (r)-[:SATISFIED_BY {created_at: datetime()}]->(d);

// Skilled Worker visa ISSUED_BY Home Office
MATCH (v:visa_type {id: 'visa_skilled_worker_sample_001'}),
      (o:organization {id: 'org_home_office_sample_001'})
CREATE (v)-[:ISSUED_BY {created_at: datetime()}]->(o);

// Skilled Worker visa APPLIES_TO United Kingdom
MATCH (v:visa_type {id: 'visa_skilled_worker_sample_001'}),
      (c:country {id: 'country_uk_sample_001'})
CREATE (v)-[:APPLIES_TO {created_at: datetime()}]->(c);

// Financial requirement APPLIES_IF condition (UK degree waiver)
MATCH (r:requirement {id: 'req_financial_sample_001'}),
      (cond:condition {id: 'condition_uk_degree_sample_001'})
CREATE (r)-[:APPLIES_IF {created_at: datetime()}]->(cond);

// ============================================================================
// 8. VERIFICATION QUERIES
// ============================================================================
// Run these queries to validate schema was created correctly

// Query 1: Count nodes by label
MATCH (n)
RETURN labels(n) AS label, count(n) AS count
ORDER BY count DESC;

// Query 2: Count relationships by type
MATCH ()-[r]->()
RETURN type(r) AS type, count(r) AS count
ORDER BY count DESC;

// Query 3: Sample graph traversal - Find documents for Skilled Worker visa
MATCH (v:visa_type {text: 'Skilled Worker visa'})
MATCH (v)-[:REQUIRES]->(r:requirement)
MATCH (r)-[:SATISFIED_BY]->(d:document_type)
RETURN
  v.text AS visa,
  r.text AS requirement,
  r.mandatory AS is_mandatory,
  d.text AS document
LIMIT 10;

// Query 4: List all constraints
SHOW CONSTRAINTS;

// Query 5: List all indexes
SHOW INDEXES;

// ============================================================================
// 9. CLEANUP COMMANDS (For Development Only)
// ============================================================================
// Use these commands to remove sample data or reset the database
// WARNING: Destructive operations - use with caution!

// Remove ONLY sample data (keeps schema intact)
// MATCH (n)
// WHERE n.id CONTAINS '_sample_'
// DETACH DELETE n;

// DANGER: Remove ALL data (destroys entire graph)
// MATCH (n) DETACH DELETE n;

// DANGER: Drop all constraints and indexes
// DROP CONSTRAINT entity_id_unique IF EXISTS;
// DROP INDEX entity_type_index IF EXISTS;
// DROP INDEX entityTextIndex IF EXISTS;
// ... (etc. for all constraints/indexes)

// ============================================================================
// 10. EXPECTED SCHEMA VALIDATION OUTPUT
// ============================================================================
// After running this script, you should see:
//
// CONSTRAINTS: 1 unique constraint (entity_id_unique)
// INDEXES: 15 B-tree indexes + 3 full-text indexes
// SAMPLE NODES: 9 nodes (1 visa, 2 requirements, 2 documents, 1 org, 1 country, 1 process, 1 condition)
// SAMPLE RELATIONSHIPS: 7 relationships
//
// Expected query results:
// - Query 1: 9 nodes across 8 labels
// - Query 2: 7 relationships across 5 types
// - Query 3: 2 documents (bank statement, CoS) for Skilled Worker visa
// ============================================================================

// ============================================================================
// DEPLOYMENT NOTES
// ============================================================================
// 1. Run this script via cypher-shell:
//    cat init_neo4j_schema.cypher | docker exec -i gov-ai-neo4j cypher-shell -u neo4j -p <password>
//
// 2. Verify schema creation:
//    docker exec gov-ai-neo4j cypher-shell -u neo4j -p <password> "SHOW CONSTRAINTS;"
//    docker exec gov-ai-neo4j cypher-shell -u neo4j -p <password> "SHOW INDEXES;"
//
// 3. Test sample query:
//    docker exec gov-ai-neo4j cypher-shell -u neo4j -p <password> \
//      "MATCH (v:visa_type)-[:REQUIRES]->(r:requirement)-[:SATISFIED_BY]->(d:document_type) RETURN v.text, r.text, d.text LIMIT 5;"
//
// 4. Remove sample data after validation:
//    docker exec gov-ai-neo4j cypher-shell -u neo4j -p <password> \
//      "MATCH (n) WHERE n.id CONTAINS '_sample_' DETACH DELETE n;"
//
// 5. Estimated execution time: 2-3 seconds
// ============================================================================

// 🤖 Generated with Claude Code
// Database Developer Python T2 Agent
// Schema based on: /docs/design/database/NEO4J_GRAPH_SCHEMA_DESIGN.md
