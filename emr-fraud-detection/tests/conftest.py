"""Pytest fixtures for EMR Fraud Detection Pipeline tests."""

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

# Set test environment variables before importing application code
os.environ.update({
    "ENVIRONMENT": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_REGION": "us-east-1",
    "KINESIS_STREAM_NAME": "test-transactions-stream",
    "DATA_BUCKET": "test-data-bucket",
    "MODELS_BUCKET": "test-models-bucket",
    "LOGS_BUCKET": "test-logs-bucket",
    "ALERTS_TABLE_NAME": "test-alerts",
    "PREDICTIONS_TABLE_NAME": "test-predictions",
    "EXECUTIONS_TABLE_NAME": "test-executions",
    "FRAUD_ALERTS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-fraud-alerts",
    "PIPELINE_NOTIFICATIONS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-pipeline",
    "MODEL_VERSION": "v1.0",
    "FRAUD_THRESHOLD": "0.7",
    "SUSPICIOUS_THRESHOLD": "0.4",
    "POWERTOOLS_SERVICE_NAME": "test-fraud-detection",
    "LOG_LEVEL": "DEBUG",
})


@pytest.fixture
def sample_transaction() -> dict[str, Any]:
    """Create a sample transaction for testing."""
    return {
        "transaction_id": "tx-12345",
        "account_id": "ACC123456789",
        "merchant_id": "MERCHANT001",
        "transaction_type": "PURCHASE",
        "channel": "ONLINE",
        "amount": "150.50",
        "currency": "USD",
        "timestamp": "2024-01-15T14:30:00Z",
        "location": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "country": "US",
            "city": "New York",
        },
        "device_info": {
            "device_id": "device-123",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        },
    }


@pytest.fixture
def sample_transaction_batch() -> list[dict[str, Any]]:
    """Create a batch of sample transactions."""
    base_transaction = {
        "account_id": "ACC123456789",
        "merchant_id": "MERCHANT001",
        "transaction_type": "PURCHASE",
        "channel": "ONLINE",
        "currency": "USD",
        "location": {"latitude": 40.7128, "longitude": -74.0060, "country": "US"},
        "device_info": {"device_id": "device-123"},
    }

    transactions = []
    for i in range(5):
        tx = base_transaction.copy()
        tx["transaction_id"] = f"tx-{i:05d}"
        tx["amount"] = str(Decimal("100.00") + Decimal(i * 50))
        tx["timestamp"] = f"2024-01-15T14:{30+i}:00Z"
        transactions.append(tx)

    return transactions


@pytest.fixture
def sample_fraud_alert() -> dict[str, Any]:
    """Create a sample fraud alert for testing."""
    return {
        "alert_id": "alert-12345",
        "transaction_id": "tx-12345",
        "account_id": "ACC123456789",
        "fraud_score": 0.85,
        "alert_type": "FRAUD_DETECTED",
        "severity": "HIGH",
        "message": "High-risk transaction detected",
        "recommended_action": "Block transaction and notify customer",
        "created_at": datetime.utcnow().isoformat(),
        "acknowledged": False,
    }


@pytest.fixture
def sample_prediction() -> dict[str, Any]:
    """Create a sample fraud prediction for testing."""
    return {
        "prediction_id": "pred-12345",
        "transaction_id": "tx-12345",
        "account_id": "ACC123456789",
        "fraud_score": 0.85,
        "fraud_status": "FRAUDULENT",
        "confidence": 0.92,
        "risk_factors": ["HIGH_AMOUNT", "NEW_MERCHANT", "ODD_HOURS"],
        "model_version": "v1.0",
        "processed_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_kinesis_client() -> Generator[MagicMock, None, None]:
    """Mock Kinesis client."""
    with patch("src.common.clients.boto3.client") as mock:
        client = MagicMock()
        mock.return_value = client
        client.put_record.return_value = {"ShardId": "shard-001", "SequenceNumber": "123"}
        client.put_records.return_value = {"FailedRecordCount": 0, "Records": []}
        yield client


@pytest.fixture
def mock_dynamodb_client() -> Generator[MagicMock, None, None]:
    """Mock DynamoDB client."""
    with patch("src.common.clients.boto3.client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_s3_client() -> Generator[MagicMock, None, None]:
    """Mock S3 client."""
    with patch("src.common.clients.boto3.client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_sns_client() -> Generator[MagicMock, None, None]:
    """Mock SNS client."""
    with patch("src.common.clients.boto3.client") as mock:
        client = MagicMock()
        mock.return_value = client
        client.publish.return_value = {"MessageId": "msg-12345"}
        yield client


@pytest.fixture
def mock_emr_client() -> Generator[MagicMock, None, None]:
    """Mock EMR client."""
    with patch("src.common.clients.boto3.client") as mock:
        client = MagicMock()
        mock.return_value = client
        client.run_job_flow.return_value = {"JobFlowId": "j-12345"}
        client.describe_cluster.return_value = {
            "Cluster": {"Status": {"State": "RUNNING"}}
        }
        yield client


@pytest.fixture
def api_gateway_event(sample_transaction: dict) -> dict[str, Any]:
    """Create an API Gateway event for testing."""
    return {
        "httpMethod": "POST",
        "path": "/transactions",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(sample_transaction),
        "pathParameters": None,
        "queryStringParameters": None,
        "requestContext": {
            "requestId": "test-request-id",
            "stage": "test",
        },
    }


@pytest.fixture
def kinesis_event(sample_transaction_batch: list) -> dict[str, Any]:
    """Create a Kinesis event for testing."""
    import base64

    records = []
    for tx in sample_transaction_batch:
        data = base64.b64encode(json.dumps(tx).encode()).decode()
        records.append({
            "kinesis": {
                "sequenceNumber": "123",
                "partitionKey": tx["account_id"],
                "data": data,
            },
            "eventSource": "aws:kinesis",
            "eventSourceARN": "arn:aws:kinesis:us-east-1:123456789012:stream/test-stream",
        })

    return {"Records": records}


@pytest.fixture
def step_functions_event() -> dict[str, Any]:
    """Create a Step Functions event for testing."""
    return {
        "execution_id": "exec-12345",
        "execution_date": "2024-01-15",
        "execution_mode": "FULL",
        "action": "validate",
    }


@pytest.fixture
def lambda_context() -> MagicMock:
    """Create a mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-function"
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.aws_request_id = "test-request-id"
    context.get_remaining_time_in_millis.return_value = 30000
    return context
