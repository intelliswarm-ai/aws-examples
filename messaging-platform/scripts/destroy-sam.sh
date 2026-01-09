#!/bin/bash
# Destroy SAM application for SMS Marketing Platform
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

STACK_NAME="sms-marketing-${ENV}"

echo "=========================================="
echo "Destroying SMS Marketing Stack: $STACK_NAME"
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

# Empty S3 bucket first (required before deletion)
echo "Emptying S3 bucket (if exists)..."
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`ArchiveBucketName`].OutputValue' \
    --output text 2>/dev/null) || true

if [ -n "$BUCKET_NAME" ] && [ "$BUCKET_NAME" != "None" ]; then
    echo "Emptying bucket: $BUCKET_NAME"
    aws s3 rm "s3://${BUCKET_NAME}" --recursive 2>/dev/null || true
fi

# Delete the stack
echo "Deleting CloudFormation stack..."
sam delete \
    --stack-name "$STACK_NAME" \
    --no-prompts \
    --region eu-central-1

echo "=========================================="
echo "Stack $STACK_NAME destroyed successfully!"
echo "=========================================="
