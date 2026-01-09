#!/bin/bash
# Destroy SAM application for Multi-Tenant SaaS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default environment
ENV=${1:-dev}

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Invalid environment '$ENV'"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
fi

STACK_NAME="mt-saas-${ENV}"

echo "=========================================="
echo "Destroying Multi-Tenant SaaS Stack: $STACK_NAME"
echo "=========================================="

# Confirm destruction for non-dev environments
if [ "$ENV" != "dev" ]; then
    read -p "Are you sure you want to destroy the $ENV stack? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Destruction cancelled."
        exit 0
    fi
fi

cd "$PROJECT_DIR"

# Delete the stack
echo "Deleting CloudFormation stack..."
sam delete \
    --stack-name "$STACK_NAME" \
    --no-prompts \
    --region eu-central-1

echo "=========================================="
echo "Stack $STACK_NAME destroyed successfully!"
echo "=========================================="
