"""Configuration management for healthcare imaging data lake."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    # S3 Buckets
    images_bucket: str = Field(default="", alias="IMAGES_BUCKET")
    metadata_bucket: str = Field(default="", alias="METADATA_BUCKET")
    results_bucket: str = Field(default="", alias="RESULTS_BUCKET")

    # KMS Configuration
    kms_key_id: str = Field(default="", alias="KMS_KEY_ID")
    kms_key_arn: str = Field(default="", alias="KMS_KEY_ARN")

    # Glue Configuration
    glue_database: str = Field(default="healthcare_imaging", alias="GLUE_DATABASE")
    imaging_table: str = Field(default="imaging_metadata", alias="IMAGING_TABLE")
    clinical_table: str = Field(default="clinical_records", alias="CLINICAL_TABLE")
    glue_crawler_name: str = Field(default="imaging-crawler", alias="GLUE_CRAWLER_NAME")

    # Athena Configuration
    athena_workgroup: str = Field(default="healthcare_analytics", alias="ATHENA_WORKGROUP")
    athena_query_timeout: int = Field(default=300, alias="ATHENA_QUERY_TIMEOUT")
    athena_bytes_limit: int = Field(
        default=107374182400, alias="ATHENA_BYTES_LIMIT"  # 100 GB
    )

    # Lake Formation Configuration
    enable_lakeformation: bool = Field(default=True, alias="ENABLE_LAKEFORMATION")
    lakeformation_admin_arn: str = Field(default="", alias="LAKEFORMATION_ADMIN_ARN")

    # Application Configuration
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Ingestion Configuration
    max_image_size_bytes: int = Field(
        default=2147483648, alias="MAX_IMAGE_SIZE_BYTES"  # 2 GB
    )
    max_batch_size: int = Field(default=100, alias="MAX_BATCH_SIZE")

    # Partition Configuration
    partition_columns: list[str] = Field(
        default=["year", "month", "day"],
        alias="PARTITION_COLUMNS",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "prod"

    @property
    def images_bucket_arn(self) -> str:
        """Get ARN for images bucket."""
        return f"arn:aws:s3:::{self.images_bucket}"

    @property
    def metadata_bucket_arn(self) -> str:
        """Get ARN for metadata bucket."""
        return f"arn:aws:s3:::{self.metadata_bucket}"

    @property
    def results_bucket_arn(self) -> str:
        """Get ARN for results bucket."""
        return f"arn:aws:s3:::{self.results_bucket}"

    @property
    def athena_output_location(self) -> str:
        """Get S3 location for Athena query results."""
        return f"s3://{self.results_bucket}/athena-results/"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance for convenience
settings = get_settings()
