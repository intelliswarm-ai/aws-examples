#!/bin/bash
################################################################################
# SAM Deployment Script for Healthcare Imaging Data Lake
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check requirements
check_requirements() {
    log_info "Checking requirements..."

    if ! command -v sam &> /dev/null; then
        log_error "SAM CLI is not installed"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    log_info "Requirements check passed"
}

# Build
build() {
    log_info "Building SAM application..."

    cd "${PROJECT_ROOT}"

    sam build \
        --template-file sam/template.yaml \
        --parallel \
        --cached

    log_info "Build completed"
}

# Deploy
deploy() {
    log_info "Deploying SAM application..."

    cd "${PROJECT_ROOT}"

    # Check if required parameters are set
    if [ -z "${IMAGES_BUCKET:-}" ] || [ -z "${METADATA_BUCKET:-}" ] || [ -z "${RESULTS_BUCKET:-}" ]; then
        log_warn "Using guided deployment mode (buckets not specified)"

        sam deploy \
            --template-file sam/template.yaml \
            --config-file sam/samconfig.toml \
            --config-env "${ENVIRONMENT}" \
            --guided

    else
        sam deploy \
            --template-file sam/template.yaml \
            --config-file sam/samconfig.toml \
            --config-env "${ENVIRONMENT}" \
            --parameter-overrides \
                "Environment=${ENVIRONMENT}" \
                "ImagesBucketName=${IMAGES_BUCKET}" \
                "MetadataBucketName=${METADATA_BUCKET}" \
                "ResultsBucketName=${RESULTS_BUCKET}" \
                "KMSKeyId=${KMS_KEY_ID:-}" \
                "GlueDatabaseName=${GLUE_DATABASE:-healthcare_imaging}" \
                "GlueCrawlerName=${GLUE_CRAWLER:-}" \
                "AthenaWorkgroupName=${ATHENA_WORKGROUP:-}" \
                "EnableLakeFormation=${ENABLE_LAKEFORMATION:-true}" \
            --no-confirm-changeset
    fi

    log_info "Deployment completed"
}

# Get outputs
outputs() {
    log_info "SAM stack outputs:"

    cd "${PROJECT_ROOT}"

    STACK_NAME="healthcare-imaging-lake-${ENVIRONMENT}"

    aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --query 'Stacks[0].Outputs' \
        --output table \
        --region "${AWS_REGION}"
}

# Main function
main() {
    log_info "Starting SAM deployment for healthcare-imaging-lake"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Region: ${AWS_REGION}"

    check_requirements

    case "${1:-deploy}" in
        build)
            build
            ;;
        deploy)
            build
            deploy
            outputs
            ;;
        outputs)
            outputs
            ;;
        *)
            echo "Usage: $0 {build|deploy|outputs}"
            exit 1
            ;;
    esac

    log_info "Operation completed!"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region|-r)
            AWS_REGION="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

main "${1:-deploy}"
