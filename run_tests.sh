#!/bin/bash
# Comprehensive test runner for Memory Scope API

set -e

echo "=========================================="
echo "Memory Scope API - Test Suite Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default options
VERBOSE=""
COVERAGE=""
PARALLEL=""
SPECIFIC_TEST=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -c|--coverage)
            COVERAGE="--cov=app --cov-report=html --cov-report=term"
            shift
            ;;
        -p|--parallel)
            PARALLEL="-n auto"
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose      Run tests with verbose output"
            echo "  -c, --coverage     Generate coverage report"
            echo "  -p, --parallel     Run tests in parallel"
            echo "  -t, --test PATH    Run specific test file or test"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Run all tests"
            echo "  $0 -v                       # Run all tests with verbose output"
            echo "  $0 -c                       # Run tests with coverage"
            echo "  $0 -p                       # Run tests in parallel"
            echo "  $0 -t tests/test_memory_create.py  # Run specific test file"
            echo "  $0 -t tests/test_memory_create.py::TestMemoryCreate::test_create_memory_basic  # Run specific test"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Check if pytest is available (try both direct command and python module)
if ! command -v pytest &> /dev/null && ! python3 -m pytest --version &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install it with: pip install pytest pytest-cov pytest-xdist"
    exit 1
fi

# Use python3 -m pytest if pytest command not found, otherwise use pytest directly
if command -v pytest &> /dev/null; then
    PYTEST_CMD="pytest"
else
    PYTEST_CMD="python3 -m pytest"
fi

# Build test command
TEST_CMD="$PYTEST_CMD tests/"

if [ -n "$SPECIFIC_TEST" ]; then
    TEST_CMD="$PYTEST_CMD $SPECIFIC_TEST"
fi

if [ -n "$VERBOSE" ]; then
    TEST_CMD="$TEST_CMD $VERBOSE"
fi

if [ -n "$COVERAGE" ]; then
    TEST_CMD="$TEST_CMD $COVERAGE"
fi

if [ -n "$PARALLEL" ]; then
    # Check if pytest-xdist is installed
    if ! python3 -c "import xdist" 2>/dev/null; then
        echo -e "${YELLOW}Warning: pytest-xdist not installed, skipping parallel execution${NC}"
    else
        TEST_CMD="$TEST_CMD $PARALLEL"
    fi
fi

echo "Running: $TEST_CMD"
echo ""

# Run tests
if eval $TEST_CMD; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "All tests passed! ✓"
    echo "==========================================${NC}"
    
    if [ -n "$COVERAGE" ]; then
        echo ""
        echo "Coverage report generated in htmlcov/index.html"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}=========================================="
    echo "Some tests failed! ✗"
    echo "==========================================${NC}"
    exit 1
fi

