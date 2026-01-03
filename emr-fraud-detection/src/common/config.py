"""Configuration settings for EMR Spark Fraud Detection Pipeline.

This module provides centralized configuration management using Pydantic Settings,
loading values from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    Variable names are case-insensitive and use the alias if provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_account_id: str = Field(default="", alias="AWS_ACCOUNT_ID")

    # Project Configuration
    project_name: str = Field(default="emr-fraud-detection", alias="PROJECT_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    service_name: str = Field(default="fraud-detection", alias="SERVICE_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Kinesis Configuration
    kinesis_stream_name: str = Field(default="", alias="KINESIS_STREAM_NAME")
    kinesis_stream_arn: str = Field(default="", alias="KINESIS_STREAM_ARN")
    kinesis_shard_count: int = Field(default=4, alias="KINESIS_SHARD_COUNT")
    kinesis_batch_size: int = Field(default=100, alias="KINESIS_BATCH_SIZE")
    kinesis_starting_position: str = Field(default="LATEST", alias="KINESIS_STARTING_POSITION")

    # S3 Configuration
    raw_bucket: str = Field(default="", alias="RAW_BUCKET")
    features_bucket: str = Field(default="", alias="FEATURES_BUCKET")
    models_bucket: str = Field(default="", alias="MODELS_BUCKET")
    predictions_bucket: str = Field(default="", alias="PREDICTIONS_BUCKET")
    scripts_bucket: str = Field(default="", alias="SCRIPTS_BUCKET")
    logs_bucket: str = Field(default="", alias="LOGS_BUCKET")

    # S3 Prefixes
    raw_prefix: str = Field(default="raw/transactions", alias="RAW_PREFIX")
    features_prefix: str = Field(default="features", alias="FEATURES_PREFIX")
    models_prefix: str = Field(default="models", alias="MODELS_PREFIX")
    predictions_prefix: str = Field(default="predictions", alias="PREDICTIONS_PREFIX")
    checkpoints_prefix: str = Field(default="checkpoints", alias="CHECKPOINTS_PREFIX")

    # EMR Configuration
    emr_release_label: str = Field(default="emr-7.0.0", alias="EMR_RELEASE_LABEL")
    emr_master_instance_type: str = Field(default="m5.xlarge", alias="EMR_MASTER_INSTANCE_TYPE")
    emr_core_instance_type: str = Field(default="m5.2xlarge", alias="EMR_CORE_INSTANCE_TYPE")
    emr_core_instance_count: int = Field(default=2, alias="EMR_CORE_INSTANCE_COUNT")
    emr_task_instance_type: str = Field(default="m5.2xlarge", alias="EMR_TASK_INSTANCE_TYPE")
    emr_task_instance_count: int = Field(default=0, alias="EMR_TASK_INSTANCE_COUNT")
    emr_subnet_id: str = Field(default="", alias="EMR_SUBNET_ID")
    emr_log_uri: str = Field(default="", alias="EMR_LOG_URI")
    emr_service_role: str = Field(default="EMR_DefaultRole", alias="EMR_SERVICE_ROLE")
    emr_ec2_role: str = Field(default="EMR_EC2_DefaultRole", alias="EMR_EC2_ROLE")
    emr_use_spot: bool = Field(default=True, alias="EMR_USE_SPOT")
    emr_spot_bid_percentage: int = Field(default=50, alias="EMR_SPOT_BID_PERCENTAGE")
    emr_idle_timeout: int = Field(default=3600, alias="EMR_IDLE_TIMEOUT")

    # Streaming EMR Configuration (for real-time scoring)
    streaming_cluster_id: str = Field(default="", alias="STREAMING_CLUSTER_ID")
    streaming_enabled: bool = Field(default=True, alias="STREAMING_ENABLED")

    # DynamoDB Configuration
    alerts_table_name: str = Field(default="", alias="ALERTS_TABLE_NAME")
    predictions_table_name: str = Field(default="", alias="PREDICTIONS_TABLE_NAME")
    executions_table_name: str = Field(default="", alias="EXECUTIONS_TABLE_NAME")
    dynamodb_ttl_days: int = Field(default=90, alias="DYNAMODB_TTL_DAYS")

    # SNS Configuration
    fraud_alerts_topic_arn: str = Field(default="", alias="FRAUD_ALERTS_TOPIC_ARN")
    pipeline_notifications_topic_arn: str = Field(default="", alias="PIPELINE_NOTIFICATIONS_TOPIC_ARN")

    # Step Functions Configuration
    pipeline_state_machine_arn: str = Field(default="", alias="PIPELINE_STATE_MACHINE_ARN")

    # VPC Configuration
    vpc_id: str = Field(default="", alias="VPC_ID")
    private_subnet_ids: str = Field(default="", alias="PRIVATE_SUBNET_IDS")
    security_group_ids: str = Field(default="", alias="SECURITY_GROUP_IDS")

    # ML Configuration
    model_version: str = Field(default="v1.0", alias="MODEL_VERSION")
    fraud_threshold: float = Field(default=0.7, alias="FRAUD_THRESHOLD")
    suspicious_threshold: float = Field(default=0.5, alias="SUSPICIOUS_THRESHOLD")
    model_s3_path: str = Field(default="", alias="MODEL_S3_PATH")

    # Feature Engineering Configuration
    feature_window_1h: int = Field(default=3600, alias="FEATURE_WINDOW_1H")
    feature_window_6h: int = Field(default=21600, alias="FEATURE_WINDOW_6H")
    feature_window_24h: int = Field(default=86400, alias="FEATURE_WINDOW_24H")
    feature_window_7d: int = Field(default=604800, alias="FEATURE_WINDOW_7D")
    feature_window_30d: int = Field(default=2592000, alias="FEATURE_WINDOW_30D")

    # High-risk configurations
    high_risk_mcc_codes: str = Field(
        default="5912,5122,5962,5966,5967,7995",
        alias="HIGH_RISK_MCC_CODES",
    )
    high_risk_countries: str = Field(default="", alias="HIGH_RISK_COUNTRIES")
    unusual_hours_start: int = Field(default=0, alias="UNUSUAL_HOURS_START")
    unusual_hours_end: int = Field(default=5, alias="UNUSUAL_HOURS_END")

    # API Configuration
    api_rate_limit: int = Field(default=1000, alias="API_RATE_LIMIT")
    api_burst_limit: int = Field(default=2000, alias="API_BURST_LIMIT")
    api_timeout_seconds: int = Field(default=30, alias="API_TIMEOUT_SECONDS")

    # Processing Configuration
    batch_processing_enabled: bool = Field(default=True, alias="BATCH_PROCESSING_ENABLED")
    batch_schedule: str = Field(default="rate(1 hour)", alias="BATCH_SCHEDULE")
    max_batch_size: int = Field(default=10000, alias="MAX_BATCH_SIZE")

    @property
    def high_risk_mcc_list(self) -> list[str]:
        """Get high-risk MCC codes as a list."""
        return [code.strip() for code in self.high_risk_mcc_codes.split(",") if code.strip()]

    @property
    def high_risk_country_list(self) -> list[str]:
        """Get high-risk countries as a list."""
        return [c.strip() for c in self.high_risk_countries.split(",") if c.strip()]

    @property
    def private_subnet_list(self) -> list[str]:
        """Get private subnet IDs as a list."""
        return [s.strip() for s in self.private_subnet_ids.split(",") if s.strip()]

    @property
    def security_group_list(self) -> list[str]:
        """Get security group IDs as a list."""
        return [s.strip() for s in self.security_group_ids.split(",") if s.strip()]

    def get_s3_raw_path(self, partition: str = "") -> str:
        """Get S3 path for raw data."""
        path = f"s3://{self.raw_bucket}/{self.raw_prefix}"
        if partition:
            path = f"{path}/{partition}"
        return path

    def get_s3_features_path(self, partition: str = "") -> str:
        """Get S3 path for feature data."""
        path = f"s3://{self.features_bucket}/{self.features_prefix}"
        if partition:
            path = f"{path}/{partition}"
        return path

    def get_s3_model_path(self, version: str | None = None) -> str:
        """Get S3 path for ML model."""
        version = version or self.model_version
        return f"s3://{self.models_bucket}/{self.models_prefix}/{version}"

    def get_s3_predictions_path(self, partition: str = "") -> str:
        """Get S3 path for predictions."""
        path = f"s3://{self.predictions_bucket}/{self.predictions_prefix}"
        if partition:
            path = f"{path}/{partition}"
        return path

    def get_s3_checkpoint_path(self, stream_name: str) -> str:
        """Get S3 path for streaming checkpoint."""
        return f"s3://{self.predictions_bucket}/{self.checkpoints_prefix}/{stream_name}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once
    and reused across the application.
    """
    return Settings()


# Global settings instance for convenient imports
settings = get_settings()
