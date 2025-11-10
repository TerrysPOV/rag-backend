#!/bin/bash
# Quick test runner for Neo4J Graph Traversals tests
# Usage: ./tests/RUN_GRAPH_TESTS.sh [test_type] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Neo4J Graph Traversals - Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Default values
TEST_TYPE=${1:-"all"}
VERBOSE=${2:-"-v"}

# Function to run tests with coverage
run_with_coverage() {
    local test_path=$1
    local coverage_source=$2
    local test_name=$3

    echo -e "${YELLOW}Running ${test_name}...${NC}"

    pytest "$test_path" \
        --cov="$coverage_source" \
        --cov-report=html \
        --cov-report=term-missing \
        "$VERBOSE" \
        --tb=short

    echo -e "${GREEN}✓ ${test_name} complete${NC}"
    echo ""
}

# Function to run tests without coverage
run_without_coverage() {
    local test_path=$1
    local test_name=$2

    echo -e "${YELLOW}Running ${test_name}...${NC}"

    pytest "$test_path" "$VERBOSE" --tb=short

    echo -e "${GREEN}✓ ${test_name} complete${NC}"
    echo ""
}

# Main test execution
case $TEST_TYPE in
    "contract")
        echo -e "${BLUE}Running Contract Tests Only${NC}"
        echo ""
        run_with_coverage \
            "tests/contract/test_graph_api_contract.py" \
            "src.api.routes.graph" \
            "Graph API Contract Tests"
        ;;

    "integration-service")
        echo -e "${BLUE}Running Integration Tests (Neo4J Service)${NC}"
        echo ""
        run_with_coverage \
            "tests/integration/test_neo4j_integration.py" \
            "src.services.neo4j_graph_service" \
            "Neo4J Service Integration Tests"
        ;;

    "integration-queries")
        echo -e "${BLUE}Running Integration Tests (Graph Queries)${NC}"
        echo ""
        run_with_coverage \
            "tests/integration/test_graph_queries.py" \
            "src.services.neo4j_graph_retriever" \
            "Graph Query Integration Tests"
        ;;

    "integration")
        echo -e "${BLUE}Running All Integration Tests${NC}"
        echo ""
        run_with_coverage \
            "tests/integration/test_neo4j_integration.py tests/integration/test_graph_queries.py" \
            "src.services.neo4j_graph_service,src.services.neo4j_graph_retriever" \
            "All Integration Tests"
        ;;

    "e2e")
        echo -e "${BLUE}Running E2E Tests (Currently Skipped)${NC}"
        echo ""
        echo -e "${YELLOW}Note: E2E tests are placeholders and currently skipped.${NC}"
        echo -e "${YELLOW}They will be enabled when frontend is implemented.${NC}"
        echo ""
        run_without_coverage \
            "tests/e2e/test_graph_workflows.py" \
            "E2E Workflow Tests"
        ;;

    "fast")
        echo -e "${BLUE}Running Fast Tests (Excluding Slow Tests)${NC}"
        echo ""
        pytest tests/contract/test_graph_api_contract.py \
               tests/integration/test_neo4j_integration.py \
               tests/integration/test_graph_queries.py \
               -m "graph and not slow" \
               "$VERBOSE" \
               --tb=short
        echo -e "${GREEN}✓ Fast tests complete${NC}"
        ;;

    "slow")
        echo -e "${BLUE}Running Slow Tests Only${NC}"
        echo ""
        pytest tests/contract/test_graph_api_contract.py \
               tests/integration/test_neo4j_integration.py \
               tests/integration/test_graph_queries.py \
               -m "graph and slow" \
               "$VERBOSE" \
               --tb=short
        echo -e "${GREEN}✓ Slow tests complete${NC}"
        ;;

    "coverage")
        echo -e "${BLUE}Running All Tests with Full Coverage Report${NC}"
        echo ""

        pytest tests/contract/test_graph_api_contract.py \
               tests/integration/test_neo4j_integration.py \
               tests/integration/test_graph_queries.py \
               --cov=src.api.routes.graph \
               --cov=src.services.neo4j_graph_service \
               --cov=src.services.neo4j_graph_retriever \
               --cov-report=html \
               --cov-report=term-missing \
               --cov-report=json \
               "$VERBOSE" \
               --tb=short

        echo ""
        echo -e "${GREEN}✓ All tests complete with coverage${NC}"
        echo -e "${BLUE}Coverage report: file://$(pwd)/htmlcov/index.html${NC}"
        ;;

    "all")
        echo -e "${BLUE}Running All Graph Tests${NC}"
        echo ""

        echo -e "${YELLOW}1/3 - Contract Tests${NC}"
        run_with_coverage \
            "tests/contract/test_graph_api_contract.py" \
            "src.api.routes.graph" \
            "Graph API Contract Tests"

        echo -e "${YELLOW}2/3 - Integration Tests (Service)${NC}"
        run_with_coverage \
            "tests/integration/test_neo4j_integration.py" \
            "src.services.neo4j_graph_service" \
            "Neo4J Service Integration Tests"

        echo -e "${YELLOW}3/3 - Integration Tests (Queries)${NC}"
        run_with_coverage \
            "tests/integration/test_graph_queries.py" \
            "src.services.neo4j_graph_retriever" \
            "Graph Query Integration Tests"

        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✓ All tests complete!${NC}"
        echo -e "${GREEN}========================================${NC}"
        ;;

    "help"|"--help"|"-h")
        echo "Usage: ./tests/RUN_GRAPH_TESTS.sh [test_type] [options]"
        echo ""
        echo "Test Types:"
        echo "  all                 - Run all graph tests (default)"
        echo "  contract            - Run contract tests only"
        echo "  integration         - Run all integration tests"
        echo "  integration-service - Run Neo4J service integration tests"
        echo "  integration-queries - Run graph query integration tests"
        echo "  e2e                 - Run E2E tests (currently skipped)"
        echo "  fast                - Run fast tests (exclude slow tests)"
        echo "  slow                - Run slow tests only"
        echo "  coverage            - Run all tests with full coverage report"
        echo "  help                - Show this help message"
        echo ""
        echo "Options:"
        echo "  -v      - Verbose output (default)"
        echo "  -q      - Quiet output"
        echo "  -vv     - Very verbose output"
        echo ""
        echo "Examples:"
        echo "  ./tests/RUN_GRAPH_TESTS.sh                    # Run all tests"
        echo "  ./tests/RUN_GRAPH_TESTS.sh contract           # Contract tests only"
        echo "  ./tests/RUN_GRAPH_TESTS.sh fast -q            # Fast tests, quiet mode"
        echo "  ./tests/RUN_GRAPH_TESTS.sh coverage           # Full coverage report"
        echo ""
        ;;

    *)
        echo -e "${RED}Error: Unknown test type '$TEST_TYPE'${NC}"
        echo ""
        echo "Run './tests/RUN_GRAPH_TESTS.sh help' for usage information"
        exit 1
        ;;
esac

# Exit with success
exit 0
