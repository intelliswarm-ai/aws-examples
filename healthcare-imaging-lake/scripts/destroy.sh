#!/bin/bash
################################################################################
# Terraform Destroy Script for Healthcare Imaging Data Lake
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="${PROJECT_ROOT}/terraform"

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

# Confirm destruction
confirm() {
    log_warn "This will DESTROY all resources for healthcare-imaging-lake in ${ENVIRONMENT}"
    log_warn "This action cannot be undone!"

    read -p "Are you sure you want to continue? (yes/no): " CONFIRM

    if [ "${CONFIRM}" != "yes" ]; then
        log_info "Destruction cancelled"
        exit 0
    fi
}

# Empty S3 buckets
empty_buckets() {
    log_info "Emptying S3 buckets..."

    cd "${TERRAFORM_DIR}"

    # Get bucket names from Terraform output
    IMAGES_BUCKET=$(terraform output -raw images_bucket_name 2>/dev/null || echo "")
    METADATA_BUCKET=$(terraform output -raw metadata_bucket_name 2>/dev/null || echo "")
    RESULTS_BUCKET=$(terraform output -raw results_bucket_name 2>/dev/null || echo "")

    for BUCKET in "${IMAGES_BUCKET}" "${METADATA_BUCKET}" "${RESULTS_BUCKET}"; do
        if [ -n "${BUCKET}" ]; then
            log_info "Emptying bucket: ${BUCKET}"

            # Delete all objects
            aws s3 rm "s3://${BUCKET}" --recursive --region "${AWS_REGION}" 2>/dev/null || true

            # Delete all object versions (for versioned buckets)
            aws s3api list-object-versions \
                --bucket "${BUCKET}" \
                --query 'Versions[].{Key:Key,VersionId:VersionId}' \
                --output json \
                --region "${AWS_REGION}" 2>/dev/null | \
            jq -r '.[] | "\(.Key) \(.VersionId)"' 2>/dev/null | \
            while read -r KEY VERSION; do
                aws s3api delete-object \
                    --bucket "${BUCKET}" \
                    --key "${KEY}" \
                    --version-id "${VERSION}" \
                    --region "${AWS_REGION}" 2>/dev/null || true
            done

            # Delete delete markers
            aws s3api list-object-versions \
                --bucket "${BUCKET}" \
                --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' \
                --output json \
                --region "${AWS_REGION}" 2>/dev/null | \
            jq -r '.[] | "\(.Key) \(.VersionId)"' 2>/dev/null | \
            while read -r KEY VERSION; do
                aws s3api delete-object \
                    --bucket "${BUCKET}" \
                    --key "${KEY}" \
                    --version-id "${VERSION}" \
                    --region "${AWS_REGION}" 2>/dev/null || true
            done
        fi
    done

    log_info "Buckets emptied"
}

# Destroy infrastructure
destroy() {
    log_info "Destroying Terraform infrastructure..."

    cd "${TERRAFORM_DIR}"

    terraform destroy \
        -var="environment=${ENVIRONMENT}" \
        -var="aws_region=${AWS_REGION}" \
        -auto-approve

    log_info "Infrastructure destroyed"
}

# Main function
main() {
    log_info "Starting destruction of healthcare-imaging-lake"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Region: ${AWS_REGION}"

    confirm
    empty_buckets
    destroy

    log_info "Destruction completed!"
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
        --force|-f)
            FORCE=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

main
