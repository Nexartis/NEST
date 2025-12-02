#!/bin/bash
#
# Local Test Script for NEST on Windows (Git Bash / MINGW)
#
# Usage:
#   ./scripts/local_test_windows_bash.sh           # Run all tests
#   ./scripts/local_test_windows_bash.sh lint      # Run lint only
#   ./scripts/local_test_windows_bash.sh test      # Run tests only
#   ./scripts/local_test_windows_bash.sh all       # Run lint + tests
#
# This script mirrors the CI workflow for local validation before pushing.

set -e

# Colors for output (works in Git Bash)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  NEST Local Test Runner (Windows)   ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "Project root: ${PROJECT_ROOT}"
echo -e "Python version: $(python --version 2>&1)"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Function to run lint
run_lint() {
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}  Running Lint (flake8)                 ${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo ""

    # Check if flake8 is installed
    if ! python -m flake8 --version > /dev/null 2>&1; then
        echo -e "${RED}[ERROR] flake8 not installed${NC}"
        echo "Run: pip install flake8"
        return 1
    fi

    echo "Checking for critical errors (E9, F63, F7, F82)..."
    echo ""

    if python -m flake8 nanda_core/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        echo ""
        echo -e "${GREEN}[PASS] Lint check passed${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}[FAIL] Lint check failed${NC}"
        echo ""
        echo "POTENTIAL CAUSES:"
        echo "  - Syntax errors in Python files"
        echo "  - Undefined variable names"
        echo "  - Invalid comparisons"
        echo ""
        echo "SOLUTIONS:"
        echo "  - Check the file and line numbers above"
        echo "  - Fix the reported issues"
        return 1
    fi
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}  Running Tests (pytest)                ${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo ""

    # Check if pytest is installed
    if ! python -m pytest --version > /dev/null 2>&1; then
        echo -e "${RED}[ERROR] pytest not installed${NC}"
        echo "Run: pip install -e \".[dev]\""
        return 1
    fi

    # Check if tests directory exists
    if [ ! -d "tests" ]; then
        echo -e "${RED}[ERROR] tests/ directory not found${NC}"
        return 1
    fi

    echo "Running pytest with verbose output..."
    echo ""

    if python -m pytest tests/ -v -s --tb=long; then
        echo ""
        echo -e "${GREEN}[PASS] All tests passed${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}[FAIL] Some tests failed${NC}"
        echo ""
        echo "POTENTIAL CAUSES:"
        echo "  - Code changes broke existing functionality"
        echo "  - Missing dependencies"
        echo "  - API changes in agent_bridge.py"
        echo ""
        echo "SOLUTIONS:"
        echo "  - Check the test output above for details"
        echo "  - Each test includes diagnostic information"
        echo "  - Run single test: pytest tests/test_agent_bridge.py::TestName -v"
        return 1
    fi
}

# Function to check dependencies
check_deps() {
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}  Checking Dependencies                 ${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo ""

    local missing=0

    # Check Python
    if ! python --version > /dev/null 2>&1; then
        echo -e "${RED}[MISSING] Python not found${NC}"
        missing=1
    else
        echo -e "${GREEN}[OK] Python: $(python --version 2>&1)${NC}"
    fi

    # Check pip
    if ! python -m pip --version > /dev/null 2>&1; then
        echo -e "${RED}[MISSING] pip not found${NC}"
        missing=1
    else
        echo -e "${GREEN}[OK] pip: $(python -m pip --version 2>&1 | head -1)${NC}"
    fi

    # Check if package is installed
    if python -c "import nanda_core" 2>/dev/null; then
        echo -e "${GREEN}[OK] nanda_core package installed${NC}"
    else
        echo -e "${YELLOW}[WARN] nanda_core not installed - run: pip install -e \".[dev]\"${NC}"
    fi

    # Check pytest
    if python -m pytest --version > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] pytest installed${NC}"
    else
        echo -e "${YELLOW}[WARN] pytest not installed - run: pip install pytest${NC}"
    fi

    # Check flake8
    if python -m flake8 --version > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] flake8 installed${NC}"
    else
        echo -e "${YELLOW}[WARN] flake8 not installed - run: pip install flake8${NC}"
    fi

    echo ""
    return $missing
}

# Function to install dependencies
install_deps() {
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}  Installing Dependencies               ${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo ""

    echo "Installing NEST with dev dependencies..."
    python -m pip install -e ".[dev]"

    echo ""
    echo -e "${GREEN}[DONE] Dependencies installed${NC}"
}

# Main execution
case "${1:-all}" in
    lint)
        run_lint
        ;;
    test|tests)
        run_tests
        ;;
    deps|check)
        check_deps
        ;;
    install)
        install_deps
        ;;
    all|"")
        echo -e "${BLUE}Running full CI check (lint + tests)${NC}"
        echo ""

        LINT_PASSED=0
        TEST_PASSED=0

        if run_lint; then
            LINT_PASSED=1
        fi

        echo ""

        if run_tests; then
            TEST_PASSED=1
        fi

        echo ""
        echo -e "${BLUE}======================================${NC}"
        echo -e "${BLUE}  Summary                             ${NC}"
        echo -e "${BLUE}======================================${NC}"

        if [ $LINT_PASSED -eq 1 ]; then
            echo -e "  Lint:  ${GREEN}PASSED${NC}"
        else
            echo -e "  Lint:  ${RED}FAILED${NC}"
        fi

        if [ $TEST_PASSED -eq 1 ]; then
            echo -e "  Tests: ${GREEN}PASSED${NC}"
        else
            echo -e "  Tests: ${RED}FAILED${NC}"
        fi

        echo ""

        if [ $LINT_PASSED -eq 1 ] && [ $TEST_PASSED -eq 1 ]; then
            echo -e "${GREEN}All checks passed! Ready to commit.${NC}"
            exit 0
        else
            echo -e "${RED}Some checks failed. Please fix before committing.${NC}"
            exit 1
        fi
        ;;
    help|--help|-h)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  all      Run lint + tests (default)"
        echo "  lint     Run flake8 lint check only"
        echo "  test     Run pytest tests only"
        echo "  deps     Check if dependencies are installed"
        echo "  install  Install dev dependencies"
        echo "  help     Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0              # Run all checks"
        echo "  $0 lint         # Quick lint check"
        echo "  $0 test         # Run tests only"
        echo "  $0 install      # Install dependencies first"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
