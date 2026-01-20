#!/bin/bash
################################################################################
# CloudFormation Deployment Script for Healthcare Imaging Data Lake
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_NAME="${PROJECT_NAME:-healthcare-imaging-lake}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check required environment variables
check_requirements() {
    log_info "Checking requirements..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    if [ -z "${DEPLOYMENT_BUCKET:-}" ]; then
        log_error "DEPLOYMENT_BUCKET environment variable is required"
        exit 1
    fi

    log_info "Requirements check passed"
}

# Upload nested templates to S3
upload_templates() {
    log_info "Uploading nested templates to S3..."

    # Create S3 prefix
    S3_PREFIX="cloudformation"

    # Upload nested templates
    aws s3 cp "${SCRIPT_DIR}/nested/" "s3://${DEPLOYMENT_BUCKET}/${S3_PREFIX}/nested/" \
        --recursive \
        --region "${AWS_REGION}"

    log_info "Templates uploaded successfully"
}

# Build and upload Lambda package
build_lambda() {
    log_info "Building Lambda deployment package..."

    LAMBDA_DIR="${PROJECT_ROOT}/src"
    BUILD_DIR="${PROJECT_ROOT}/.build"
    PACKAGE_FILE="${BUILD_DIR}/lambda.zip"

    # Create build directory
    rm -rf "${BUILD_DIR}"
    mkdir -p "${BUILD_DIR}"

    # Create package
    cd "${PROJECT_ROOT}"

    # Install dependencies
    pip install -r requirements.txt -t "${BUILD_DIR}/package" --quiet

    # Copy source code
    cp -r src "${BUILD_DIR}/package/"

    # Create zip
    cd "${BUILD_DIR}/package"
    zip -r "${PACKAGE_FILE}" . -x "*.pyc" -x "__pycache__/*" > /dev/null

    # Upload to S3
    aws s3 cp "${PACKAGE_FILE}" "s3://${DEPLOYMENT_BUCKET}/lambda/${PROJECT_NAME}.zip" \
        --region "${AWS_REGION}"

    log_info "Lambda package uploaded successfully"
}

# Deploy CloudFormation stack
deploy_stack() {
    log_info "Deploying CloudFormation stack..."

    STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "${STACK_NAME}" --region "${AWS_REGION}" &> /dev/null; then
        ACTION="update"
    else
        ACTION="create"
    fi

    log_info "Stack action: ${ACTION}"

    # Deploy stack
    aws cloudformation deploy \
        --template-file "${SCRIPT_DIR}/main.yaml" \
        --stack-name "${STACK_NAME}" \
        --parameter-overrides \
            Environment="${ENVIRONMENT}" \
            ProjectName="${PROJECT_NAME}" \
            DeploymentBucket="${DEPLOYMENT_BUCKET}" \
            DeploymentKey="lambda/${PROJECT_NAME}.zip" \
            EnableLakeFormation="${ENABLE_LAKEFORMATION:-true}" \
            LakeFormationAdminArn="${LAKEFORMATION_ADMIN_ARN:-}" \
            AlertEmail="${ALERT_EMAIL:-}" \
        --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
        --region "${AWS_REGION}" \
        --tags \
            Environment="${ENVIRONMENT}" \
            Project="${PROJECT_NAME}" \
            ManagedBy="CloudFormation"

    log_info "Stack deployment completed"
}

# Get stack outputs
get_outputs() {
    log_info "Stack outputs:"

    STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

    aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
}

# Main function
main() {
    log_info "Starting CloudFormation deployment for ${PROJECT_NAME}"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Region: ${AWS_REGION}"

    check_requirements
    upload_templates
    build_lambda
    deploy_stack
    get_outputs

    log_info "Deployment completed successfully!"
}

# Parse command line arguments
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
        --bucket|-b)
            DEPLOYMENT_BUCKET="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -e, --environment   Environment name (default: dev)"
            echo "  -r, --region        AWS region (default: us-east-1)"
            echo "  -b, --bucket        Deployment S3 bucket (required)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  DEPLOYMENT_BUCKET         S3 bucket for deployment artifacts"
            echo "  ENABLE_LAKEFORMATION      Enable Lake Formation (default: true)"
            echo "  LAKEFORMATION_ADMIN_ARN   Lake Formation admin ARN (optional)"
            echo "  ALERT_EMAIL               Email for CloudWatch alarms (optional)"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main
