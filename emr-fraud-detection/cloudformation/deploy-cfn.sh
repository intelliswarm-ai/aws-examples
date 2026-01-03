#!/bin/bash
set -euo pipefail

# EMR Fraud Detection Pipeline - CloudFormation Deployment Script

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STACK_NAME="${STACK_NAME:-fraud-detection}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TEMPLATES_BUCKET="${TEMPLATES_BUCKET:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy EMR Fraud Detection Pipeline using CloudFormation

Options:
    -s, --stack-name NAME       Stack name (default: fraud-detection)
    -e, --environment ENV       Environment (dev/staging/prod, default: dev)
    -r, --region REGION         AWS region (default: us-east-1)
    -b, --templates-bucket      S3 bucket for nested templates (required)
    -m, --alert-email EMAIL     Email for alerts (optional)
    -h, --help                  Show this help message

Examples:
    $0 -b my-templates-bucket -e dev
    $0 -s my-stack -b my-templates-bucket -e prod -m alerts@example.com

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -b|--templates-bucket)
            TEMPLATES_BUCKET="$2"
            shift 2
            ;;
        -m|--alert-email)
            ALERT_EMAIL="$2"
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

# Validate required parameters
if [[ -z "$TEMPLATES_BUCKET" ]]; then
    log_error "Templates bucket is required. Use -b or --templates-bucket"
    usage
fi

FULL_STACK_NAME="${STACK_NAME}-${ENVIRONMENT}"

log_info "Deploying EMR Fraud Detection Pipeline"
log_info "Stack Name: $FULL_STACK_NAME"
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"
log_info "Templates Bucket: $TEMPLATES_BUCKET"

# Upload nested templates to S3
upload_templates() {
    log_info "Uploading nested templates to S3..."

    # Create bucket if it doesn't exist
    if ! aws s3 ls "s3://${TEMPLATES_BUCKET}" 2>&1 > /dev/null; then
        log_info "Creating templates bucket..."
        aws s3 mb "s3://${TEMPLATES_BUCKET}" --region "$AWS_REGION"
    fi

    # Upload nested templates
    aws s3 sync "${SCRIPT_DIR}/nested/" "s3://${TEMPLATES_BUCKET}/nested/" \
        --region "$AWS_REGION" \
        --exclude "*" \
        --include "*.yaml"

    log_info "Templates uploaded successfully"
}

# Deploy the stack
deploy_stack() {
    log_info "Deploying CloudFormation stack..."

    # Build parameters
    PARAMS="ParameterKey=Environment,ParameterValue=${ENVIRONMENT}"
    PARAMS="${PARAMS} ParameterKey=ProjectName,ParameterValue=${STACK_NAME}"
    PARAMS="${PARAMS} ParameterKey=TemplatesBucket,ParameterValue=${TEMPLATES_BUCKET}"

    if [[ -n "$ALERT_EMAIL" ]]; then
        PARAMS="${PARAMS} ParameterKey=AlertEmail,ParameterValue=${ALERT_EMAIL}"
    fi

    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$FULL_STACK_NAME" --region "$AWS_REGION" 2>&1 > /dev/null; then
        log_info "Updating existing stack..."

        aws cloudformation update-stack \
            --stack-name "$FULL_STACK_NAME" \
            --template-body "file://${SCRIPT_DIR}/main.yaml" \
            --parameters $PARAMS \
            --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --region "$AWS_REGION" || {
                if [[ $? -eq 255 ]]; then
                    log_info "No updates to perform"
                    return 0
                fi
                return 1
            }

        log_info "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name "$FULL_STACK_NAME" \
            --region "$AWS_REGION"
    else
        log_info "Creating new stack..."

        aws cloudformation create-stack \
            --stack-name "$FULL_STACK_NAME" \
            --template-body "file://${SCRIPT_DIR}/main.yaml" \
            --parameters $PARAMS \
            --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --region "$AWS_REGION"

        log_info "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete \
            --stack-name "$FULL_STACK_NAME" \
            --region "$AWS_REGION"
    fi

    log_info "Stack deployment completed successfully"
}

# Get stack outputs
get_outputs() {
    log_info "Stack Outputs:"

    aws cloudformation describe-stacks \
        --stack-name "$FULL_STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
}

# Main execution
main() {
    upload_templates
    deploy_stack
    get_outputs

    log_info "Deployment complete!"
}

main
