"""Transaction Ingestion Handler.

This Lambda function receives transactions from API Gateway and publishes
them to Kinesis Data Streams for downstream processing.
"""

import json
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from ..common import (
    IngestionRequest,
    IngestionResponse,
    Transaction,
    get_kinesis_client,
    settings,
)
from ..services.kinesis_service import KinesisService

logger = Logger()
tracer = Tracer()
metrics = Metrics()
app = APIGatewayHttpResolver()

kinesis_service = KinesisService(get_kinesis_client(), settings.kinesis_stream_name)


@app.post("/transactions")
@tracer.capture_method
def ingest_transactions() -> dict[str, Any]:
    """Ingest a batch of transactions.

    Accepts a JSON body with a list of transactions and publishes them
    to Kinesis for processing.
    """
    try:
        body = app.current_event.json_body
        request = IngestionRequest(**body)
    except ValidationError as e:
        logger.warning("Validation error", errors=e.errors())
        metrics.add_metric(name="ValidationErrors", unit=MetricUnit.Count, value=1)
        raise BadRequestError(f"Invalid request: {e.errors()}")

    accepted = 0
    rejected = 0
    rejected_ids: list[str] = []

    # Process transactions in batches
    batch: list[Transaction] = []
    for tx in request.transactions:
        try:
            batch.append(tx)

            # Send batch when reaching max size
            if len(batch) >= settings.kinesis_batch_size:
                _send_batch(batch)
                accepted += len(batch)
                batch = []

        except Exception as e:
            logger.error("Failed to process transaction", transaction_id=tx.transaction_id, error=str(e))
            rejected += 1
            rejected_ids.append(tx.transaction_id)

    # Send remaining batch
    if batch:
        try:
            _send_batch(batch)
            accepted += len(batch)
        except Exception as e:
            logger.error("Failed to send final batch", error=str(e))
            rejected += len(batch)
            rejected_ids.extend([tx.transaction_id for tx in batch])

    # Record metrics
    metrics.add_metric(name="TransactionsAccepted", unit=MetricUnit.Count, value=accepted)
    metrics.add_metric(name="TransactionsRejected", unit=MetricUnit.Count, value=rejected)

    batch_id = request.batch_id or f"batch-{hash(json.dumps([tx.transaction_id for tx in request.transactions]))}"

    response = IngestionResponse(
        success=rejected == 0,
        batch_id=batch_id,
        transactions_accepted=accepted,
        transactions_rejected=rejected,
        rejected_ids=rejected_ids,
        message=f"Ingested {accepted} transactions" + (f", rejected {rejected}" if rejected > 0 else ""),
    )

    logger.info(
        "Ingestion complete",
        batch_id=batch_id,
        accepted=accepted,
        rejected=rejected,
    )

    return response.model_dump()


@tracer.capture_method
def _send_batch(transactions: list[Transaction]) -> None:
    """Send a batch of transactions to Kinesis."""
    records = [tx.to_kinesis_record() for tx in transactions]
    kinesis_service.put_records(records)

    # Record total amount for metrics
    total_amount = sum(float(tx.amount) for tx in transactions)
    metrics.add_metric(name="TotalTransactionAmount", unit=MetricUnit.Count, value=total_amount)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "ingestion"}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda handler for transaction ingestion.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    return app.resolve(event, context)
