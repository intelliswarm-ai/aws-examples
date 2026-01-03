#!/bin/bash
set -euo pipefail

# EMR Fraud Detection Pipeline - Destroy Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOY_METHOD="${DEPLOY_METHOD:-terraform}"
FORCE=false

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

Destroy EMR Fraud Detection Pipeline infrastructure

Options:
    -e, --environment ENV       Environment (dev/staging/prod, default: dev)
    -r, --region REGION         AWS region (default: us-east-1)
    -m, --method METHOD         Deployment method (terraform/cloudformation, default: terraform)
    -f, --force                 Skip confirmation prompt
    -h, --help                  Show this help message

WARNING: This will permanently delete all infrastructure and data!

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -m|--method)
            DEPLOY_METHOD="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
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

# Confirm destruction
confirm_destroy() {
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi

    log_warn "This will PERMANENTLY DELETE all infrastructure for environment: ${ENVIRONMENT}"
    log_warn "This includes:"
    log_warn "  - All S3 buckets and data"
    log_warn "  - All DynamoDB tables and data"
    log_warn "  - All Lambda functions"
    log_warn "  - All EMR clusters"
    log_warn "  - All Step Functions state machines"
    log_warn "  - All VPC resources"

    echo ""
    read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirmation

    if [[ "$confirmation" != "yes" ]]; then
        log_info "Destruction cancelled"
        exit 0
    fi
}

# Terminate any running EMR clusters
terminate_emr_clusters() {
    log_info "Checking for running EMR clusters..."

    CLUSTERS=$(aws emr list-clusters \
        --active \
        --query "Clusters[?contains(Name, 'fraud-detection-${ENVIRONMENT}')].Id" \
        --output text \
        --region "${AWS_REGION}")

    if [[ -n "$CLUSTERS" ]]; then
        log_warn "Terminating EMR clusters..."
        for cluster_id in $CLUSTERS; do
            log_info "Terminating cluster: ${cluster_id}"
            aws emr terminate-clusters --cluster-ids "${cluster_id}" --region "${AWS_REGION}"
        done

        # Wait for termination
        log_info "Waiting for clusters to terminate..."
        for cluster_id in $CLUSTERS; do
            aws emr wait cluster-terminated --cluster-id "${cluster_id}" --region "${AWS_REGION}" || true
        done
    fi
}

# Empty S3 buckets
empty_s3_buckets() {
    log_info "Emptying S3 buckets..."

    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

    BUCKET_PREFIXES=(
        "fraud-detection-${ENVIRONMENT}-data"
        "fraud-detection-${ENVIRONMENT}-models"
        "fraud-detection-${ENVIRONMENT}-logs"
        "fraud-detection-${ENVIRONMENT}-code"
    )

    for prefix in "${BUCKET_PREFIXES[@]}"; do
        BUCKET="${prefix}-${AWS_ACCOUNT_ID}"
        if aws s3 ls "s3://${BUCKET}" 2>&1 > /dev/null; then
            log_info "Emptying bucket: ${BUCKET}"
            aws s3 rm "s3://${BUCKET}" --recursive --region "${AWS_REGION}" || true

            # Also remove versions if versioning is enabled
            aws s3api list-object-versions \
                --bucket "${BUCKET}" \
                --query 'Versions[].{Key: Key, VersionId: VersionId}' \
                --output text 2>/dev/null | while read -r key version; do
                if [[ -n "$key" && -n "$version" ]]; then
                    aws s3api delete-object \
                        --bucket "${BUCKET}" \
                        --key "$key" \
                        --version-id "$version" 2>/dev/null || true
                fi
            done
        fi
    done
}

# Destroy with Terraform
destroy_terraform() {
    log_info "Destroying with Terraform..."

    TF_DIR="${PROJECT_ROOT}/terraform"
    cd "${TF_DIR}"

    # Select workspace
    terraform workspace select "${ENVIRONMENT}" 2>/dev/null || {
        log_warn "Workspace ${ENVIRONMENT} does not exist"
        return 0
    }

    # Destroy
    log_info "Running terraform destroy..."
    terraform destroy \
        -var="environment=${ENVIRONMENT}" \
        -var="aws_region=${AWS_REGION}" \
        -auto-approve

    # Delete workspace
    terraform workspace select default
    terraform workspace delete "${ENVIRONMENT}" || true

    log_info "Terraform destruction completed"
}

# Destroy with CloudFormation
destroy_cloudformation() {
    log_info "Destroying with CloudFormation..."

    STACK_NAME="fraud-detection-${ENVIRONMENT}"

    # Check if stack exists
    if ! aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}" 2>&1 > /dev/null; then
        log_warn "Stack ${STACK_NAME} does not exist"
        return 0
    fi

    # Delete stack
    log_info "Deleting CloudFormation stack: ${STACK_NAME}"
    aws cloudformation delete-stack \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}"

    # Wait for deletion
    log_info "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}"

    log_info "CloudFormation destruction completed"
}

# Main
main() {
    log_info "Starting destruction process..."
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Region: ${AWS_REGION}"
    log_info "Method: ${DEPLOY_METHOD}"

    confirm_destroy
    terminate_emr_clusters
    empty_s3_buckets

    case "$DEPLOY_METHOD" in
        terraform)
            destroy_terraform
            ;;
        cloudformation)
            destroy_cloudformation
            ;;
        *)
            log_error "Unknown deployment method: ${DEPLOY_METHOD}"
            exit 1
            ;;
    esac

    log_info "Destruction completed successfully!"
}

main
