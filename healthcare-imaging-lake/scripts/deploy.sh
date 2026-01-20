#!/bin/bash
################################################################################
# Terraform Deployment Script for Healthcare Imaging Data Lake
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

# Check requirements
check_requirements() {
    log_info "Checking requirements..."

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi

    log_info "Requirements check passed"
}

# Initialize Terraform
init() {
    log_info "Initializing Terraform..."

    cd "${TERRAFORM_DIR}"

    terraform init \
        -backend-config="key=healthcare-imaging-lake/${ENVIRONMENT}/terraform.tfstate"

    log_info "Terraform initialized"
}

# Plan deployment
plan() {
    log_info "Planning Terraform deployment..."

    cd "${TERRAFORM_DIR}"

    terraform plan \
        -var="environment=${ENVIRONMENT}" \
        -var="aws_region=${AWS_REGION}" \
        -out=tfplan

    log_info "Plan created: tfplan"
}

# Apply deployment
apply() {
    log_info "Applying Terraform deployment..."

    cd "${TERRAFORM_DIR}"

    if [ -f "tfplan" ]; then
        terraform apply tfplan
        rm -f tfplan
    else
        terraform apply \
            -var="environment=${ENVIRONMENT}" \
            -var="aws_region=${AWS_REGION}" \
            -auto-approve
    fi

    log_info "Deployment completed"
}

# Get outputs
outputs() {
    log_info "Terraform outputs:"

    cd "${TERRAFORM_DIR}"

    terraform output -json
}

# Main function
main() {
    log_info "Starting Terraform deployment for healthcare-imaging-lake"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Region: ${AWS_REGION}"

    check_requirements

    case "${1:-deploy}" in
        init)
            init
            ;;
        plan)
            init
            plan
            ;;
        apply)
            apply
            ;;
        deploy)
            init
            plan
            apply
            outputs
            ;;
        outputs)
            outputs
            ;;
        *)
            echo "Usage: $0 {init|plan|apply|deploy|outputs}"
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
