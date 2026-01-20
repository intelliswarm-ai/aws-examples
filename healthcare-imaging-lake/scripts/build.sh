#!/bin/bash
################################################################################
# Build Script for Healthcare Imaging Data Lake
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

# Build Lambda package
build_lambda() {
    log_info "Building Lambda deployment package..."

    BUILD_DIR="${PROJECT_ROOT}/.build"
    PACKAGE_DIR="${BUILD_DIR}/package"
    OUTPUT_FILE="${BUILD_DIR}/lambda.zip"

    # Clean previous build
    rm -rf "${BUILD_DIR}"
    mkdir -p "${PACKAGE_DIR}"

    # Install dependencies
    log_info "Installing dependencies..."
    pip install -r "${PROJECT_ROOT}/requirements.txt" -t "${PACKAGE_DIR}" --quiet --upgrade

    # Copy source code
    log_info "Copying source code..."
    cp -r "${PROJECT_ROOT}/src" "${PACKAGE_DIR}/"

    # Create zip file
    log_info "Creating zip archive..."
    cd "${PACKAGE_DIR}"
    zip -r "${OUTPUT_FILE}" . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*" > /dev/null

    log_info "Lambda package created: ${OUTPUT_FILE}"
    log_info "Package size: $(du -h "${OUTPUT_FILE}" | cut -f1)"
}

# Build Glue ETL package
build_glue() {
    log_info "Building Glue ETL package..."

    GLUE_BUILD_DIR="${PROJECT_ROOT}/.build/glue"
    mkdir -p "${GLUE_BUILD_DIR}"

    # Copy Glue scripts
    cp "${PROJECT_ROOT}/glue/"*.py "${GLUE_BUILD_DIR}/"

    log_info "Glue scripts copied to: ${GLUE_BUILD_DIR}"
}

# Run linting
lint() {
    log_info "Running linting..."

    cd "${PROJECT_ROOT}"

    if command -v ruff &> /dev/null; then
        ruff check src/ tests/ --fix || true
        ruff format src/ tests/
    else
        log_warn "ruff not installed, skipping linting"
    fi
}

# Run type checking
typecheck() {
    log_info "Running type checking..."

    cd "${PROJECT_ROOT}"

    if command -v mypy &> /dev/null; then
        mypy src/ --ignore-missing-imports || true
    else
        log_warn "mypy not installed, skipping type checking"
    fi
}

# Main function
main() {
    log_info "Starting build process..."

    case "${1:-all}" in
        lambda)
            build_lambda
            ;;
        glue)
            build_glue
            ;;
        lint)
            lint
            ;;
        typecheck)
            typecheck
            ;;
        all)
            lint
            typecheck
            build_lambda
            build_glue
            ;;
        *)
            echo "Usage: $0 {lambda|glue|lint|typecheck|all}"
            exit 1
            ;;
    esac

    log_info "Build completed successfully!"
}

main "$@"
