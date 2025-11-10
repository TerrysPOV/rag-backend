// ============================================================================
// UK IMMIGRATION GRAPH SCHEMA
// Feature: NEO4J-001 - Graph Traversals Integration
// Date: 2025-11-10
// Database: Neo4J Community Edition 5.14+
// ============================================================================

// ============================================================================
// 1. CONSTRAINTS (Data Integrity)
// ============================================================================

// Entity ID uniqueness (all entity types)
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity)
REQUIRE e.id IS UNIQUE;

// ============================================================================
// 2. INDEXES (Query Performance)
// ============================================================================

// Entity base indexes
CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_chunk_id_index IF NOT EXISTS
FOR (e:Entity) ON (e.chunk_id);

CREATE INDEX entity_document_id_index IF NOT EXISTS
FOR (e:Entity) ON (e.document_id);

// visa_type indexes
CREATE INDEX visa_type_text_index IF NOT EXISTS
FOR (v:visa_type) ON (v.text);

CREATE INDEX visa_type_category_index IF NOT EXISTS
FOR (v:visa_type) ON (v.category);

// requirement indexes
CREATE INDEX requirement_category_index IF NOT EXISTS
FOR (r:requirement) ON (r.category);

CREATE INDEX requirement_mandatory_index IF NOT EXISTS
FOR (r:requirement) ON (r.mandatory);

// Composite index for common pattern
CREATE INDEX requirement_mandatory_category IF NOT EXISTS
FOR (r:requirement) ON (r.mandatory, r.category);

// document_type indexes
CREATE INDEX document_type_text_index IF NOT EXISTS
FOR (d:document_type) ON (d.text);

// organization indexes
CREATE INDEX organization_text_index IF NOT EXISTS
FOR (o:organization) ON (o.text);

// country indexes
CREATE INDEX country_text_index IF NOT EXISTS
FOR (c:country) ON (c.text);

// ============================================================================
// 3. FULL-TEXT SEARCH INDEXES
// ============================================================================

// Full-text search on all entity text
CREATE FULLTEXT INDEX entityTextIndex IF NOT EXISTS
FOR (e:Entity) ON EACH [e.text];

// Full-text search on visa types
CREATE FULLTEXT INDEX visaTypeIndex IF NOT EXISTS
FOR (v:visa_type) ON EACH [v.text];

// ============================================================================
// 4. RELATIONSHIP INDEXES (Optional, for large graphs)
// ============================================================================

// Index on REQUIRES relationship mandatory property
CREATE INDEX requires_mandatory IF NOT EXISTS
FOR ()-[r:REQUIRES]-() ON (r.mandatory);

// ============================================================================
// 5. SAMPLE DATA (for testing only - remove in production)
// ============================================================================

// Create sample visa type
CREATE (v:Entity:visa_type {
  id: 'visa_skilled_worker_001',
  text: 'Skilled Worker visa',
  category: 'work',
  chunk_ids: ['chunk_12345'],
  document_id: 'doc_immigration_guide_001',
  created_at: datetime()
});

// Create sample requirement
CREATE (r:Entity:requirement {
  id: 'req_financial_001',
  text: 'Demonstrate financial requirement (£1,270)',
  category: 'financial',
  mandatory: true,
  chunk_ids: ['chunk_12345'],
  document_id: 'doc_immigration_guide_001',
  created_at: datetime()
});

// Create sample document type
CREATE (d:Entity:document_type {
  id: 'doc_type_bank_statement_001',
  text: 'bank statement',
  chunk_ids: ['chunk_12346'],
  document_id: 'doc_immigration_guide_002',
  created_at: datetime()
});

// Create relationships
MATCH (v:visa_type {id: 'visa_skilled_worker_001'}),
      (r:requirement {id: 'req_financial_001'})
CREATE (v)-[:REQUIRES {mandatory: true, created_at: datetime()}]->(r);

MATCH (r:requirement {id: 'req_financial_001'}),
      (d:document_type {id: 'doc_type_bank_statement_001'})
CREATE (r)-[:SATISFIED_BY {created_at: datetime()}]->(d);

// ============================================================================
// 6. VERIFICATION QUERIES
// ============================================================================

// Count nodes by type
// MATCH (n)
// RETURN labels(n) AS label, count(n) AS count
// ORDER BY count DESC;

// Count relationships by type
// MATCH ()-[r]->()
// RETURN type(r) AS type, count(r) AS count
// ORDER BY count DESC;

// Sample graph traversal
// MATCH (v:visa_type {text: 'Skilled Worker visa'})
// MATCH (v)-[:REQUIRES]->(r:requirement)
// MATCH (r)-[:SATISFIED_BY]->(d:document_type)
// RETURN v.text, r.text, r.mandatory, d.text
// LIMIT 10;

// ============================================================================
// 7. CLEANUP (for testing only)
// ============================================================================

// Remove sample data
// MATCH (n)
// WHERE n.id IN [
//   'visa_skilled_worker_001',
//   'req_financial_001',
//   'doc_type_bank_statement_001'
// ]
// DETACH DELETE n;

// DANGER: Remove ALL data (use with extreme caution!)
// MATCH (n) DETACH DELETE n;
