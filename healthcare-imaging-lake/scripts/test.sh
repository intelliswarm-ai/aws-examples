#!/bin/bash
################################################################################
# Test Script for Healthcare Imaging Data Lake
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Run unit tests
unit_tests() {
    log_info "Running unit tests..."

    cd "${PROJECT_ROOT}"

    python -m pytest tests/unit/ \
        -v \
        --cov=src \
        --cov-report=term-missing \
        --cov-report=html:coverage_report \
        --cov-fail-under=80

    log_info "Unit tests completed"
}

# Run integration tests
integration_tests() {
    log_info "Running integration tests..."

    cd "${PROJECT_ROOT}"

    python -m pytest tests/integration/ \
        -v \
        --tb=short

    log_info "Integration tests completed"
}

# Run all tests
all_tests() {
    log_info "Running all tests..."

    cd "${PROJECT_ROOT}"

    python -m pytest tests/ \
        -v \
        --cov=src \
        --cov-report=term-missing \
        --cov-report=html:coverage_report

    log_info "All tests completed"
}

# Run linting
lint() {
    log_info "Running linting..."

    cd "${PROJECT_ROOT}"

    if command -v ruff &> /dev/null; then
        ruff check src/ tests/
        ruff format --check src/ tests/
    else
        log_warn "ruff not installed, skipping linting"
    fi

    log_info "Linting completed"
}

# Run type checking
typecheck() {
    log_info "Running type checking..."

    cd "${PROJECT_ROOT}"

    if command -v mypy &> /dev/null; then
        mypy src/ --ignore-missing-imports
    else
        log_warn "mypy not installed, skipping type checking"
    fi

    log_info "Type checking completed"
}

# Run security scan
security_scan() {
    log_info "Running security scan..."

    cd "${PROJECT_ROOT}"

    if command -v bandit &> /dev/null; then
        bandit -r src/ -ll
    else
        log_warn "bandit not installed, skipping security scan"
    fi

    log_info "Security scan completed"
}

# Main function
main() {
    log_info "Starting test suite for healthcare-imaging-lake"

    case "${1:-all}" in
        unit)
            unit_tests
            ;;
        integration)
            integration_tests
            ;;
        lint)
            lint
            ;;
        typecheck)
            typecheck
            ;;
        security)
            security_scan
            ;;
        all)
            lint
            typecheck
            security_scan
            unit_tests
            ;;
        ci)
            lint
            typecheck
            unit_tests
            ;;
        *)
            echo "Usage: $0 {unit|integration|lint|typecheck|security|all|ci}"
            exit 1
            ;;
    esac

    log_info "Test suite completed!"
}

main "$@"
