"""Main API handler for healthcare imaging data lake."""

import json
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.common.config import settings

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Main API Gateway router.

    Routes requests to appropriate handlers based on path.

    Routes:
        POST   /ingest              -> ingestion_handler
        POST   /ingest/batch        -> ingestion_handler (batch)
        GET    /catalog/tables      -> catalog_handler
        GET    /catalog/tables/{id} -> catalog_handler
        POST   /catalog/crawl       -> catalog_handler
        GET    /catalog/partitions  -> catalog_handler
        GET    /catalog/permissions -> catalog_handler
        POST   /query               -> query_handler
        GET    /query/{id}          -> query_handler
        GET    /query/{id}/results  -> query_handler
        DELETE /query/{id}          -> query_handler
        POST   /query/imaging       -> query_handler (imaging search)
        POST   /query/cohort        -> query_handler (ML cohort)
        GET    /query/statistics    -> query_handler (stats)
        GET    /health              -> health check

    Args:
        event: Lambda event.
        context: Lambda context.

    Returns:
        API Gateway response.
    """
    path = event.get("path", "/")
    http_method = event.get("httpMethod", "GET")

    logger.info(
        "Routing request",
        extra={"path": path, "method": http_method},
    )

    try:
        # Health check
        if path == "/health" or path == "/":
            return _health_check()

        # Ingestion routes
        if path.startswith("/ingest"):
            from src.handlers.ingestion_handler import handler as ingestion_handler

            return ingestion_handler(event, context)

        # Catalog routes
        if path.startswith("/catalog"):
            from src.handlers.catalog_handler import handler as catalog_handler

            return catalog_handler(event, context)

        # Query routes
        if path.startswith("/query"):
            from src.handlers.query_handler import handler as query_handler

            return query_handler(event, context)

        # Not found
        return _api_response(
            404,
            {"error": "Not found", "path": path},
        )

    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        return _api_response(
            500,
            {"error": "Internal server error"},
        )


def _health_check() -> dict[str, Any]:
    """Return health check response."""
    return _api_response(
        200,
        {
            "status": "healthy",
            "service": "healthcare-imaging-lake",
            "version": "0.1.0",
            "environment": settings.environment,
            "region": settings.aws_region,
            "database": settings.glue_database,
        },
    )


def _api_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "X-Service": "healthcare-imaging-lake",
        },
        "body": json.dumps(body, default=str),
    }
