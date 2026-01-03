"""Data models for EMR Spark Fraud Detection Pipeline.

This module defines all Pydantic models used throughout the fraud detection system,
including transaction data, feature vectors, predictions, and configuration objects.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class TransactionType(str, Enum):
    """Types of financial transactions."""

    PURCHASE = "PURCHASE"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    DEPOSIT = "DEPOSIT"


class TransactionChannel(str, Enum):
    """Transaction origination channels."""

    POS = "POS"
    ATM = "ATM"
    ONLINE = "ONLINE"
    MOBILE = "MOBILE"
    BRANCH = "BRANCH"
    PHONE = "PHONE"


class Currency(str, Enum):
    """Supported currencies (ISO 4217)."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"


class FraudStatus(str, Enum):
    """Fraud detection status."""

    PENDING = "PENDING"
    LEGITIMATE = "LEGITIMATE"
    SUSPICIOUS = "SUSPICIOUS"
    FRAUDULENT = "FRAUDULENT"
    REVIEW = "REVIEW"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    """Types of fraud alerts."""

    HIGH_VALUE = "HIGH_VALUE"
    VELOCITY = "VELOCITY"
    GEOGRAPHIC = "GEOGRAPHIC"
    PATTERN = "PATTERN"
    BLACKLIST = "BLACKLIST"
    BEHAVIORAL = "BEHAVIORAL"


class PipelineStatus(str, Enum):
    """ML pipeline execution status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EMRStepState(str, Enum):
    """EMR step execution states."""

    PENDING = "PENDING"
    CANCEL_PENDING = "CANCEL_PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class EMRClusterState(str, Enum):
    """EMR cluster states."""

    STARTING = "STARTING"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    TERMINATED_WITH_ERRORS = "TERMINATED_WITH_ERRORS"


class Location(BaseModel):
    """Geographic location information."""

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    country: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)

    def has_coordinates(self) -> bool:
        """Check if location has valid coordinates."""
        return self.latitude is not None and self.longitude is not None


class DeviceInfo(BaseModel):
    """Device information for transaction origin."""

    device_id: str | None = Field(default=None, max_length=64)
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)
    device_type: str | None = Field(default=None, max_length=50)
    os: str | None = Field(default=None, max_length=50)
    browser: str | None = Field(default=None, max_length=50)


class Transaction(BaseModel):
    """Financial transaction model.

    This is the primary input model for the fraud detection pipeline.
    Transactions are ingested via API Gateway and processed through
    the Kinesis stream to the Spark processing layer.
    """

    transaction_id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str = Field(..., min_length=8, max_length=20, description="Source account identifier")
    card_id: str | None = Field(default=None, max_length=20, description="Card used if applicable")
    merchant_id: str | None = Field(default=None, max_length=50, description="Merchant identifier")
    merchant_name: str | None = Field(default=None, max_length=200, description="Merchant name")
    merchant_category: str | None = Field(default=None, max_length=10, description="MCC code")
    transaction_type: TransactionType
    channel: TransactionChannel
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Transaction amount")
    currency: Currency = Currency.USD
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    location: Location = Field(default_factory=Location)
    device_info: DeviceInfo = Field(default_factory=DeviceInfo)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        """Validate account ID format."""
        if not v.replace("-", "").isalnum():
            raise ValueError("Account ID must be alphanumeric")
        return v

    def to_kinesis_record(self) -> dict[str, Any]:
        """Convert to Kinesis record format."""
        return {
            "Data": self.model_dump_json().encode("utf-8"),
            "PartitionKey": self.account_id,
        }

    def to_dynamodb_item(self) -> dict[str, dict[str, Any]]:
        """Convert to DynamoDB item format."""
        return {
            "transaction_id": {"S": self.transaction_id},
            "account_id": {"S": self.account_id},
            "amount": {"N": str(self.amount)},
            "currency": {"S": self.currency.value},
            "transaction_type": {"S": self.transaction_type.value},
            "channel": {"S": self.channel.value},
            "timestamp": {"S": self.timestamp.isoformat()},
            "ttl": {"N": str(int((self.timestamp.timestamp()) + 90 * 24 * 60 * 60))},
        }


class FeatureVector(BaseModel):
    """Feature vector for ML model input.

    Contains engineered features computed by the Spark feature engineering job.
    These features are used for both model training and inference.
    """

    transaction_id: str
    account_id: str

    # Transaction features
    amount: float = Field(..., ge=0)
    hour_of_day: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    is_weekend: bool = False

    # Velocity features (transaction counts in time windows)
    tx_count_1h: int = Field(default=0, ge=0)
    tx_count_6h: int = Field(default=0, ge=0)
    tx_count_24h: int = Field(default=0, ge=0)
    tx_count_7d: int = Field(default=0, ge=0)

    # Amount features (transaction amounts in time windows)
    tx_amount_1h: float = Field(default=0.0, ge=0)
    tx_amount_6h: float = Field(default=0.0, ge=0)
    tx_amount_24h: float = Field(default=0.0, ge=0)
    tx_amount_7d: float = Field(default=0.0, ge=0)

    # Pattern features (historical patterns)
    avg_amount_30d: float = Field(default=0.0, ge=0)
    std_amount_30d: float = Field(default=0.0, ge=0)
    max_amount_30d: float = Field(default=0.0, ge=0)
    min_amount_30d: float = Field(default=0.0, ge=0)

    # Merchant features
    unique_merchants_7d: int = Field(default=0, ge=0)
    unique_merchants_30d: int = Field(default=0, ge=0)
    merchant_tx_count: int = Field(default=0, ge=0)

    # Location features
    unique_locations_7d: int = Field(default=0, ge=0)
    unique_countries_30d: int = Field(default=0, ge=0)

    # Distance features
    distance_from_home: float = Field(default=0.0, ge=0, description="Distance in km")
    distance_from_last_tx: float = Field(default=0.0, ge=0, description="Distance in km")
    time_since_last_tx: float = Field(default=0.0, ge=0, description="Time in seconds")
    velocity_km_per_hour: float = Field(default=0.0, ge=0)

    # Risk indicators
    is_new_merchant: bool = False
    is_new_location: bool = False
    is_new_device: bool = False
    is_high_risk_mcc: bool = False
    is_high_risk_country: bool = False
    is_unusual_hour: bool = False
    is_amount_outlier: bool = False

    # Channel features
    channel_encoded: int = Field(default=0, ge=0, le=5)
    tx_type_encoded: int = Field(default=0, ge=0, le=5)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_feature_array(self) -> list[float]:
        """Convert to numeric feature array for ML model."""
        return [
            self.amount,
            float(self.hour_of_day),
            float(self.day_of_week),
            float(self.is_weekend),
            float(self.tx_count_1h),
            float(self.tx_count_6h),
            float(self.tx_count_24h),
            float(self.tx_count_7d),
            self.tx_amount_1h,
            self.tx_amount_6h,
            self.tx_amount_24h,
            self.tx_amount_7d,
            self.avg_amount_30d,
            self.std_amount_30d,
            self.max_amount_30d,
            float(self.unique_merchants_7d),
            float(self.unique_locations_7d),
            self.distance_from_home,
            self.distance_from_last_tx,
            self.time_since_last_tx,
            self.velocity_km_per_hour,
            float(self.is_new_merchant),
            float(self.is_new_location),
            float(self.is_new_device),
            float(self.is_high_risk_mcc),
            float(self.is_high_risk_country),
            float(self.is_unusual_hour),
            float(self.is_amount_outlier),
            float(self.channel_encoded),
            float(self.tx_type_encoded),
        ]


class FraudPrediction(BaseModel):
    """Fraud detection prediction result.

    Output from the ML model scoring process.
    """

    prediction_id: str = Field(default_factory=lambda: str(uuid4()))
    transaction_id: str
    account_id: str
    fraud_score: float = Field(..., ge=0.0, le=1.0, description="Probability of fraud")
    fraud_status: FraudStatus
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence")
    risk_factors: list[str] = Field(default_factory=list)
    model_version: str
    feature_importance: dict[str, float] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_score(
        cls,
        transaction_id: str,
        account_id: str,
        fraud_score: float,
        model_version: str,
        fraud_threshold: float = 0.7,
        suspicious_threshold: float = 0.5,
        risk_factors: list[str] | None = None,
    ) -> "FraudPrediction":
        """Create prediction from fraud score with automatic status assignment."""
        if fraud_score >= fraud_threshold:
            status = FraudStatus.FRAUDULENT
        elif fraud_score >= suspicious_threshold:
            status = FraudStatus.SUSPICIOUS
        else:
            status = FraudStatus.LEGITIMATE

        return cls(
            transaction_id=transaction_id,
            account_id=account_id,
            fraud_score=fraud_score,
            fraud_status=status,
            confidence=abs(fraud_score - 0.5) * 2,  # Higher confidence near 0 or 1
            risk_factors=risk_factors or [],
            model_version=model_version,
        )

    def to_dynamodb_item(self) -> dict[str, dict[str, Any]]:
        """Convert to DynamoDB item format."""
        item = {
            "prediction_id": {"S": self.prediction_id},
            "transaction_id": {"S": self.transaction_id},
            "account_id": {"S": self.account_id},
            "fraud_score": {"N": str(self.fraud_score)},
            "fraud_status": {"S": self.fraud_status.value},
            "confidence": {"N": str(self.confidence)},
            "model_version": {"S": self.model_version},
            "processed_at": {"S": self.processed_at.isoformat()},
            "ttl": {"N": str(int(self.processed_at.timestamp() + 365 * 24 * 60 * 60))},
        }
        if self.risk_factors:
            item["risk_factors"] = {"SS": self.risk_factors}
        return item


class FraudAlert(BaseModel):
    """High-priority fraud alert for immediate action.

    Generated when a transaction is flagged as fraudulent or suspicious.
    """

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    transaction_id: str
    account_id: str
    fraud_score: float = Field(..., ge=0.0, le=1.0)
    alert_type: AlertType
    severity: AlertSeverity
    message: str = Field(..., max_length=500)
    recommended_action: str = Field(..., max_length=200)
    transaction_amount: Decimal | None = None
    merchant_name: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None

    @classmethod
    def from_prediction(
        cls,
        prediction: FraudPrediction,
        transaction: Transaction,
        alert_type: AlertType = AlertType.PATTERN,
    ) -> "FraudAlert":
        """Create alert from prediction and transaction."""
        if prediction.fraud_score >= 0.9:
            severity = AlertSeverity.CRITICAL
            action = "Block transaction and contact customer immediately"
        elif prediction.fraud_score >= 0.8:
            severity = AlertSeverity.HIGH
            action = "Block transaction and send verification request"
        elif prediction.fraud_score >= 0.7:
            severity = AlertSeverity.MEDIUM
            action = "Flag for manual review within 1 hour"
        else:
            severity = AlertSeverity.LOW
            action = "Monitor account activity"

        risk_summary = ", ".join(prediction.risk_factors[:3]) if prediction.risk_factors else "Unknown"

        return cls(
            transaction_id=prediction.transaction_id,
            account_id=prediction.account_id,
            fraud_score=prediction.fraud_score,
            alert_type=alert_type,
            severity=severity,
            message=f"Potential fraud detected: {risk_summary}. Score: {prediction.fraud_score:.2f}",
            recommended_action=action,
            transaction_amount=transaction.amount,
            merchant_name=transaction.merchant_name,
        )

    def to_dynamodb_item(self) -> dict[str, dict[str, Any]]:
        """Convert to DynamoDB item format."""
        item = {
            "alert_id": {"S": self.alert_id},
            "transaction_id": {"S": self.transaction_id},
            "account_id": {"S": self.account_id},
            "fraud_score": {"N": str(self.fraud_score)},
            "alert_type": {"S": self.alert_type.value},
            "severity": {"S": self.severity.value},
            "message": {"S": self.message},
            "recommended_action": {"S": self.recommended_action},
            "created_at": {"S": self.created_at.isoformat()},
            "acknowledged": {"BOOL": self.acknowledged},
            "ttl": {"N": str(int(self.created_at.timestamp() + 90 * 24 * 60 * 60))},
        }
        if self.transaction_amount:
            item["transaction_amount"] = {"N": str(self.transaction_amount)}
        if self.merchant_name:
            item["merchant_name"] = {"S": self.merchant_name}
        return item

    def to_sns_message(self) -> dict[str, Any]:
        """Convert to SNS message format."""
        return {
            "default": self.message,
            "email": (
                f"FRAUD ALERT [{self.severity.value}]\n\n"
                f"Transaction ID: {self.transaction_id}\n"
                f"Account ID: {self.account_id}\n"
                f"Fraud Score: {self.fraud_score:.2f}\n"
                f"Alert Type: {self.alert_type.value}\n"
                f"Amount: {self.transaction_amount or 'N/A'}\n"
                f"Merchant: {self.merchant_name or 'N/A'}\n\n"
                f"Recommended Action: {self.recommended_action}\n\n"
                f"Time: {self.created_at.isoformat()}"
            ),
            "sms": f"FRAUD ALERT: Account {self.account_id[-4:]} - Score {self.fraud_score:.0%} - {self.recommended_action}",
        }


class EMRClusterConfig(BaseModel):
    """EMR cluster configuration for Spark jobs."""

    cluster_name: str = Field(..., min_length=1, max_length=256)
    release_label: str = "emr-7.0.0"
    log_uri: str = Field(..., description="S3 URI for EMR logs")
    subnet_id: str = Field(..., description="Subnet for EMR cluster")

    # Instance configuration
    master_instance_type: str = "m5.xlarge"
    core_instance_type: str = "m5.2xlarge"
    core_instance_count: int = Field(default=2, ge=1, le=50)
    task_instance_type: str | None = "m5.2xlarge"
    task_instance_count: int = Field(default=0, ge=0, le=100)

    # Spot configuration
    use_spot_instances: bool = True
    spot_bid_percentage: int = Field(default=50, ge=1, le=100)

    # Cluster behavior
    auto_terminate: bool = True
    keep_job_flow_alive: bool = False
    termination_protected: bool = False
    idle_timeout_seconds: int = Field(default=3600, ge=300)

    # Applications
    applications: list[str] = Field(default_factory=lambda: ["Spark", "Hadoop", "Hive"])

    # Tags
    tags: dict[str, str] = Field(default_factory=dict)


class SparkJobConfig(BaseModel):
    """Spark job submission configuration."""

    job_name: str = Field(..., min_length=1, max_length=256)
    script_location: str = Field(..., description="S3 URI for Spark script")
    arguments: list[str] = Field(default_factory=list)

    # Spark configuration
    spark_config: dict[str, str] = Field(default_factory=dict)
    driver_memory: str = "4g"
    driver_cores: int = Field(default=2, ge=1)
    executor_memory: str = "8g"
    executor_cores: int = Field(default=4, ge=1)
    num_executors: int = Field(default=4, ge=1)
    dynamic_allocation: bool = True

    # Job behavior
    action_on_failure: str = "CONTINUE"  # TERMINATE_CLUSTER, CANCEL_AND_WAIT, CONTINUE

    def to_emr_step(self) -> dict[str, Any]:
        """Convert to EMR step format."""
        spark_submit_args = [
            "spark-submit",
            "--deploy-mode",
            "cluster",
            "--driver-memory",
            self.driver_memory,
            "--driver-cores",
            str(self.driver_cores),
            "--executor-memory",
            self.executor_memory,
            "--executor-cores",
            str(self.executor_cores),
        ]

        if not self.dynamic_allocation:
            spark_submit_args.extend(["--num-executors", str(self.num_executors)])

        for key, value in self.spark_config.items():
            spark_submit_args.extend(["--conf", f"{key}={value}"])

        spark_submit_args.append(self.script_location)
        spark_submit_args.extend(self.arguments)

        return {
            "Name": self.job_name,
            "ActionOnFailure": self.action_on_failure,
            "HadoopJarStep": {
                "Jar": "command-runner.jar",
                "Args": spark_submit_args,
            },
        }


class PipelineExecution(BaseModel):
    """ML pipeline execution tracking."""

    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    pipeline_name: str
    execution_mode: str = "FULL"  # FULL, TRAINING_ONLY, SCORING_ONLY
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # EMR tracking
    emr_cluster_id: str | None = None
    step_ids: list[str] = Field(default_factory=list)

    # Data locations
    input_location: str | None = None
    output_location: str | None = None
    model_location: str | None = None

    # Metrics
    metrics: dict[str, Any] = Field(default_factory=dict)
    transactions_processed: int = 0
    fraud_detected: int = 0
    suspicious_detected: int = 0

    # Error handling
    error_message: str | None = None
    error_details: dict[str, Any] = Field(default_factory=dict)

    def mark_completed(self, success: bool = True, error_message: str | None = None) -> None:
        """Mark pipeline as completed."""
        self.completed_at = datetime.utcnow()
        self.status = PipelineStatus.SUCCEEDED if success else PipelineStatus.FAILED
        if error_message:
            self.error_message = error_message

    def to_dynamodb_item(self) -> dict[str, dict[str, Any]]:
        """Convert to DynamoDB item format."""
        item = {
            "execution_id": {"S": self.execution_id},
            "pipeline_name": {"S": self.pipeline_name},
            "execution_mode": {"S": self.execution_mode},
            "status": {"S": self.status.value},
            "started_at": {"S": self.started_at.isoformat()},
            "transactions_processed": {"N": str(self.transactions_processed)},
            "fraud_detected": {"N": str(self.fraud_detected)},
            "suspicious_detected": {"N": str(self.suspicious_detected)},
        }
        if self.completed_at:
            item["completed_at"] = {"S": self.completed_at.isoformat()}
        if self.emr_cluster_id:
            item["emr_cluster_id"] = {"S": self.emr_cluster_id}
        if self.error_message:
            item["error_message"] = {"S": self.error_message}
        return item


class ModelMetrics(BaseModel):
    """ML model performance metrics."""

    model_version: str
    trained_at: datetime = Field(default_factory=datetime.utcnow)

    # Classification metrics
    auc_roc: float = Field(..., ge=0.0, le=1.0)
    auc_pr: float = Field(..., ge=0.0, le=1.0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)

    # Dataset info
    training_samples: int = Field(..., ge=0)
    validation_samples: int = Field(..., ge=0)
    test_samples: int = Field(..., ge=0)
    fraud_ratio: float = Field(..., ge=0.0, le=1.0)

    # Feature importance (top 10)
    feature_importance: dict[str, float] = Field(default_factory=dict)

    # Threshold analysis
    optimal_threshold: float = Field(..., ge=0.0, le=1.0)
    threshold_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)


class StreamingCheckpoint(BaseModel):
    """Checkpoint state for Spark Structured Streaming."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    stream_name: str
    shard_id: str
    sequence_number: str
    sub_sequence_number: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    records_processed: int = 0


class IngestionRequest(BaseModel):
    """API request for transaction ingestion."""

    transactions: list[Transaction] = Field(..., min_length=1, max_length=500)
    batch_id: str | None = Field(default=None, description="Optional batch identifier")
    callback_url: str | None = Field(default=None, description="Webhook for async results")


class IngestionResponse(BaseModel):
    """API response for transaction ingestion."""

    success: bool
    batch_id: str
    transactions_accepted: int
    transactions_rejected: int
    rejected_ids: list[str] = Field(default_factory=list)
    message: str


class QueryRequest(BaseModel):
    """API request for querying fraud results."""

    account_id: str | None = None
    transaction_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    fraud_status: FraudStatus | None = None
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    limit: int = Field(default=100, ge=1, le=1000)


class QueryResponse(BaseModel):
    """API response for fraud query results."""

    predictions: list[FraudPrediction]
    total_count: int
    has_more: bool
    next_token: str | None = None
