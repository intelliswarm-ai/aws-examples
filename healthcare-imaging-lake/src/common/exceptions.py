"""Custom exceptions for healthcare imaging data lake."""


class DataLakeError(Exception):
    """Base exception for healthcare imaging data lake."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        self.message = message
        self.error_code = error_code or "DATA_LAKE_ERROR"
        super().__init__(self.message)


class IngestionError(DataLakeError):
    """Exception raised during data ingestion."""

    def __init__(
        self,
        message: str,
        image_id: str | None = None,
        s3_key: str | None = None,
    ) -> None:
        self.image_id = image_id
        self.s3_key = s3_key
        super().__init__(message, "INGESTION_ERROR")


class ValidationError(DataLakeError):
    """Exception raised for data validation failures."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        self.field = field
        self.value = value
        super().__init__(message, "VALIDATION_ERROR")


class CatalogError(DataLakeError):
    """Exception raised for Glue Data Catalog operations."""

    def __init__(
        self,
        message: str,
        database: str | None = None,
        table_name: str | None = None,
    ) -> None:
        self.database = database
        self.table_name = table_name
        super().__init__(message, "CATALOG_ERROR")


class CrawlerError(CatalogError):
    """Exception raised for Glue crawler operations."""

    def __init__(
        self,
        message: str,
        crawler_name: str | None = None,
    ) -> None:
        self.crawler_name = crawler_name
        super().__init__(message)
        self.error_code = "CRAWLER_ERROR"


class QueryError(DataLakeError):
    """Exception raised for Athena query operations."""

    def __init__(
        self,
        message: str,
        query_execution_id: str | None = None,
        query: str | None = None,
    ) -> None:
        self.query_execution_id = query_execution_id
        self.query = query
        super().__init__(message, "QUERY_ERROR")


class QueryTimeoutError(QueryError):
    """Exception raised when Athena query times out."""

    def __init__(
        self,
        message: str,
        query_execution_id: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message, query_execution_id)
        self.error_code = "QUERY_TIMEOUT"


class AccessDeniedError(DataLakeError):
    """Exception raised for Lake Formation access denied."""

    def __init__(
        self,
        message: str,
        principal_arn: str | None = None,
        resource: str | None = None,
        action: str | None = None,
    ) -> None:
        self.principal_arn = principal_arn
        self.resource = resource
        self.action = action
        super().__init__(message, "ACCESS_DENIED")


class EncryptionError(DataLakeError):
    """Exception raised for KMS encryption operations."""

    def __init__(
        self,
        message: str,
        key_id: str | None = None,
        operation: str | None = None,
    ) -> None:
        self.key_id = key_id
        self.operation = operation
        super().__init__(message, "ENCRYPTION_ERROR")


class LakeFormationError(DataLakeError):
    """Exception raised for Lake Formation operations."""

    def __init__(
        self,
        message: str,
        resource: str | None = None,
        permission: str | None = None,
    ) -> None:
        self.resource = resource
        self.permission = permission
        super().__init__(message, "LAKE_FORMATION_ERROR")


class PermissionDeniedError(LakeFormationError):
    """Exception raised when Lake Formation permission is denied."""

    def __init__(
        self,
        message: str,
        principal_arn: str | None = None,
        table_name: str | None = None,
    ) -> None:
        self.principal_arn = principal_arn
        self.table_name = table_name
        super().__init__(message, table_name)
        self.error_code = "PERMISSION_DENIED"


class DataLocationError(LakeFormationError):
    """Exception raised for Lake Formation data location issues."""

    def __init__(
        self,
        message: str,
        s3_location: str | None = None,
    ) -> None:
        self.s3_location = s3_location
        super().__init__(message, s3_location)
        self.error_code = "DATA_LOCATION_ERROR"


class StorageError(DataLakeError):
    """Exception raised for S3 storage operations."""

    def __init__(
        self,
        message: str,
        bucket: str | None = None,
        key: str | None = None,
        operation: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.key = key
        self.operation = operation
        super().__init__(message, "STORAGE_ERROR")


class DICOMError(ValidationError):
    """Exception raised for DICOM validation errors."""

    def __init__(
        self,
        message: str,
        missing_tags: list[str] | None = None,
    ) -> None:
        self.missing_tags = missing_tags or []
        super().__init__(message, field="DICOM")
        self.error_code = "INVALID_DICOM"


class DuplicateError(DataLakeError):
    """Exception raised for duplicate records."""

    def __init__(
        self,
        message: str,
        image_id: str | None = None,
        existing_location: str | None = None,
    ) -> None:
        self.image_id = image_id
        self.existing_location = existing_location
        super().__init__(message, "DUPLICATE")
