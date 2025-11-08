// Neo4J Graph Schema for LinkedIn Lead Engine - AI Research Agent
// Created: November 7, 2025
// Purpose: Store company/person relationships, competitors, tech stack, and interactions

// ============================================================================
// 1. CONSTRAINTS - Unique identifiers and validation
// ============================================================================

// Company nodes - unique by LinkedIn company ID
CREATE CONSTRAINT company_id_unique IF NOT EXISTS
FOR (c:Company)
REQUIRE c.company_id IS UNIQUE;

// Person nodes - unique by LinkedIn profile ID
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.person_id IS UNIQUE;

// Competitor nodes - unique by name
CREATE CONSTRAINT competitor_name_unique IF NOT EXISTS
FOR (c:Competitor)
REQUIRE c.name IS UNIQUE;

// Technology nodes - unique by name
CREATE CONSTRAINT technology_name_unique IF NOT EXISTS
FOR (t:Technology)
REQUIRE t.name IS UNIQUE;

// Post nodes - unique by post ID
CREATE CONSTRAINT post_id_unique IF NOT EXISTS
FOR (p:Post)
REQUIRE p.post_id IS UNIQUE;

// ============================================================================
// 2. INDEXES - Performance optimization for common queries
// ============================================================================

// Company indexes
CREATE INDEX company_name_index IF NOT EXISTS
FOR (c:Company) ON (c.name);

CREATE INDEX company_industry_index IF NOT EXISTS
FOR (c:Company) ON (c.industry);

CREATE INDEX company_size_index IF NOT EXISTS
FOR (c:Company) ON (c.size_range);

// Person indexes
CREATE INDEX person_name_index IF NOT EXISTS
FOR (p:Person) ON (p.full_name);

CREATE INDEX person_current_role_index IF NOT EXISTS
FOR (p:Person) ON (p.current_role);

// Post indexes
CREATE INDEX post_published_date_index IF NOT EXISTS
FOR (p:Post) ON (p.published_at);

CREATE INDEX post_author_index IF NOT EXISTS
FOR (p:Post) ON (p.author_id);

// ============================================================================
// 3. NODE LABELS & PROPERTIES
// ============================================================================

// Company Node
// Properties:
//   - company_id: LinkedIn company ID (unique)
//   - name: Company name
//   - industry: Industry classification
//   - size_range: Employee size range (1-10, 11-50, etc.)
//   - headquarters: Location
//   - website: Company website URL
//   - description: Company description
//   - founded_year: Year founded
//   - created_at: Timestamp when created
//   - updated_at: Timestamp when last updated

// Person Node
// Properties:
//   - person_id: LinkedIn profile ID (unique)
//   - full_name: Full name
//   - first_name: First name
//   - last_name: Last name
//   - headline: LinkedIn headline
//   - current_role: Current job title
//   - location: Current location
//   - summary: Profile summary/about section
//   - profile_url: LinkedIn profile URL
//   - created_at: Timestamp when created
//   - updated_at: Timestamp when last updated

// Competitor Node
// Properties:
//   - name: Competitor name (unique)
//   - website: Competitor website
//   - market_position: 'direct', 'indirect', 'potential'
//   - competitive_advantage: Key advantages
//   - weaknesses: Known weaknesses
//   - created_at: Timestamp when created

// Technology Node
// Properties:
//   - name: Technology name (unique)
//   - category: Category (language, framework, database, cloud, etc.)
//   - version: Version if applicable
//   - created_at: Timestamp when created

// Post Node
// Properties:
//   - post_id: LinkedIn post ID (unique)
//   - author_id: LinkedIn profile ID of author
//   - content: Post content/text
//   - published_at: Publication timestamp
//   - likes_count: Number of likes
//   - comments_count: Number of comments
//   - shares_count: Number of shares
//   - post_url: LinkedIn post URL
//   - created_at: Timestamp when created in our system

// ============================================================================
// 4. RELATIONSHIP TYPES
// ============================================================================

// WORKS_FOR: Person → Company
// Properties:
//   - role: Job title
//   - start_date: Employment start date
//   - end_date: Employment end date (null if current)
//   - is_current: Boolean (true if current position)

// COMPETES_WITH: Company → Competitor
// Properties:
//   - analysis_date: When competitive analysis was performed
//   - market_overlap: % market overlap (0-100)
//   - threat_level: 'low', 'medium', 'high'

// USES_TECH: Company → Technology
// Properties:
//   - adoption_date: When technology was adopted (if known)
//   - confidence_score: Confidence level (0.0-1.0)
//   - source: Source of information

// POSTED: Person → Post
// Properties:
//   - is_repost: Boolean (true if reposted from someone else)

// ENGAGED_WITH: Person → Post
// Properties:
//   - engagement_type: 'like', 'comment', 'share'
//   - engagement_date: When engagement occurred
//   - comment_text: If engagement_type='comment', the actual comment

// ============================================================================
// 5. SAMPLE DATA (for testing)
// ============================================================================

// Create sample company
CREATE (c:Company {
  company_id: 'linkedin-12345',
  name: 'Acme Corporation',
  industry: 'Technology',
  size_range: '51-200',
  headquarters: 'San Francisco, CA',
  website: 'https://www.acme.com',
  description: 'Leading provider of innovative solutions',
  founded_year: 2010,
  created_at: datetime(),
  updated_at: datetime()
});

// Create sample person
CREATE (p:Person {
  person_id: 'linkedin-67890',
  full_name: 'John Doe',
  first_name: 'John',
  last_name: 'Doe',
  headline: 'VP of Engineering at Acme Corporation',
  current_role: 'VP of Engineering',
  location: 'San Francisco Bay Area',
  summary: 'Experienced engineering leader with 15+ years in tech',
  profile_url: 'https://www.linkedin.com/in/johndoe',
  created_at: datetime(),
  updated_at: datetime()
});

// Create sample competitor
CREATE (comp:Competitor {
  name: 'Beta Industries',
  website: 'https://www.betaindustries.com',
  market_position: 'direct',
  competitive_advantage: 'Lower pricing, faster delivery',
  weaknesses: 'Limited feature set, smaller team',
  created_at: datetime()
});

// Create sample technologies
CREATE (t1:Technology {
  name: 'React',
  category: 'frontend_framework',
  version: '18.2.0',
  created_at: datetime()
});

CREATE (t2:Technology {
  name: 'PostgreSQL',
  category: 'database',
  version: '14',
  created_at: datetime()
});

// Create sample post
CREATE (post:Post {
  post_id: 'linkedin-post-123',
  author_id: 'linkedin-67890',
  content: 'Excited to announce our new product launch!',
  published_at: datetime(),
  likes_count: 45,
  comments_count: 12,
  shares_count: 8,
  post_url: 'https://www.linkedin.com/feed/update/urn:li:activity:123',
  created_at: datetime()
});

// Create relationships
MATCH (p:Person {person_id: 'linkedin-67890'}), (c:Company {company_id: 'linkedin-12345'})
CREATE (p)-[:WORKS_FOR {
  role: 'VP of Engineering',
  start_date: date('2020-01-15'),
  end_date: null,
  is_current: true
}]->(c);

MATCH (c:Company {company_id: 'linkedin-12345'}), (comp:Competitor {name: 'Beta Industries'})
CREATE (c)-[:COMPETES_WITH {
  analysis_date: date(),
  market_overlap: 75.0,
  threat_level: 'high'
}]->(comp);

MATCH (c:Company {company_id: 'linkedin-12345'}), (t:Technology)
CREATE (c)-[:USES_TECH {
  adoption_date: date('2021-06-01'),
  confidence_score: 0.95,
  source: 'job_postings'
}]->(t);

MATCH (p:Person {person_id: 'linkedin-67890'}), (post:Post {post_id: 'linkedin-post-123'})
CREATE (p)-[:POSTED {
  is_repost: false
}]->(post);

// ============================================================================
// 6. COMMON QUERIES (for reference)
// ============================================================================

// Get all people working at a company
// MATCH (p:Person)-[r:WORKS_FOR]->(c:Company {company_id: $company_id})
// WHERE r.is_current = true
// RETURN p.full_name, p.current_role, r.start_date;

// Get all competitors for a company
// MATCH (c:Company {company_id: $company_id})-[r:COMPETES_WITH]->(comp:Competitor)
// RETURN comp.name, r.threat_level, r.market_overlap
// ORDER BY r.market_overlap DESC;

// Get tech stack for a company
// MATCH (c:Company {company_id: $company_id})-[r:USES_TECH]->(t:Technology)
// RETURN t.name, t.category, r.confidence_score
// ORDER BY t.category, t.name;

// Get recent posts by a person (last 6 months)
// MATCH (p:Person {person_id: $person_id})-[:POSTED]->(post:Post)
// WHERE post.published_at >= datetime() - duration('P6M')
// RETURN post.content, post.published_at, post.likes_count
// ORDER BY post.published_at DESC;

// Find common connections between two companies
// MATCH (p:Person)-[:WORKS_FOR]->(c1:Company {company_id: $company_id_1})
// MATCH (p)-[:WORKS_FOR]->(c2:Company {company_id: $company_id_2})
// RETURN p.full_name, p.current_role;

// ============================================================================
// 7. CLEANUP (for testing - removes sample data)
// ============================================================================

// To remove all sample data:
// MATCH (n) WHERE n.person_id = 'linkedin-67890' OR n.company_id = 'linkedin-12345'
// OR n.name IN ['Beta Industries', 'React', 'PostgreSQL'] OR n.post_id = 'linkedin-post-123'
// DETACH DELETE n;

// To remove ALL data (use with caution!):
// MATCH (n) DETACH DELETE n;
