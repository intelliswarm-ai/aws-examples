"""Unit tests for data models."""

from datetime import datetime
from decimal import Decimal

import pytest

from src.common.models import (
    EMRClusterConfig,
    FeatureVector,
    FraudAlert,
    FraudPrediction,
    FraudStatus,
    Severity,
    SparkJobConfig,
    Transaction,
    TransactionChannel,
    TransactionType,
)


class TestTransaction:
    """Tests for Transaction model."""

    def test_create_transaction(self, sample_transaction: dict):
        """Test creating a transaction from dict."""
        tx = Transaction(**sample_transaction)

        assert tx.transaction_id == "tx-12345"
        assert tx.account_id == "ACC123456789"
        assert tx.amount == Decimal("150.50")
        assert tx.transaction_type == TransactionType.PURCHASE
        assert tx.channel == TransactionChannel.ONLINE

    def test_transaction_generates_id(self):
        """Test that transaction generates ID if not provided."""
        tx = Transaction(
            account_id="ACC123",
            transaction_type=TransactionType.PURCHASE,
            channel=TransactionChannel.POS,
            amount=Decimal("100.00"),
            currency="USD",
            timestamp=datetime.utcnow(),
        )

        assert tx.transaction_id is not None
        assert tx.transaction_id.startswith("tx-")

    def test_transaction_validation_amount(self):
        """Test that amount must be positive."""
        with pytest.raises(ValueError):
            Transaction(
                account_id="ACC123",
                transaction_type=TransactionType.PURCHASE,
                channel=TransactionChannel.POS,
                amount=Decimal("-100.00"),  # Negative amount
                currency="USD",
                timestamp=datetime.utcnow(),
            )

    def test_transaction_to_kinesis_record(self, sample_transaction: dict):
        """Test converting transaction to Kinesis record."""
        tx = Transaction(**sample_transaction)
        record = tx.to_kinesis_record()

        assert "Data" in record
        assert "PartitionKey" in record
        assert record["PartitionKey"] == tx.account_id

    def test_transaction_to_dynamodb_item(self, sample_transaction: dict):
        """Test converting transaction to DynamoDB item."""
        tx = Transaction(**sample_transaction)
        item = tx.to_dynamodb_item()

        assert "transaction_id" in item
        assert "S" in item["transaction_id"]
        assert item["transaction_id"]["S"] == tx.transaction_id
        assert "N" in item["amount"]


class TestFraudPrediction:
    """Tests for FraudPrediction model."""

    def test_create_prediction(self, sample_prediction: dict):
        """Test creating a prediction."""
        pred = FraudPrediction(**sample_prediction)

        assert pred.prediction_id == "pred-12345"
        assert pred.fraud_score == 0.85
        assert pred.fraud_status == FraudStatus.FRAUDULENT

    def test_prediction_status_from_score(self):
        """Test that status is correctly determined from score."""
        # Fraudulent (>= 0.7)
        pred = FraudPrediction(
            prediction_id="p1",
            transaction_id="t1",
            account_id="a1",
            fraud_score=0.85,
            fraud_status=FraudStatus.FRAUDULENT,
            confidence=0.9,
            risk_factors=[],
            model_version="v1.0",
            processed_at=datetime.utcnow(),
        )
        assert pred.fraud_status == FraudStatus.FRAUDULENT

        # Suspicious (0.4 - 0.7)
        pred2 = FraudPrediction(
            prediction_id="p2",
            transaction_id="t2",
            account_id="a2",
            fraud_score=0.55,
            fraud_status=FraudStatus.SUSPICIOUS,
            confidence=0.8,
            risk_factors=[],
            model_version="v1.0",
            processed_at=datetime.utcnow(),
        )
        assert pred2.fraud_status == FraudStatus.SUSPICIOUS

    def test_prediction_to_dynamodb_item(self, sample_prediction: dict):
        """Test converting prediction to DynamoDB item."""
        pred = FraudPrediction(**sample_prediction)
        item = pred.to_dynamodb_item()

        assert "prediction_id" in item
        assert "fraud_score" in item
        assert "N" in item["fraud_score"]


class TestFraudAlert:
    """Tests for FraudAlert model."""

    def test_create_alert(self, sample_fraud_alert: dict):
        """Test creating a fraud alert."""
        alert = FraudAlert(**sample_fraud_alert)

        assert alert.alert_id == "alert-12345"
        assert alert.severity == Severity.HIGH
        assert alert.acknowledged is False

    def test_alert_to_sns_message(self, sample_fraud_alert: dict):
        """Test converting alert to SNS message."""
        alert = FraudAlert(**sample_fraud_alert)
        message = alert.to_sns_message()

        assert "default" in message
        assert alert.alert_id in message["default"]


class TestFeatureVector:
    """Tests for FeatureVector model."""

    def test_create_feature_vector(self):
        """Test creating a feature vector."""
        fv = FeatureVector(
            transaction_id="tx-123",
            account_id="ACC123",
            amount=150.0,
            hour_of_day=14,
            day_of_week=3,
            is_weekend=0,
            tx_count_1h=2,
            tx_count_24h=5,
            tx_amount_1h=300.0,
            tx_amount_24h=750.0,
            avg_amount_30d=200.0,
            std_amount_30d=50.0,
            amount_zscore=1.0,
            distance_from_last=10.5,
            time_since_last=2.0,
            is_new_merchant=0,
            is_new_device=0,
            is_high_risk_country=0,
            channel_encoded=2,
            tx_type_encoded=0,
            timestamp=datetime.utcnow(),
        )

        assert fv.transaction_id == "tx-123"
        assert fv.amount == 150.0
        assert fv.hour_of_day == 14

    def test_feature_vector_to_array(self):
        """Test converting feature vector to array."""
        fv = FeatureVector(
            transaction_id="tx-123",
            account_id="ACC123",
            amount=150.0,
            hour_of_day=14,
            day_of_week=3,
            is_weekend=0,
            tx_count_1h=2,
            tx_count_24h=5,
            tx_amount_1h=300.0,
            tx_amount_24h=750.0,
            avg_amount_30d=200.0,
            std_amount_30d=50.0,
            amount_zscore=1.0,
            distance_from_last=10.5,
            time_since_last=2.0,
            is_new_merchant=0,
            is_new_device=0,
            is_high_risk_country=0,
            channel_encoded=2,
            tx_type_encoded=0,
            timestamp=datetime.utcnow(),
        )

        arr = fv.to_feature_array()
        assert isinstance(arr, list)
        assert len(arr) == 18  # Number of features


class TestEMRClusterConfig:
    """Tests for EMRClusterConfig model."""

    def test_default_config(self):
        """Test default cluster configuration."""
        config = EMRClusterConfig(cluster_name="test-cluster")

        assert config.cluster_name == "test-cluster"
        assert config.release_label == "emr-7.0.0"
        assert config.master_instance_type == "m5.xlarge"
        assert config.core_instance_count == 2
        assert "Spark" in config.applications

    def test_custom_config(self):
        """Test custom cluster configuration."""
        config = EMRClusterConfig(
            cluster_name="custom-cluster",
            release_label="emr-6.15.0",
            master_instance_type="m5.2xlarge",
            core_instance_type="m5.4xlarge",
            core_instance_count=4,
            use_spot_instances=True,
            spot_bid_percentage=50,
        )

        assert config.master_instance_type == "m5.2xlarge"
        assert config.core_instance_count == 4
        assert config.use_spot_instances is True


class TestSparkJobConfig:
    """Tests for SparkJobConfig model."""

    def test_create_spark_job_config(self):
        """Test creating a Spark job configuration."""
        config = SparkJobConfig(
            job_name="feature-engineering",
            main_class="",
            jar_path="s3://bucket/jobs/feature_engineering.py",
            args=["--date", "2024-01-15"],
        )

        assert config.job_name == "feature-engineering"
        assert "--date" in config.args

    def test_spark_job_to_emr_step(self):
        """Test converting Spark job to EMR step."""
        config = SparkJobConfig(
            job_name="batch-scoring",
            main_class="",
            jar_path="s3://bucket/jobs/batch_scoring.py",
            args=["--model-version", "v1.0"],
            spark_config={"spark.sql.shuffle.partitions": "100"},
        )

        step = config.to_emr_step()

        assert step["Name"] == "batch-scoring"
        assert "HadoopJarStep" in step
        assert "Args" in step["HadoopJarStep"]
