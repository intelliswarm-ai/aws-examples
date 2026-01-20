#!/bin/bash
################################################################################
# SAM Destroy Script for Healthcare Imaging Data Lake
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="healthcare-imaging-lake-${ENVIRONMENT}"

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
    log_warn "This will DELETE the CloudFormation stack: ${STACK_NAME}"
    log_warn "This action cannot be undone!"

    read -p "Are you sure you want to continue? (yes/no): " CONFIRM

    if [ "${CONFIRM}" != "yes" ]; then
        log_info "Destruction cancelled"
        exit 0
    fi
}

# Delete stack
delete_stack() {
    log_info "Deleting SAM stack: ${STACK_NAME}"

    cd "${PROJECT_ROOT}"

    sam delete \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}" \
        --no-prompts

    log_info "Stack deleted"
}

# Main function
main() {
    log_info "Starting destruction of SAM stack"
    log_info "Stack: ${STACK_NAME}"
    log_info "Region: ${AWS_REGION}"

    confirm
    delete_stack

    log_info "Destruction completed!"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            STACK_NAME="healthcare-imaging-lake-${ENVIRONMENT}"
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
