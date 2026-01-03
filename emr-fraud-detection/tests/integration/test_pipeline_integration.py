"""Integration tests for the fraud detection pipeline.

These tests use moto to mock AWS services and test the full pipeline flow.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Try to import moto, skip tests if not available
try:
    import boto3
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_aws = lambda: lambda x: x  # noqa


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestPipelineIntegration:
    """Integration tests for the fraud detection pipeline."""

    @pytest.fixture
    def aws_credentials(self):
        """Mock AWS credentials."""
        import os

        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    @pytest.fixture
    def kinesis_stream(self, aws_credentials):
        """Create a mock Kinesis stream."""
        with mock_aws():
            client = boto3.client("kinesis", region_name="us-east-1")
            client.create_stream(StreamName="test-transactions", ShardCount=1)

            # Wait for stream to be active
            waiter = client.get_waiter("stream_exists")
            waiter.wait(StreamName="test-transactions")

            yield client

    @pytest.fixture
    def dynamodb_tables(self, aws_credentials):
        """Create mock DynamoDB tables."""
        with mock_aws():
            client = boto3.client("dynamodb", region_name="us-east-1")

            # Create alerts table
            client.create_table(
                TableName="test-alerts",
                KeySchema=[{"AttributeName": "alert_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "alert_id", "AttributeType": "S"},
                    {"AttributeName": "account_id", "AttributeType": "S"},
                    {"AttributeName": "created_at", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "account-index",
                        "KeySchema": [
                            {"AttributeName": "account_id", "KeyType": "HASH"},
                            {"AttributeName": "created_at", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create predictions table
            client.create_table(
                TableName="test-predictions",
                KeySchema=[{"AttributeName": "prediction_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "prediction_id", "AttributeType": "S"},
                    {"AttributeName": "transaction_id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "transaction-index",
                        "KeySchema": [
                            {"AttributeName": "transaction_id", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            yield client

    @pytest.fixture
    def s3_buckets(self, aws_credentials):
        """Create mock S3 buckets."""
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")

            client.create_bucket(Bucket="test-data-bucket")
            client.create_bucket(Bucket="test-models-bucket")

            yield client

    @pytest.fixture
    def sns_topic(self, aws_credentials):
        """Create a mock SNS topic."""
        with mock_aws():
            client = boto3.client("sns", region_name="us-east-1")

            response = client.create_topic(Name="test-fraud-alerts")
            topic_arn = response["TopicArn"]

            yield client, topic_arn

    @mock_aws
    def test_ingestion_to_kinesis(
        self,
        aws_credentials,
        sample_transaction: dict,
    ):
        """Test ingesting a transaction to Kinesis."""
        # Setup
        kinesis = boto3.client("kinesis", region_name="us-east-1")
        kinesis.create_stream(StreamName="test-transactions", ShardCount=1)

        waiter = kinesis.get_waiter("stream_exists")
        waiter.wait(StreamName="test-transactions")

        # Import after moto setup
        from src.services.kinesis_service import KinesisService
        from src.common.models import Transaction

        service = KinesisService(
            stream_name="test-transactions",
            client=kinesis,
        )

        tx = Transaction(**sample_transaction)

        # Act
        result = service.put_record(tx)

        # Assert
        assert "ShardId" in result
        assert "SequenceNumber" in result

    @mock_aws
    def test_store_fraud_alert(
        self,
        aws_credentials,
        sample_fraud_alert: dict,
    ):
        """Test storing a fraud alert in DynamoDB."""
        # Setup
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-alerts",
            KeySchema=[{"AttributeName": "alert_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "alert_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        from src.services.dynamodb_service import DynamoDBService
        from src.common.models import FraudAlert, AlertType, Severity

        # Patch settings
        with patch("src.services.dynamodb_service.settings") as mock_settings:
            mock_settings.alerts_table_name = "test-alerts"
            mock_settings.predictions_table_name = "test-predictions"
            mock_settings.executions_table_name = "test-executions"

            service = DynamoDBService(client=dynamodb)

            alert = FraudAlert(**sample_fraud_alert)

            # Act
            service.put_alert(alert)

            # Assert - retrieve and verify
            response = dynamodb.get_item(
                TableName="test-alerts",
                Key={"alert_id": {"S": alert.alert_id}},
            )
            assert "Item" in response
            assert response["Item"]["alert_id"]["S"] == alert.alert_id

    @mock_aws
    def test_send_alert_notification(
        self,
        aws_credentials,
        sample_fraud_alert: dict,
    ):
        """Test sending a fraud alert via SNS."""
        # Setup
        sns = boto3.client("sns", region_name="us-east-1")
        topic_response = sns.create_topic(Name="test-fraud-alerts")
        topic_arn = topic_response["TopicArn"]

        from src.services.notification_service import NotificationService
        from src.common.models import FraudAlert

        service = NotificationService(
            client=sns,
            topic_arn=topic_arn,
        )

        alert = FraudAlert(**sample_fraud_alert)

        # Act
        message_id = service.send_alert(alert)

        # Assert
        assert message_id is not None

    @mock_aws
    def test_store_and_retrieve_prediction(self, aws_credentials):
        """Test storing and retrieving a fraud prediction."""
        # Setup
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")

        # Create predictions table with GSI
        dynamodb.create_table(
            TableName="test-predictions",
            KeySchema=[{"AttributeName": "prediction_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "prediction_id", "AttributeType": "S"},
                {"AttributeName": "transaction_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "transaction-index",
                    "KeySchema": [
                        {"AttributeName": "transaction_id", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        from src.services.dynamodb_service import DynamoDBService
        from src.common.models import FraudPrediction, FraudStatus

        with patch("src.services.dynamodb_service.settings") as mock_settings:
            mock_settings.alerts_table_name = "test-alerts"
            mock_settings.predictions_table_name = "test-predictions"
            mock_settings.executions_table_name = "test-executions"

            service = DynamoDBService(client=dynamodb)

            prediction = FraudPrediction(
                prediction_id="pred-test-001",
                transaction_id="tx-test-001",
                account_id="ACC123",
                fraud_score=0.85,
                fraud_status=FraudStatus.FRAUDULENT,
                confidence=0.92,
                risk_factors=["HIGH_AMOUNT", "NEW_MERCHANT"],
                model_version="v1.0",
                processed_at=datetime.utcnow(),
            )

            # Act - store
            service.put_prediction(prediction)

            # Act - retrieve
            retrieved = service.get_prediction_by_transaction("tx-test-001")

            # Assert
            assert retrieved is not None
            assert retrieved.prediction_id == "pred-test-001"
            assert retrieved.fraud_status == FraudStatus.FRAUDULENT

    @mock_aws
    def test_s3_data_storage(self, aws_credentials):
        """Test storing data in S3."""
        # Setup
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-data-bucket")

        from src.services.s3_service import S3Service

        service = S3Service(bucket="test-data-bucket", client=s3)

        test_data = {
            "transaction_id": "tx-001",
            "amount": 150.50,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Act - store
        service.put_json("raw/test/data.json", test_data)

        # Act - retrieve
        retrieved = service.get_json("raw/test/data.json")

        # Assert
        assert retrieved["transaction_id"] == "tx-001"
        assert retrieved["amount"] == 150.50

    @mock_aws
    def test_full_ingestion_flow(
        self,
        aws_credentials,
        sample_transaction: dict,
    ):
        """Test the full ingestion flow from API to Kinesis."""
        # Setup Kinesis
        kinesis = boto3.client("kinesis", region_name="us-east-1")
        kinesis.create_stream(StreamName="test-transactions", ShardCount=1)

        waiter = kinesis.get_waiter("stream_exists")
        waiter.wait(StreamName="test-transactions")

        # Mock the handler's dependencies
        with patch("src.handlers.ingestion_handler.get_kinesis_client") as mock_kinesis:
            mock_kinesis.return_value = kinesis

            with patch("src.handlers.ingestion_handler.settings") as mock_settings:
                mock_settings.kinesis_stream_name = "test-transactions"

                # Create API Gateway event
                event = {
                    "httpMethod": "POST",
                    "path": "/transactions",
                    "body": json.dumps(sample_transaction),
                    "headers": {"Content-Type": "application/json"},
                }

                # Import handler
                from src.handlers.ingestion_handler import handler

                # Act
                context = MagicMock()
                response = handler(event, context)

                # Assert
                assert response["statusCode"] == 202
                body = json.loads(response["body"])
                assert "transaction_id" in body
