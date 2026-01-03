"""Lambda handlers for EMR Spark Fraud Detection Pipeline."""

from .alert_handler import handler as alert_handler
from .ingestion_handler import handler as ingestion_handler
from .orchestration_handler import handler as orchestration_handler
from .query_handler import handler as query_handler
from .stream_processor import handler as stream_processor_handler

__all__ = [
    "alert_handler",
    "ingestion_handler",
    "orchestration_handler",
    "query_handler",
    "stream_processor_handler",
]
