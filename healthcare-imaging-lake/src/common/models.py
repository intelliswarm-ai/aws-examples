"""Data models for healthcare imaging data lake."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Modality(str, Enum):
    """Medical imaging modality types."""

    CT = "CT"
    MRI = "MRI"
    XRAY = "XRAY"
    ULTRASOUND = "ULTRASOUND"
    PET = "PET"
    MAMMOGRAPHY = "MAMMOGRAPHY"
    FLUOROSCOPY = "FLUOROSCOPY"
    NUCLEAR_MEDICINE = "NM"
    OTHER = "OTHER"


class BodyPart(str, Enum):
    """Body part examined in imaging study."""

    HEAD = "HEAD"
    NECK = "NECK"
    CHEST = "CHEST"
    ABDOMEN = "ABDOMEN"
    PELVIS = "PELVIS"
    SPINE = "SPINE"
    UPPER_EXTREMITY = "UPPER_EXTREMITY"
    LOWER_EXTREMITY = "LOWER_EXTREMITY"
    WHOLE_BODY = "WHOLE_BODY"
    OTHER = "OTHER"


class ImageFormat(str, Enum):
    """Image file format."""

    DICOM = "DICOM"
    PNG = "PNG"
    JPEG = "JPEG"
    NIFTI = "NIFTI"
    OTHER = "OTHER"


class AccessLevel(str, Enum):
    """Access level for Lake Formation permissions."""

    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    RESEARCHER = "RESEARCHER"
    AUDITOR = "AUDITOR"
    READ_ONLY = "READ_ONLY"


class QueryState(str, Enum):
    """Athena query execution state."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CrawlerStatus(str, Enum):
    """Glue crawler status."""

    READY = "READY"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"


class S3Location(BaseModel):
    """S3 location with bucket and prefix."""

    bucket: str
    prefix: str
    region: str | None = None

    @property
    def uri(self) -> str:
        """Get S3 URI."""
        return f"s3://{self.bucket}/{self.prefix}"

    @property
    def arn(self) -> str:
        """Get S3 ARN."""
        return f"arn:aws:s3:::{self.bucket}/{self.prefix}*"


class PartitionSpec(BaseModel):
    """Time-based partition specification."""

    year: str
    month: str
    day: str
    facility_id: str | None = None
    modality: str | None = None

    @property
    def path(self) -> str:
        """Get partition path for S3."""
        parts = [f"year={self.year}", f"month={self.month}", f"day={self.day}"]
        if self.facility_id:
            parts.insert(0, f"facility={self.facility_id}")
        if self.modality:
            parts.insert(1 if self.facility_id else 0, f"modality={self.modality}")
        return "/".join(parts)

    @classmethod
    def from_datetime(
        cls,
        dt: datetime,
        facility_id: str | None = None,
        modality: str | None = None,
    ) -> "PartitionSpec":
        """Create partition spec from datetime."""
        return cls(
            year=str(dt.year),
            month=f"{dt.month:02d}",
            day=f"{dt.day:02d}",
            facility_id=facility_id,
            modality=modality,
        )

    @property
    def partition_values(self) -> dict[str, str]:
        """Get partition values as dictionary."""
        values = {"year": self.year, "month": self.month, "day": self.day}
        if self.facility_id:
            values["facility"] = self.facility_id
        if self.modality:
            values["modality"] = self.modality
        return values


class ImageMetadata(BaseModel):
    """Medical image metadata record."""

    image_id: str = Field(default_factory=lambda: str(uuid4()))
    study_id: str
    series_id: str | None = None
    patient_id: str  # Encrypted/hashed reference
    modality: Modality
    body_part: BodyPart
    laterality: str | None = None  # LEFT, RIGHT, BILATERAL
    facility_id: str
    acquisition_date: datetime
    s3_uri: str
    file_size_bytes: int
    image_format: ImageFormat = ImageFormat.DICOM

    # DICOM-specific metadata
    pixel_spacing: list[float] | None = None
    slice_thickness: float | None = None
    rows: int | None = None
    columns: int | None = None
    bits_allocated: int | None = None
    dicom_tags: dict[str, Any] = Field(default_factory=dict)

    # Clinical linkage
    condition_codes: list[str] = Field(default_factory=list)  # ICD-10 codes

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    @property
    def partition(self) -> PartitionSpec:
        """Get partition spec for this image."""
        return PartitionSpec.from_datetime(
            self.acquisition_date,
            facility_id=self.facility_id,
            modality=self.modality.value,
        )


class ClinicalRecord(BaseModel):
    """Clinical record associated with imaging study."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str  # Encrypted/hashed reference
    study_id: str  # Links to ImageMetadata
    encounter_id: str | None = None
    diagnosis: str | None = None  # Primary diagnosis (PHI)
    condition_codes: list[str] = Field(default_factory=list)  # ICD-10 codes
    procedure_codes: list[str] = Field(default_factory=list)  # CPT codes
    physician_id: str | None = None
    facility_id: str
    record_date: datetime
    notes_summary: str | None = None  # De-identified summary (PHI)
    age_at_study: int | None = None
    sex: str | None = None

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    @property
    def partition(self) -> PartitionSpec:
        """Get partition spec for this record."""
        return PartitionSpec.from_datetime(
            self.record_date,
            facility_id=self.facility_id,
        )


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""

    success: bool
    records_processed: int = 0
    records_failed: int = 0
    s3_location: str | None = None
    partition: PartitionSpec | None = None
    errors: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QueryResult(BaseModel):
    """Result of an Athena query execution."""

    query_execution_id: str
    state: QueryState
    query: str | None = None
    database: str | None = None
    output_location: str | None = None
    execution_time_ms: int | None = None
    data_scanned_bytes: int | None = None
    result_count: int | None = None
    next_token: str | None = None
    error_message: str | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def data_scanned_gb(self) -> float:
        """Get data scanned in GB."""
        if self.data_scanned_bytes is None:
            return 0.0
        return self.data_scanned_bytes / (1024**3)

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate query cost at $5/TB scanned."""
        if self.data_scanned_bytes is None:
            return 0.0
        tb_scanned = self.data_scanned_bytes / (1024**4)
        return tb_scanned * 5.0


class CatalogEntry(BaseModel):
    """Glue Data Catalog table entry."""

    database: str
    table_name: str
    location: str
    columns: list[dict[str, str]] = Field(default_factory=list)
    partition_keys: list[str] = Field(default_factory=list)
    row_count: int | None = None
    size_bytes: int | None = None
    last_updated: datetime | None = None


class LakeFormationPermission(BaseModel):
    """Lake Formation permission grant."""

    principal_arn: str
    resource_type: str  # DATABASE, TABLE, COLUMN
    database: str
    table_name: str | None = None
    column_names: list[str] | None = None
    permissions: list[str]  # SELECT, INSERT, DELETE, etc.
    row_filter: str | None = None  # SQL expression for row-level security
    column_mask: dict[str, str] | None = None  # Column masking expressions


class CrawlerRun(BaseModel):
    """Glue crawler run information."""

    crawler_name: str
    status: CrawlerStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    tables_created: int = 0
    tables_updated: int = 0
    tables_deleted: int = 0
    error_message: str | None = None
