#!/bin/bash
set -euo pipefail

# EMR Fraud Detection Pipeline - Deployment Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DIST_DIR="${PROJECT_ROOT}/dist"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOY_METHOD="${DEPLOY_METHOD:-terraform}"  # terraform or cloudformation

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

Deploy EMR Fraud Detection Pipeline

Options:
    -e, --environment ENV       Environment (dev/staging/prod, default: dev)
    -r, --region REGION         AWS region (default: us-east-1)
    -m, --method METHOD         Deployment method (terraform/cloudformation, default: terraform)
    -b, --build                 Build before deploying
    --skip-upload               Skip uploading artifacts to S3
    -h, --help                  Show this help message

Environment Variables:
    DATA_BUCKET                 S3 bucket for data (auto-created if not set)
    CODE_BUCKET                 S3 bucket for code artifacts
    MODELS_BUCKET               S3 bucket for ML models
    TEMPLATES_BUCKET            S3 bucket for CFN templates (CloudFormation only)

EOF
    exit 1
}

BUILD=false
SKIP_UPLOAD=false

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
        -b|--build)
            BUILD=true
            shift
            ;;
        --skip-upload)
            SKIP_UPLOAD=true
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

# Validate environment
validate_environment() {
    log_info "Validating environment..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account: ${AWS_ACCOUNT_ID}"
    log_info "AWS Region: ${AWS_REGION}"
    log_info "Environment: ${ENVIRONMENT}"
}

# Build artifacts
build_artifacts() {
    if [[ "$BUILD" == "true" ]]; then
        log_info "Building artifacts..."
        "${SCRIPT_DIR}/build.sh" --all --clean
    else
        # Check if artifacts exist
        if [[ ! -f "${DIST_DIR}/lambda/fraud-detection.zip" ]]; then
            log_warn "Lambda package not found, building..."
            "${SCRIPT_DIR}/build.sh" --lambda
        fi
    fi
}

# Upload artifacts to S3
upload_artifacts() {
    if [[ "$SKIP_UPLOAD" == "true" ]]; then
        log_info "Skipping artifact upload"
        return
    fi

    log_info "Uploading artifacts to S3..."

    # Determine code bucket
    CODE_BUCKET="${CODE_BUCKET:-fraud-detection-${ENVIRONMENT}-code-${AWS_ACCOUNT_ID}}"

    # Create bucket if it doesn't exist
    if ! aws s3 ls "s3://${CODE_BUCKET}" 2>&1 > /dev/null; then
        log_info "Creating code bucket: ${CODE_BUCKET}"
        aws s3 mb "s3://${CODE_BUCKET}" --region "${AWS_REGION}"
    fi

    # Upload Lambda package
    log_info "Uploading Lambda package..."
    aws s3 cp "${DIST_DIR}/lambda/fraud-detection.zip" \
        "s3://${CODE_BUCKET}/lambda/fraud-detection.zip" \
        --region "${AWS_REGION}"

    # Upload Spark jobs
    log_info "Uploading Spark jobs..."
    aws s3 sync "${DIST_DIR}/spark/" \
        "s3://${CODE_BUCKET}/spark/jobs/" \
        --region "${AWS_REGION}"

    log_info "Artifacts uploaded to s3://${CODE_BUCKET}/"
}

# Deploy with Terraform
deploy_terraform() {
    log_info "Deploying with Terraform..."

    TF_DIR="${PROJECT_ROOT}/terraform"
    cd "${TF_DIR}"

    # Initialize
    log_info "Initializing Terraform..."
    terraform init -upgrade

    # Create workspace if needed
    terraform workspace select "${ENVIRONMENT}" 2>/dev/null || \
        terraform workspace new "${ENVIRONMENT}"

    # Plan
    log_info "Planning deployment..."
    terraform plan \
        -var="environment=${ENVIRONMENT}" \
        -var="aws_region=${AWS_REGION}" \
        -out=tfplan

    # Apply
    log_info "Applying deployment..."
    terraform apply -auto-approve tfplan

    # Get outputs
    log_info "Deployment outputs:"
    terraform output

    rm -f tfplan
}

# Deploy with CloudFormation
deploy_cloudformation() {
    log_info "Deploying with CloudFormation..."

    TEMPLATES_BUCKET="${TEMPLATES_BUCKET:-fraud-detection-${ENVIRONMENT}-templates-${AWS_ACCOUNT_ID}}"

    "${PROJECT_ROOT}/cloudformation/deploy-cfn.sh" \
        --stack-name "fraud-detection" \
        --environment "${ENVIRONMENT}" \
        --region "${AWS_REGION}" \
        --templates-bucket "${TEMPLATES_BUCKET}"
}

# Post-deployment validation
validate_deployment() {
    log_info "Validating deployment..."

    # Check Lambda functions
    FUNCTIONS=$(aws lambda list-functions \
        --query "Functions[?starts_with(FunctionName, 'fraud-detection-${ENVIRONMENT}')].FunctionName" \
        --output text \
        --region "${AWS_REGION}")

    if [[ -n "$FUNCTIONS" ]]; then
        log_info "Lambda functions deployed:"
        echo "$FUNCTIONS" | tr '\t' '\n' | while read -r fn; do
            log_info "  - $fn"
        done
    fi

    # Check Step Functions
    STATE_MACHINES=$(aws stepfunctions list-state-machines \
        --query "stateMachines[?contains(name, 'fraud-detection-${ENVIRONMENT}')].name" \
        --output text \
        --region "${AWS_REGION}")

    if [[ -n "$STATE_MACHINES" ]]; then
        log_info "State machines deployed: $STATE_MACHINES"
    fi

    log_info "Deployment validation completed"
}

# Main
main() {
    log_info "Starting deployment..."
    log_info "Deployment method: ${DEPLOY_METHOD}"

    validate_environment
    build_artifacts
    upload_artifacts

    case "$DEPLOY_METHOD" in
        terraform)
            deploy_terraform
            ;;
        cloudformation)
            deploy_cloudformation
            ;;
        *)
            log_error "Unknown deployment method: ${DEPLOY_METHOD}"
            exit 1
            ;;
    esac

    validate_deployment

    log_info "Deployment completed successfully!"
}

main
