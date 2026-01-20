#!/bin/bash
################################################################################
# SAM Build Script for Healthcare Imaging Data Lake
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

# Check SAM CLI
check_sam() {
    if ! command -v sam &> /dev/null; then
        log_error "SAM CLI is not installed"
        log_info "Install it with: pip install aws-sam-cli"
        exit 1
    fi
}

# Build with SAM
build() {
    log_info "Building with SAM..."

    cd "${PROJECT_ROOT}"

    sam build \
        --template-file sam/template.yaml \
        --build-dir .aws-sam/build \
        --parallel \
        --cached

    log_info "SAM build completed"
}

# Validate template
validate() {
    log_info "Validating SAM template..."

    cd "${PROJECT_ROOT}"

    sam validate \
        --template-file sam/template.yaml \
        --lint

    log_info "Template validation passed"
}

# Main function
main() {
    log_info "Starting SAM build process..."

    check_sam

    case "${1:-build}" in
        build)
            build
            ;;
        validate)
            validate
            ;;
        all)
            validate
            build
            ;;
        *)
            echo "Usage: $0 {build|validate|all}"
            exit 1
            ;;
    esac

    log_info "SAM build process completed!"
}

main "$@"
