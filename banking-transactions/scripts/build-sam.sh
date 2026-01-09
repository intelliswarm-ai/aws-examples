#!/bin/bash
# Build SAM application for Banking Platform
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Building Banking Platform SAM Application"
echo "=========================================="

cd "$PROJECT_DIR"

# Validate template first
echo "Validating SAM template..."
sam validate --template-file sam/template.yaml --lint

# Build the application
echo "Building SAM application..."
sam build \
    --template-file sam/template.yaml \
    --build-dir sam/.aws-sam/build \
    --parallel \
    --cached

echo "=========================================="
echo "Build completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - Deploy to dev:     ./scripts/deploy-sam.sh dev"
echo "  - Deploy to staging: ./scripts/deploy-sam.sh staging"
echo "  - Deploy to prod:    ./scripts/deploy-sam.sh prod"
