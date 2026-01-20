"""Services for healthcare imaging data lake."""

from src.services.athena_service import AthenaService
from src.services.glue_service import GlueService
from src.services.kms_service import KMSService
from src.services.lakeformation_service import LakeFormationService
from src.services.s3_service import S3Service

__all__ = [
    "S3Service",
    "KMSService",
    "GlueService",
    "LakeFormationService",
    "AthenaService",
]


def get_s3_service() -> S3Service:
    """Factory function for S3Service."""
    return S3Service()


def get_kms_service() -> KMSService:
    """Factory function for KMSService."""
    return KMSService()


def get_glue_service() -> GlueService:
    """Factory function for GlueService."""
    return GlueService()


def get_lakeformation_service() -> LakeFormationService:
    """Factory function for LakeFormationService."""
    return LakeFormationService()


def get_athena_service() -> AthenaService:
    """Factory function for AthenaService."""
    return AthenaService()
