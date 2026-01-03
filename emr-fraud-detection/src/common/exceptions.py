"""Custom exceptions for EMR Spark Fraud Detection Pipeline.

This module defines a hierarchy of custom exceptions used throughout the
fraud detection system for specific error handling and reporting.
"""

from typing import Any


class FraudDetectionError(Exception):
    """Base exception for all fraud detection errors.

    All custom exceptions in this module inherit from this base class,
    allowing for catch-all error handling when needed.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code or "FRAUD_DETECTION_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# Kinesis Exceptions


class KinesisError(FraudDetectionError):
    """Base exception for Kinesis-related errors."""

    def __init__(
        self,
        message: str,
        stream_name: str | None = None,
        shard_id: str | None = None,
    ) -> None:
        details = {}
        if stream_name:
            details["stream_name"] = stream_name
        if shard_id:
            details["shard_id"] = shard_id
        super().__init__(message, error_code="KINESIS_ERROR", details=details)
        self.stream_name = stream_name
        self.shard_id = shard_id


class KinesisStreamNotFoundError(KinesisError):
    """Raised when a Kinesis stream is not found."""

    def __init__(self, stream_name: str) -> None:
        super().__init__(
            message=f"Kinesis stream not found: {stream_name}",
            stream_name=stream_name,
        )
        self.error_code = "KINESIS_STREAM_NOT_FOUND"


class KinesisPutRecordError(KinesisError):
    """Raised when putting records to Kinesis fails."""

    def __init__(
        self,
        message: str,
        stream_name: str,
        failed_count: int = 0,
    ) -> None:
        super().__init__(message=message, stream_name=stream_name)
        self.error_code = "KINESIS_PUT_RECORD_ERROR"
        self.failed_count = failed_count
        self.details["failed_count"] = failed_count


class KinesisThrottlingError(KinesisError):
    """Raised when Kinesis requests are throttled."""

    def __init__(self, stream_name: str, shard_id: str | None = None) -> None:
        super().__init__(
            message=f"Kinesis throughput exceeded for stream: {stream_name}",
            stream_name=stream_name,
            shard_id=shard_id,
        )
        self.error_code = "KINESIS_THROTTLING"


# EMR Exceptions


class EMRError(FraudDetectionError):
    """Base exception for EMR-related errors."""

    def __init__(
        self,
        message: str,
        cluster_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        details = {}
        if cluster_id:
            details["cluster_id"] = cluster_id
        if step_id:
            details["step_id"] = step_id
        super().__init__(message, error_code="EMR_ERROR", details=details)
        self.cluster_id = cluster_id
        self.step_id = step_id


class ClusterCreationError(EMRError):
    """Raised when EMR cluster creation fails."""

    def __init__(self, message: str, cluster_name: str) -> None:
        super().__init__(message=message)
        self.error_code = "CLUSTER_CREATION_ERROR"
        self.cluster_name = cluster_name
        self.details["cluster_name"] = cluster_name


class ClusterNotFoundError(EMRError):
    """Raised when an EMR cluster is not found."""

    def __init__(self, cluster_id: str) -> None:
        super().__init__(
            message=f"EMR cluster not found: {cluster_id}",
            cluster_id=cluster_id,
        )
        self.error_code = "CLUSTER_NOT_FOUND"


class ClusterTerminationError(EMRError):
    """Raised when EMR cluster termination fails."""

    def __init__(self, cluster_id: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to terminate cluster {cluster_id}: {reason}",
            cluster_id=cluster_id,
        )
        self.error_code = "CLUSTER_TERMINATION_ERROR"
        self.reason = reason
        self.details["reason"] = reason


class StepSubmissionError(EMRError):
    """Raised when submitting an EMR step fails."""

    def __init__(
        self,
        message: str,
        cluster_id: str,
        step_name: str,
    ) -> None:
        super().__init__(message=message, cluster_id=cluster_id)
        self.error_code = "STEP_SUBMISSION_ERROR"
        self.step_name = step_name
        self.details["step_name"] = step_name


class StepExecutionError(EMRError):
    """Raised when an EMR step execution fails."""

    def __init__(
        self,
        message: str,
        cluster_id: str,
        step_id: str,
        step_state: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        super().__init__(message=message, cluster_id=cluster_id, step_id=step_id)
        self.error_code = "STEP_EXECUTION_ERROR"
        self.step_state = step_state
        self.failure_reason = failure_reason
        if step_state:
            self.details["step_state"] = step_state
        if failure_reason:
            self.details["failure_reason"] = failure_reason


class StepTimeoutError(EMRError):
    """Raised when an EMR step exceeds timeout."""

    def __init__(
        self,
        cluster_id: str,
        step_id: str,
        timeout_seconds: int,
    ) -> None:
        super().__init__(
            message=f"Step {step_id} timed out after {timeout_seconds} seconds",
            cluster_id=cluster_id,
            step_id=step_id,
        )
        self.error_code = "STEP_TIMEOUT"
        self.timeout_seconds = timeout_seconds
        self.details["timeout_seconds"] = timeout_seconds


# Model Exceptions


class ModelError(FraudDetectionError):
    """Base exception for ML model errors."""

    def __init__(
        self,
        message: str,
        model_version: str | None = None,
    ) -> None:
        details = {}
        if model_version:
            details["model_version"] = model_version
        super().__init__(message, error_code="MODEL_ERROR", details=details)
        self.model_version = model_version


class ModelNotFoundError(ModelError):
    """Raised when an ML model is not found."""

    def __init__(self, model_version: str, model_path: str | None = None) -> None:
        super().__init__(
            message=f"Model version {model_version} not found",
            model_version=model_version,
        )
        self.error_code = "MODEL_NOT_FOUND"
        self.model_path = model_path
        if model_path:
            self.details["model_path"] = model_path


class ModelLoadError(ModelError):
    """Raised when loading an ML model fails."""

    def __init__(self, model_version: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to load model {model_version}: {reason}",
            model_version=model_version,
        )
        self.error_code = "MODEL_LOAD_ERROR"
        self.reason = reason
        self.details["reason"] = reason


class ModelValidationError(ModelError):
    """Raised when model validation fails."""

    def __init__(self, model_version: str, validation_errors: list[str]) -> None:
        super().__init__(
            message=f"Model {model_version} validation failed",
            model_version=model_version,
        )
        self.error_code = "MODEL_VALIDATION_ERROR"
        self.validation_errors = validation_errors
        self.details["validation_errors"] = validation_errors


class ModelTrainingError(ModelError):
    """Raised when model training fails."""

    def __init__(self, model_version: str, stage: str, reason: str) -> None:
        super().__init__(
            message=f"Training failed at {stage}: {reason}",
            model_version=model_version,
        )
        self.error_code = "MODEL_TRAINING_ERROR"
        self.stage = stage
        self.reason = reason
        self.details["stage"] = stage
        self.details["reason"] = reason


# Feature Engineering Exceptions


class FeatureEngineeringError(FraudDetectionError):
    """Base exception for feature engineering errors."""

    def __init__(
        self,
        message: str,
        transaction_id: str | None = None,
        feature_name: str | None = None,
    ) -> None:
        details = {}
        if transaction_id:
            details["transaction_id"] = transaction_id
        if feature_name:
            details["feature_name"] = feature_name
        super().__init__(message, error_code="FEATURE_ENGINEERING_ERROR", details=details)
        self.transaction_id = transaction_id
        self.feature_name = feature_name


class FeatureComputationError(FeatureEngineeringError):
    """Raised when computing a specific feature fails."""

    def __init__(
        self,
        feature_name: str,
        reason: str,
        transaction_id: str | None = None,
    ) -> None:
        super().__init__(
            message=f"Failed to compute feature {feature_name}: {reason}",
            transaction_id=transaction_id,
            feature_name=feature_name,
        )
        self.error_code = "FEATURE_COMPUTATION_ERROR"
        self.reason = reason
        self.details["reason"] = reason


class FeatureValidationError(FeatureEngineeringError):
    """Raised when feature validation fails."""

    def __init__(
        self,
        transaction_id: str,
        validation_errors: list[str],
    ) -> None:
        super().__init__(
            message=f"Feature validation failed for transaction {transaction_id}",
            transaction_id=transaction_id,
        )
        self.error_code = "FEATURE_VALIDATION_ERROR"
        self.validation_errors = validation_errors
        self.details["validation_errors"] = validation_errors


# Pipeline Exceptions


class PipelineError(FraudDetectionError):
    """Base exception for ML pipeline errors."""

    def __init__(
        self,
        message: str,
        execution_id: str | None = None,
        pipeline_name: str | None = None,
    ) -> None:
        details = {}
        if execution_id:
            details["execution_id"] = execution_id
        if pipeline_name:
            details["pipeline_name"] = pipeline_name
        super().__init__(message, error_code="PIPELINE_ERROR", details=details)
        self.execution_id = execution_id
        self.pipeline_name = pipeline_name


class PipelineExecutionError(PipelineError):
    """Raised when pipeline execution fails."""

    def __init__(
        self,
        execution_id: str,
        stage: str,
        reason: str,
    ) -> None:
        super().__init__(
            message=f"Pipeline execution {execution_id} failed at {stage}: {reason}",
            execution_id=execution_id,
        )
        self.error_code = "PIPELINE_EXECUTION_ERROR"
        self.stage = stage
        self.reason = reason
        self.details["stage"] = stage
        self.details["reason"] = reason


class PipelineValidationError(PipelineError):
    """Raised when pipeline input validation fails."""

    def __init__(
        self,
        pipeline_name: str,
        validation_errors: list[str],
    ) -> None:
        super().__init__(
            message=f"Pipeline {pipeline_name} validation failed",
            pipeline_name=pipeline_name,
        )
        self.error_code = "PIPELINE_VALIDATION_ERROR"
        self.validation_errors = validation_errors
        self.details["validation_errors"] = validation_errors


# Alert Exceptions


class AlertError(FraudDetectionError):
    """Base exception for alert-related errors."""

    def __init__(
        self,
        message: str,
        alert_id: str | None = None,
    ) -> None:
        details = {}
        if alert_id:
            details["alert_id"] = alert_id
        super().__init__(message, error_code="ALERT_ERROR", details=details)
        self.alert_id = alert_id


class AlertCreationError(AlertError):
    """Raised when creating an alert fails."""

    def __init__(self, transaction_id: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to create alert for transaction {transaction_id}: {reason}",
        )
        self.error_code = "ALERT_CREATION_ERROR"
        self.transaction_id = transaction_id
        self.reason = reason
        self.details["transaction_id"] = transaction_id
        self.details["reason"] = reason


class AlertNotificationError(AlertError):
    """Raised when sending alert notification fails."""

    def __init__(self, alert_id: str, channel: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to send alert {alert_id} via {channel}: {reason}",
            alert_id=alert_id,
        )
        self.error_code = "ALERT_NOTIFICATION_ERROR"
        self.channel = channel
        self.reason = reason
        self.details["channel"] = channel
        self.details["reason"] = reason


# Storage Exceptions


class StorageError(FraudDetectionError):
    """Base exception for storage-related errors."""

    def __init__(
        self,
        message: str,
        storage_type: str | None = None,
        resource: str | None = None,
    ) -> None:
        details = {}
        if storage_type:
            details["storage_type"] = storage_type
        if resource:
            details["resource"] = resource
        super().__init__(message, error_code="STORAGE_ERROR", details=details)
        self.storage_type = storage_type
        self.resource = resource


class S3Error(StorageError):
    """Raised for S3-related errors."""

    def __init__(
        self,
        message: str,
        bucket: str | None = None,
        key: str | None = None,
    ) -> None:
        resource = None
        if bucket and key:
            resource = f"s3://{bucket}/{key}"
        elif bucket:
            resource = f"s3://{bucket}"
        super().__init__(message, storage_type="S3", resource=resource)
        self.error_code = "S3_ERROR"
        self.bucket = bucket
        self.key = key


class DynamoDBError(StorageError):
    """Raised for DynamoDB-related errors."""

    def __init__(
        self,
        message: str,
        table_name: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, storage_type="DynamoDB", resource=table_name)
        self.error_code = "DYNAMODB_ERROR"
        self.table_name = table_name
        self.operation = operation
        if operation:
            self.details["operation"] = operation


# Validation Exceptions


class ValidationError(FraudDetectionError):
    """Raised for input validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)
        self.field = field
        self.value = value


class TransactionValidationError(ValidationError):
    """Raised when transaction validation fails."""

    def __init__(
        self,
        transaction_id: str | None,
        errors: list[str],
    ) -> None:
        super().__init__(
            message=f"Transaction validation failed: {'; '.join(errors)}",
        )
        self.error_code = "TRANSACTION_VALIDATION_ERROR"
        self.transaction_id = transaction_id
        self.errors = errors
        self.details["transaction_id"] = transaction_id
        self.details["errors"] = errors


# Rate Limiting Exceptions


class RateLimitError(FraudDetectionError):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        super().__init__(message, error_code="RATE_LIMIT_ERROR")
        self.limit = limit
        self.window_seconds = window_seconds
        self.details["limit"] = limit
        self.details["window_seconds"] = window_seconds
