# Neo4J Graph Traversals - Test Suite Documentation

**Feature**: NEO4J-001 - Graph Traversals for Immigration RAG
**Created**: 2025-01-10
**Test Coverage Target**: 85%

---

## Overview

Comprehensive test suite for Neo4J Graph Traversals feature covering:
- **Contract Tests**: API endpoint specifications
- **Integration Tests**: Neo4J service methods and graph queries
- **E2E Tests**: Full user workflows (placeholders for when frontend is ready)

---

## Test Files

### 1. Contract Tests
**File**: `tests/contract/test_graph_api_contract.py`
**Purpose**: Validate API endpoints against OpenAPI specification
**Test Count**: 45+ tests

#### Endpoints Tested
1. `POST /api/rag/graph/extract` - Trigger entity extraction (auth required)
2. `GET /api/rag/graph/stats` - Graph statistics (public)
3. `GET /api/rag/graph/health` - Health check (public)
4. `POST /api/rag/graph/query` - RAG query with graph (public with optional auth)
5. `GET /api/rag/graph/entity/{entity_id}` - Entity details (public)
6. `GET /api/rag/graph/visualize/{entity_id}` - Visualization data (public)
7. `POST /api/rag/graph/search` - Search entities (public with optional auth)

#### Coverage
- ✅ Request/response schema validation
- ✅ HTTP status codes (200, 202, 400, 401, 403, 404, 422, 500, 503)
- ✅ Error response formats
- ✅ Authentication enforcement
- ✅ Rate limiting behavior
- ✅ Parameter validation (boundary values)
- ✅ Performance benchmarks (<5s for queries, <1s for stats)

#### Running Contract Tests
```bash
# All contract tests
pytest tests/contract/test_graph_api_contract.py -m contract -v

# Specific endpoint
pytest tests/contract/test_graph_api_contract.py::test_graph_query_endpoint_exists -v

# With coverage
pytest tests/contract/test_graph_api_contract.py --cov=src.api.routes.graph --cov-report=html
```

---

### 2. Integration Tests - Neo4J Service
**File**: `tests/integration/test_neo4j_integration.py`
**Purpose**: Test Neo4J service methods with mock database
**Test Count**: 35+ tests

#### Components Tested
- `Neo4JGraphService` class
- Graph statistics calculation
- Health checks (orphaned nodes, broken references)
- Entity details retrieval
- Visualization data generation
- Entity search (with/without type filters)
- Schema initialization
- Singleton pattern
- Error handling and graceful degradation

#### Mock Strategy
Uses `unittest.mock` to mock Neo4J driver and session:
- No live Neo4J required
- Fast execution
- Predictable test data
- Isolated tests (no database side effects)

#### Running Integration Tests
```bash
# All Neo4J integration tests
pytest tests/integration/test_neo4j_integration.py -m integration -v

# Specific test category
pytest tests/integration/test_neo4j_integration.py -k "statistics" -v

# With coverage
pytest tests/integration/test_neo4j_integration.py --cov=src.services.neo4j_graph_service
```

---

### 3. Integration Tests - Graph Queries
**File**: `tests/integration/test_graph_queries.py`
**Purpose**: Test graph traversal logic and query strategies
**Test Count**: 40+ tests

#### Query Strategies Tested
1. **Direct Entity Search**
   - Single entity matching
   - Multiple entity matching
   - Case-insensitive search
   - No results handling

2. **Relationship Expansion**
   - REQUIRES relationships
   - SATISFIED_BY relationships
   - CAN_TRANSITION_TO relationships
   - DEPENDS_ON relationships
   - Multiple relationship types

3. **Multi-Hop Traversal**
   - Depth 1-5 traversal
   - Hop count penalties
   - Path tracking
   - Shortest paths first

4. **Hybrid Scoring**
   - Direct match score: 1.0
   - Relationship expansion score: 0.8
   - Multi-hop score: 0.6 / hop_count
   - Combined scoring

5. **Query Entity Extraction**
   - SpaCy NER (ORG, GPE, PERSON, DATE, MONEY)
   - Visa type patterns
   - Document type patterns
   - Case-insensitive deduplication

6. **Graph Path Explainability**
   - Traversal path generation
   - Relationship type tracking
   - Hop count reporting
   - Strategy attribution

#### Running Query Tests
```bash
# All graph query tests
pytest tests/integration/test_graph_queries.py -m integration -v

# Specific strategy
pytest tests/integration/test_graph_queries.py -k "direct_search" -v
pytest tests/integration/test_graph_queries.py -k "relationship_expansion" -v
pytest tests/integration/test_graph_queries.py -k "multihop" -v

# Performance tests
pytest tests/integration/test_graph_queries.py -m slow -v
```

---

### 4. E2E Tests - User Workflows
**File**: `tests/e2e/test_graph_workflows.py`
**Purpose**: End-to-end user journey tests
**Test Count**: 8 placeholder tests (currently skipped)

#### Critical User Journeys
1. **Search and View Graph**
   - User searches for "Skilled Worker visa requirements"
   - Graph visualization appears
   - Entities and relationships displayed
   - Interactive graph (pan, zoom, hover)

2. **Explore Entity Details**
   - Click entity to view details
   - Properties displayed
   - Relationships shown (incoming/outgoing)
   - Navigate to related entities

3. **Multi-Hop Navigation**
   - Follow relationship paths
   - Breadcrumb tracking
   - Path highlighting in graph
   - Navigate back via breadcrumb

4. **Admin Graph Extraction**
   - Login as admin
   - Select documents
   - Trigger extraction
   - Monitor progress
   - View updated statistics
   - Run health check

#### Status: **PLACEHOLDERS**
These tests are currently marked with `@pytest.mark.skip` because:
- Frontend is not yet implemented
- Selenium setup not configured
- Test data fixtures not created

#### Enabling E2E Tests (When Frontend is Ready)
See detailed instructions in `tests/e2e/test_graph_workflows.py`:
1. Remove `@pytest.mark.skip` decorators
2. Install Selenium and WebDriver
3. Setup test environment (frontend, backend, Neo4J)
4. Create test data fixtures
5. Configure CI/CD integration

---

## Test Data and Fixtures

### Contract Test Fixtures
- `valid_extraction_request`: Sample extraction payload
- `valid_query_request`: Sample graph query payload
- `valid_search_request`: Sample entity search payload

### Integration Test Fixtures
- `mock_neo4j_driver`: Mocked Neo4J driver
- `mock_neo4j_session`: Mocked Neo4J session
- `graph_service`: Neo4JGraphService instance with mocks
- `graph_retriever`: Neo4JGraphRetriever instance with mocks
- `sample_graph_stats`: Sample statistics data
- `sample_entity_data`: Sample entity with relationships
- `sample_direct_search_results`: Direct search mock results
- `sample_relationship_expansion_results`: Expansion mock results
- `sample_multihop_traversal_results`: Multi-hop mock results

### E2E Test Fixtures (Planned)
- `sample_search_query`: Test search query
- `expected_entities`: Expected entities in results
- `expected_relationships`: Expected graph relationships
- `admin_credentials`: Admin user credentials
- `test_document_ids`: Test documents for extraction
- `setup_test_graph_data`: Neo4J test data setup/teardown

---

## Running Tests

### Run All Graph Tests
```bash
pytest tests/ -m graph -v
```

### Run by Test Type
```bash
# Contract tests only
pytest tests/contract/test_graph_api_contract.py -v

# Integration tests only
pytest tests/integration/test_neo4j_integration.py tests/integration/test_graph_queries.py -v

# E2E tests (currently all skipped)
pytest tests/e2e/test_graph_workflows.py -v
```

### Run with Coverage
```bash
# Full coverage report
pytest tests/contract/test_graph_api_contract.py \
       tests/integration/test_neo4j_integration.py \
       tests/integration/test_graph_queries.py \
       --cov=src.api.routes.graph \
       --cov=src.services.neo4j_graph_service \
       --cov=src.services.neo4j_graph_retriever \
       --cov-report=html \
       --cov-report=term-missing

# Open HTML report
open htmlcov/index.html
```

### Run Slow Tests
```bash
# Skip slow tests
pytest tests/ -m "graph and not slow" -v

# Run only slow tests
pytest tests/ -m "graph and slow" -v
```

### Run Specific Test
```bash
# By test name
pytest tests/contract/test_graph_api_contract.py::test_graph_query_response_schema -v

# By test pattern
pytest tests/ -k "statistics" -v
pytest tests/ -k "multihop" -v
```

---

## CI/CD Integration

### GitHub Actions Workflow
```yaml
name: Graph Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run contract tests
        run: |
          pytest tests/contract/test_graph_api_contract.py \
                 --cov=src.api.routes.graph \
                 --cov-report=xml

      - name: Run integration tests
        run: |
          pytest tests/integration/test_neo4j_integration.py \
                 tests/integration/test_graph_queries.py \
                 --cov=src.services.neo4j_graph_service \
                 --cov=src.services.neo4j_graph_retriever \
                 --cov-report=xml \
                 --cov-append

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Test Coverage Goals

### Target Coverage: 85%

#### Current Coverage by Component
- `src/api/routes/graph.py`: **Target 90%**
  - All endpoints tested
  - All error paths tested
  - All authentication flows tested

- `src/services/neo4j_graph_service.py`: **Target 85%**
  - All public methods tested
  - Error handling tested
  - Edge cases covered

- `src/services/neo4j_graph_retriever.py`: **Target 85%**
  - All query strategies tested
  - Scoring algorithms tested
  - Entity extraction tested

### Coverage Gaps (To Address)
- [ ] SpaCy NER integration (currently mocked)
- [ ] Actual Neo4J query execution (using testcontainers)
- [ ] Rate limiting integration tests
- [ ] Caching behavior tests
- [ ] WebSocket real-time updates (if implemented)

---

## Test Maintenance

### Adding New Tests
1. Identify test category (contract, integration, e2e)
2. Create test in appropriate file
3. Use existing fixtures where possible
4. Follow naming convention: `test_<component>_<scenario>_<expected_outcome>`
5. Add docstring with clear description
6. Add appropriate pytest markers
7. Update coverage targets

### Updating Tests
1. Tests must be updated when:
   - API specification changes
   - Service methods change
   - Query logic changes
   - Error handling changes
2. Run full test suite before committing
3. Verify coverage doesn't decrease

### Test Data
- Keep test data minimal
- Use fixtures for reusable data
- Mock external dependencies (Neo4J, SpaCy)
- Document expected test data in docstrings

---

## Troubleshooting

### Common Issues

#### 1. Neo4J Connection Errors
**Symptom**: Tests fail with "Neo4J driver not initialized"
**Solution**: Check that mocks are properly configured. Integration tests should NOT require live Neo4J.

#### 2. Import Errors
**Symptom**: `ModuleNotFoundError: No module named 'src'`
**Solution**: Run pytest from project root: `pytest tests/`

#### 3. Fixture Not Found
**Symptom**: `fixture 'mock_neo4j_driver' not found`
**Solution**: Ensure fixture is defined in same file or in `conftest.py`

#### 4. Slow Tests
**Symptom**: Tests take too long to run
**Solution**: Use `-m "not slow"` to skip slow tests during development

#### 5. Coverage Not Reported
**Symptom**: No coverage report generated
**Solution**: Install `pytest-cov`: `pip install pytest-cov`

---

## Performance Benchmarks

### Target Performance Metrics

#### API Endpoints
- Graph query: **< 5 seconds**
- Graph stats: **< 1 second**
- Health check: **< 1 second**
- Entity details: **< 500ms**
- Visualization data: **< 2 seconds**
- Entity search: **< 1 second**

#### Graph Queries
- Direct search: **< 200ms**
- Relationship expansion: **< 500ms**
- Multi-hop (depth 3): **< 2 seconds**
- Entity extraction: **< 100ms**

### Monitoring Performance
```bash
# Run with timing report
pytest tests/ -m graph --durations=10

# Profile slow tests
pytest tests/ -m slow --profile
```

---

## Future Enhancements

### Planned Improvements
1. **Testcontainers Integration**
   - Use real Neo4J instance in Docker
   - More realistic integration tests
   - Test actual Cypher queries

2. **Property-Based Testing**
   - Use Hypothesis for query generation
   - Test edge cases automatically
   - Fuzzing entity extraction

3. **Load Testing**
   - Concurrent query performance
   - Large graph scalability
   - Memory usage under load

4. **E2E Tests Enablement**
   - Selenium setup
   - Test data fixtures
   - CI/CD integration
   - Screenshot comparison

5. **Mutation Testing**
   - Use `mutmut` to verify test quality
   - Ensure tests catch bugs
   - Improve test coverage

---

## References

- **API Specification**: `/docs/design/api/NEO4J-001-architecture-diagrams.md`
- **Graph Service**: `/backend-source/src/services/neo4j_graph_service.py`
- **Graph Retriever**: `/backend-source/src/services/neo4j_graph_retriever.py`
- **API Routes**: `/backend-source/src/api/routes/graph.py`
- **Pytest Documentation**: https://docs.pytest.org/
- **Neo4J Python Driver**: https://neo4j.com/docs/python-manual/

---

**Last Updated**: 2025-01-10
**Maintained By**: Test Writer Agent
**Status**: Complete (E2E tests pending frontend)
