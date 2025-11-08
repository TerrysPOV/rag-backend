# Week 1 Development Plan - AI Sales Research Agent
## Sprint 1, Phase 2.1

**Duration**: 8 hours
**Status**: In Progress
**Started**: November 7, 2025

---

## Objectives

1. ✅ Set up Neo4J database (AuraDB free tier or Docker)
2. ✅ Create graph schema for company/individual relationships
3. ✅ Test Neo4J connection from research-backend
4. ✅ Adapt research-backend for LinkedIn Lead Engine
5. ✅ Configure Supabase integration (replace PostgreSQL)
6. ✅ Test existing Qdrant + Haystack + OpenRouter integration
7. ✅ Verify DigitalOcean Spaces connection
8. ✅ Create LinkedIn-specific Qdrant collections

---

## Task Breakdown

### US-001A-NEW: Neo4J Setup (4 hours)

**Agent**: backend-api-developer-python-t2

**Tasks**:
1. **Neo4J Installation** (1 hour)
   - Option A: Neo4J AuraDB free tier (cloud)
     - Sign up at https://neo4j.com/cloud/platform/aura-graph-database/
     - Create free instance (50K nodes, 175K relationships)
     - Get connection URI, username, password

   - Option B: Docker container (local development)
     - Add Neo4J service to docker-compose.yml
     - Configure with APOC plugin
     - Set up persistent volumes
     - Start container and verify

2. **Graph Schema Design** (2 hours)
   - Define node types:
     * `Company` - LinkedIn companies
     * `Person` - LinkedIn profiles
     * `Competitor` - Competitor companies
     * `Technology` - Tech stack items
     * `Post` - LinkedIn posts

   - Define relationship types:
     * `WORKS_FOR` - Person → Company
     * `COMPETES_WITH` - Company → Competitor
     * `USES_TECH` - Company → Technology
     * `POSTED` - Person → Post
     * `ENGAGED_WITH` - Person → Post

   - Create schema constraints and indexes
   - Document schema in Cypher queries

3. **Connection Testing** (1 hour)
   - Install neo4j Python driver
   - Create connection utility in research-backend
   - Test CRUD operations
   - Verify indexes working
   - Add Neo4J credentials to .env

**Deliverables**:
- [ ] Neo4J instance running (cloud or Docker)
- [ ] Graph schema created with constraints
- [ ] Python connection utility working
- [ ] Credentials in .env file
- [ ] Basic test queries passing

---

### US-002A: Backend Adaptation (4 hours)

**Agent**: database-developer-python-t2

**Tasks**:
1. **Review Research-Backend Structure** (0.5 hours)
   - Examine src/ directory structure
   - Review main.py FastAPI setup
   - Understand Qdrant + Haystack integration
   - Review OpenRouter API client
   - Check DigitalOcean Spaces integration

2. **Adapt for LinkedIn Use Case** (1.5 hours)
   - Create LinkedIn-specific models in src/api/models/
   - Adapt RAG components for LinkedIn data
   - Create LinkedIn document processors
   - Update Haystack pipelines for company/person research

3. **Supabase Integration** (1 hour)
   - Replace PostgreSQL connection with Supabase
   - Update database configuration
   - Test Supabase connection
   - Migrate relevant tables if needed

4. **Integration Testing** (1 hour)
   - Test Qdrant connection and collections
   - Test Haystack pipeline with OpenRouter
   - Test DeepInfra embeddings API
   - Test DigitalOcean Spaces upload/download
   - Create LinkedIn-specific Qdrant collections:
     * `linkedin_company_research`
     * `linkedin_person_profiles`

**Deliverables**:
- [ ] Research-backend adapted for LinkedIn
- [ ] Supabase connection working
- [ ] All existing integrations tested
- [ ] LinkedIn Qdrant collections created
- [ ] Documentation of changes

---

## Environment Variables Required

Add to `.env`:

```bash
# Neo4J Configuration
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io  # Or bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j

# Existing (from uk-immigration-rag-backend)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=<if-using-cloud>
DEEPINFRA_API_KEY=<your-key>
OPENROUTER_API_KEY=<your-key>
COHERE_API_KEY=<your-key>
DO_SPACES_ENDPOINT=https://lon1.digitaloceanspaces.com
DO_SPACES_BUCKET=li-lead-engine
DO_SPACES_ACCESS_KEY=<your-key>
DO_SPACES_SECRET_KEY=<your-key>

# Supabase (replacing PostgreSQL)
SUPABASE_URL=https://demo-project.supabase.co
SUPABASE_ANON_KEY=<your-key>
SUPABASE_SERVICE_ROLE_KEY=<your-key>
DATABASE_URL=<supabase-postgres-url>
```

---

## Success Criteria

### Neo4J Setup
- ✅ Neo4J instance accessible
- ✅ Graph schema created and documented
- ✅ Python driver can connect and query
- ✅ Constraints and indexes working
- ✅ Credentials securely stored in .env

### Backend Adaptation
- ✅ Research-backend running with LinkedIn config
- ✅ Supabase connection successful
- ✅ Qdrant collections created (linkedin_company_research, linkedin_person_profiles)
- ✅ Haystack pipeline tested with OpenRouter
- ✅ DigitalOcean Spaces upload/download working
- ✅ All tests passing

---

## Testing Checklist

### Neo4J Tests
- [ ] Create company node
- [ ] Create person node
- [ ] Create WORKS_FOR relationship
- [ ] Query by company_id (index performance)
- [ ] Query by person_id (index performance)
- [ ] Delete and verify cascade

### Backend Integration Tests
- [ ] Qdrant: Create collection, insert vector, search
- [ ] Haystack: Execute research pipeline end-to-end
- [ ] OpenRouter: Test GPT-4 API call
- [ ] DeepInfra: Generate embeddings
- [ ] Supabase: CRUD operations on test table
- [ ] DO Spaces: Upload file, retrieve file, delete file

---

## Dependencies

**External Services**:
- Neo4J AuraDB account OR Docker runtime
- Qdrant (existing from research-backend)
- Supabase account (existing)
- OpenRouter API key (existing in .env)
- DeepInfra API key (existing in .env)
- DigitalOcean Spaces (existing)

**Python Packages** (add to requirements.txt if missing):
```
neo4j>=5.14.0  # Neo4J Python driver
supabase>=2.0.0  # Supabase client (if not present)
```

---

## Risks & Mitigation

### Risk 1: Neo4J Free Tier Limits
- **Limit**: 50K nodes, 175K relationships
- **Mitigation**: Monitor usage, upgrade to paid tier if needed ($65/month)
- **Alternative**: Self-hosted Docker container

### Risk 2: Supabase Connection Issues
- **Mitigation**: Test connection early, verify credentials
- **Fallback**: Keep PostgreSQL as backup option

### Risk 3: Integration Breaking Changes
- **Mitigation**: Version pinning in requirements.txt
- **Mitigation**: Comprehensive integration tests before changing code

---

## Timeline

**Hours 1-4**: Neo4J Setup (Agent 1)
- Hour 1: Set up Neo4J instance
- Hours 2-3: Design and create graph schema
- Hour 4: Test connection and basic operations

**Hours 5-8**: Backend Adaptation (Agent 2)
- Hours 5-6: Review and adapt research-backend
- Hour 7: Supabase integration
- Hour 8: Integration testing and documentation

**Parallel Execution**: Both agents can work independently after initial setup

---

## Documentation Updates

### Files to Create/Update
1. `research-backend/NEO4J_SCHEMA.md` - Graph schema documentation
2. `research-backend/LINKEDIN_ADAPTATION.md` - Changes made for LinkedIn
3. `research-backend/INTEGRATION_TEST_RESULTS.md` - Test results
4. `research-backend/.env.example` - Update with Neo4J variables
5. `research-backend/requirements.txt` - Add neo4j driver

---

## Next Steps (Week 2)

After Week 1 completion:
1. Company research pipeline (US-007)
2. Individual/profile research pipeline (US-010)
3. Competitor analysis module (US-008)
4. Briefing note generation (US-014)

---

**Status**: Ready to begin
**Last Updated**: November 7, 2025
