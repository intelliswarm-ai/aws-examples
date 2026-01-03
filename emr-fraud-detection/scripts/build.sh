#!/bin/bash
set -euo pipefail

# EMR Fraud Detection Pipeline - Build Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/dist"

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

Build EMR Fraud Detection Pipeline artifacts

Options:
    -c, --clean         Clean build directories before building
    -l, --lambda        Build Lambda deployment package only
    -s, --spark         Build Spark jobs package only
    -a, --all           Build all artifacts (default)
    -h, --help          Show this help message

EOF
    exit 1
}

BUILD_LAMBDA=false
BUILD_SPARK=false
CLEAN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -l|--lambda)
            BUILD_LAMBDA=true
            shift
            ;;
        -s|--spark)
            BUILD_SPARK=true
            shift
            ;;
        -a|--all)
            BUILD_LAMBDA=true
            BUILD_SPARK=true
            shift
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

# Default to building all
if [[ "$BUILD_LAMBDA" == "false" && "$BUILD_SPARK" == "false" ]]; then
    BUILD_LAMBDA=true
    BUILD_SPARK=true
fi

# Clean build directories
clean_build() {
    log_info "Cleaning build directories..."
    rm -rf "${BUILD_DIR}"
    rm -rf "${DIST_DIR}"
    log_info "Build directories cleaned"
}

# Create directories
setup_directories() {
    mkdir -p "${BUILD_DIR}"
    mkdir -p "${DIST_DIR}"
    mkdir -p "${DIST_DIR}/lambda"
    mkdir -p "${DIST_DIR}/spark"
}

# Build Lambda package
build_lambda() {
    log_info "Building Lambda deployment package..."

    LAMBDA_BUILD="${BUILD_DIR}/lambda"
    rm -rf "${LAMBDA_BUILD}"
    mkdir -p "${LAMBDA_BUILD}"

    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install \
        --platform manylinux2014_x86_64 \
        --target "${LAMBDA_BUILD}" \
        --implementation cp \
        --python-version 3.11 \
        --only-binary=:all: \
        --upgrade \
        -r "${PROJECT_ROOT}/requirements.txt" \
        --quiet

    # Copy source code
    log_info "Copying source code..."
    cp -r "${PROJECT_ROOT}/src/"* "${LAMBDA_BUILD}/"

    # Remove unnecessary files
    find "${LAMBDA_BUILD}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${LAMBDA_BUILD}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find "${LAMBDA_BUILD}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "${LAMBDA_BUILD}" -name "*.pyc" -delete 2>/dev/null || true

    # Create zip
    log_info "Creating Lambda zip package..."
    cd "${LAMBDA_BUILD}"
    zip -r "${DIST_DIR}/lambda/fraud-detection.zip" . -q

    LAMBDA_SIZE=$(du -h "${DIST_DIR}/lambda/fraud-detection.zip" | cut -f1)
    log_info "Lambda package created: ${DIST_DIR}/lambda/fraud-detection.zip (${LAMBDA_SIZE})"
}

# Build Spark jobs package
build_spark() {
    log_info "Building Spark jobs package..."

    SPARK_BUILD="${BUILD_DIR}/spark"
    rm -rf "${SPARK_BUILD}"
    mkdir -p "${SPARK_BUILD}"

    # Copy Spark jobs
    cp -r "${PROJECT_ROOT}/spark/"* "${SPARK_BUILD}/"

    # Remove unnecessary files
    find "${SPARK_BUILD}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${SPARK_BUILD}" -name "*.pyc" -delete 2>/dev/null || true

    # Copy individual job files
    for job in feature_engineering model_training batch_scoring streaming_scoring; do
        cp "${PROJECT_ROOT}/spark/jobs/${job}.py" "${DIST_DIR}/spark/"
    done

    # Copy utilities as a zip for spark-submit --py-files
    cd "${SPARK_BUILD}"
    zip -r "${DIST_DIR}/spark/spark-utils.zip" utils/ -q

    log_info "Spark jobs package created: ${DIST_DIR}/spark/"
}

# Validate Python syntax
validate_python() {
    log_info "Validating Python syntax..."

    cd "${PROJECT_ROOT}"

    # Check src/
    python -m py_compile src/common/models.py
    python -m py_compile src/common/config.py
    python -m py_compile src/common/exceptions.py
    python -m py_compile src/handlers/ingestion_handler.py

    # Check spark/
    python -m py_compile spark/jobs/feature_engineering.py
    python -m py_compile spark/jobs/model_training.py

    log_info "Python syntax validation passed"
}

# Main
main() {
    log_info "Starting build process..."
    log_info "Project root: ${PROJECT_ROOT}"

    cd "${PROJECT_ROOT}"

    if [[ "$CLEAN" == "true" ]]; then
        clean_build
    fi

    setup_directories
    validate_python

    if [[ "$BUILD_LAMBDA" == "true" ]]; then
        build_lambda
    fi

    if [[ "$BUILD_SPARK" == "true" ]]; then
        build_spark
    fi

    log_info "Build completed successfully!"
    log_info "Artifacts available in: ${DIST_DIR}"
}

main
