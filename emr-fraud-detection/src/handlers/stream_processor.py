"""Stream Processor Handler.

This Lambda function processes transactions from Kinesis Data Streams
and writes them to S3 in partitioned Parquet format.
"""

import base64
import json
from datetime import datetime
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response
from aws_lambda_powertools.utilities.batch.types import PartialItemFailureResponse
from aws_lambda_powertools.utilities.data_classes.kinesis_stream_event import KinesisStreamRecord
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from ..common import Transaction, settings
from ..services.s3_service import S3Service

logger = Logger()
tracer = Tracer()
metrics = Metrics()
processor = BatchProcessor(event_type=EventType.KinesisDataStreams)

s3_service = S3Service(settings.raw_bucket)


@tracer.capture_method
def process_record(record: KinesisStreamRecord) -> dict[str, Any]:
    """Process a single Kinesis record.

    Args:
        record: Kinesis stream record

    Returns:
        Processed transaction data

    Raises:
        ValueError: If record is invalid
    """
    # Decode the Kinesis data
    data = base64.b64decode(record.kinesis.data).decode("utf-8")

    try:
        transaction_data = json.loads(data)
        transaction = Transaction(**transaction_data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("Failed to parse transaction", error=str(e), data=data[:200])
        raise ValueError(f"Invalid transaction data: {e}")

    # Generate partition path based on timestamp
    ts = transaction.timestamp
    partition = f"year={ts.year}/month={ts.month:02d}/day={ts.day:02d}/hour={ts.hour:02d}"

    # Store transaction
    key = f"raw/transactions/{partition}/{transaction.transaction_id}.json"
    s3_service.put_json(key, transaction.model_dump(mode="json"))

    metrics.add_metric(name="TransactionsProcessed", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="TransactionAmount", unit=MetricUnit.Count, value=float(transaction.amount))

    logger.debug(
        "Processed transaction",
        transaction_id=transaction.transaction_id,
        partition=partition,
    )

    return {
        "transaction_id": transaction.transaction_id,
        "account_id": transaction.account_id,
        "amount": str(transaction.amount),
        "timestamp": transaction.timestamp.isoformat(),
        "partition": partition,
    }


def record_handler(record: KinesisStreamRecord) -> dict[str, Any]:
    """Wrapper for batch processor.

    Args:
        record: Kinesis stream record

    Returns:
        Processing result
    """
    return process_record(record)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict[str, Any], context: LambdaContext) -> PartialItemFailureResponse:
    """Lambda handler for stream processing.

    Uses batch processing with partial failure support to ensure
    successful records are acknowledged even if some fail.

    Args:
        event: Kinesis stream event
        context: Lambda context

    Returns:
        Partial item failure response
    """
    batch_size = len(event.get("Records", []))
    logger.info("Processing Kinesis batch", batch_size=batch_size)
    metrics.add_metric(name="BatchSize", unit=MetricUnit.Count, value=batch_size)

    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )
