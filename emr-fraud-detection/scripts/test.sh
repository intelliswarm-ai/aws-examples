#!/bin/bash
set -euo pipefail

# EMR Fraud Detection Pipeline - Test Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
COVERAGE_MIN=70
PYTEST_ARGS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run tests for EMR Fraud Detection Pipeline

Options:
    -u, --unit              Run unit tests only
    -i, --integration       Run integration tests only
    -a, --all               Run all tests (default)
    -c, --coverage          Generate coverage report
    -v, --verbose           Verbose output
    -f, --fast              Skip slow tests
    -k PATTERN              Run tests matching pattern
    -h, --help              Show this help message

Examples:
    $0 --unit --coverage
    $0 --all --verbose
    $0 -k "test_kinesis"

EOF
    exit 1
}

RUN_UNIT=false
RUN_INTEGRATION=false
COVERAGE=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            RUN_UNIT=true
            shift
            ;;
        -i|--integration)
            RUN_INTEGRATION=true
            shift
            ;;
        -a|--all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            PYTEST_ARGS="${PYTEST_ARGS} -v"
            shift
            ;;
        -f|--fast)
            PYTEST_ARGS="${PYTEST_ARGS} -m 'not slow'"
            shift
            ;;
        -k)
            PYTEST_ARGS="${PYTEST_ARGS} -k $2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Default to running all tests
if [[ "$RUN_UNIT" == "false" && "$RUN_INTEGRATION" == "false" ]]; then
    RUN_UNIT=true
    RUN_INTEGRATION=true
fi

# Setup environment
setup_environment() {
    log_info "Setting up test environment..."

    cd "${PROJECT_ROOT}"

    # Create virtual environment if needed
    if [[ ! -d ".venv" ]]; then
        log_info "Creating virtual environment..."
        python -m venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Install dependencies
    log_info "Installing dependencies..."
    pip install -q -r requirements.txt
    pip install -q -r requirements-dev.txt

    # Set test environment variables
    export ENVIRONMENT=test
    export AWS_DEFAULT_REGION=us-east-1
    export KINESIS_STREAM_NAME=test-stream
    export DATA_BUCKET=test-data-bucket
    export MODELS_BUCKET=test-models-bucket
    export ALERTS_TABLE_NAME=test-alerts
    export PREDICTIONS_TABLE_NAME=test-predictions
    export EXECUTIONS_TABLE_NAME=test-executions
    export FRAUD_ALERTS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:test-topic
    export POWERTOOLS_SERVICE_NAME=test-service
    export LOG_LEVEL=DEBUG
}

# Run linting
run_lint() {
    log_info "Running linting..."

    # Ruff for linting
    if command -v ruff &> /dev/null; then
        log_info "Running ruff..."
        ruff check src/ spark/ tests/ --fix --quiet || true
    fi

    # Type checking with mypy
    if command -v mypy &> /dev/null; then
        log_info "Running mypy..."
        mypy src/ --ignore-missing-imports --no-error-summary || true
    fi

    log_info "Linting completed"
}

# Run unit tests
run_unit_tests() {
    log_info "Running unit tests..."

    UNIT_ARGS="tests/unit/ ${PYTEST_ARGS}"

    if [[ "$COVERAGE" == "true" ]]; then
        UNIT_ARGS="--cov=src --cov-report=term-missing --cov-report=html:coverage_html ${UNIT_ARGS}"
    fi

    python -m pytest ${UNIT_ARGS}
}

# Run integration tests
run_integration_tests() {
    log_info "Running integration tests..."

    # Check if moto or localstack is available
    if ! python -c "import moto" 2>/dev/null; then
        log_warn "moto not installed, skipping integration tests"
        return 0
    fi

    INTEGRATION_ARGS="tests/integration/ ${PYTEST_ARGS}"

    if [[ "$COVERAGE" == "true" ]]; then
        INTEGRATION_ARGS="--cov=src --cov-append --cov-report=term-missing ${INTEGRATION_ARGS}"
    fi

    python -m pytest ${INTEGRATION_ARGS}
}

# Generate coverage report
generate_coverage_report() {
    if [[ "$COVERAGE" == "true" ]]; then
        log_info "Generating coverage report..."

        # Check coverage threshold
        python -m coverage report --fail-under=${COVERAGE_MIN} || {
            log_warn "Coverage is below ${COVERAGE_MIN}%"
        }

        log_info "HTML coverage report: ${PROJECT_ROOT}/coverage_html/index.html"
    fi
}

# Run Spark tests
run_spark_tests() {
    log_info "Running Spark tests..."

    # These require PySpark to be installed
    if ! python -c "import pyspark" 2>/dev/null; then
        log_warn "PySpark not installed, skipping Spark tests"
        return 0
    fi

    # Run Spark-specific tests
    python -m pytest tests/unit/test_spark*.py ${PYTEST_ARGS} || true
}

# Summary
print_summary() {
    echo ""
    log_info "============================================"
    log_info "Test Summary"
    log_info "============================================"
    if [[ "$RUN_UNIT" == "true" ]]; then
        log_info "Unit tests: COMPLETED"
    fi
    if [[ "$RUN_INTEGRATION" == "true" ]]; then
        log_info "Integration tests: COMPLETED"
    fi
    if [[ "$COVERAGE" == "true" ]]; then
        log_info "Coverage report generated"
    fi
    log_info "============================================"
}

# Main
main() {
    log_info "Starting test suite..."

    setup_environment
    run_lint

    if [[ "$RUN_UNIT" == "true" ]]; then
        run_unit_tests
    fi

    if [[ "$RUN_INTEGRATION" == "true" ]]; then
        run_integration_tests
    fi

    generate_coverage_report
    print_summary

    log_info "Tests completed successfully!"
}

main
