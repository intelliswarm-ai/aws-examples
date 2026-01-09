#!/bin/bash
# Deploy SAM application for Multi-Tenant SaaS
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

echo "=========================================="
echo "Deploying Multi-Tenant SaaS to $ENV"
echo "=========================================="

cd "$PROJECT_DIR"

# Build first if not already built
if [ ! -d "sam/.aws-sam/build" ]; then
    echo "Build artifacts not found. Running build first..."
    ./scripts/build-sam.sh
fi

# Deploy the application
echo "Deploying SAM application to $ENV..."
sam deploy \
    --template-file sam/template.yaml \
    --config-file sam/samconfig.toml \
    --config-env "$ENV" \
    --no-fail-on-empty-changeset

echo "=========================================="
echo "Deployment to $ENV completed successfully!"
echo "=========================================="

# Show stack outputs
echo ""
echo "Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "mt-saas-${ENV}" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table 2>/dev/null || echo "Could not retrieve stack outputs"
