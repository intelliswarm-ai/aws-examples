"""Query handler for healthcare imaging data lake."""

import json
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.common.config import settings
from src.common.exceptions import QueryError, QueryTimeoutError
from src.common.models import QueryState
from src.services import get_athena_service

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle Athena query operations.

    Supports:
    - Execute SQL queries
    - Get query status
    - Retrieve query results
    - Cancel queries
    - Pre-built queries for common patterns

    Args:
        event: Lambda event.
        context: Lambda context.

    Returns:
        Response with query results.
    """
    event_type = _get_event_type(event)
    logger.info("Processing query event", extra={"event_type": event_type})

    try:
        if event_type == "api_gateway":
            return _handle_api_request(event)
        else:
            return _handle_direct_invocation(event)

    except QueryTimeoutError as e:
        logger.error(f"Query timeout: {e}")
        metrics.add_metric(name="QueryTimeouts", unit=MetricUnit.Count, value=1)
        return _error_response(408, str(e), e.error_code, e.query_execution_id)

    except QueryError as e:
        logger.error(f"Query error: {e}")
        metrics.add_metric(name="QueryErrors", unit=MetricUnit.Count, value=1)
        return _error_response(400, str(e), e.error_code, e.query_execution_id)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return _error_response(500, "Internal server error", "INTERNAL_ERROR")


def _get_event_type(event: dict[str, Any]) -> str:
    """Determine event source type."""
    if "httpMethod" in event or "requestContext" in event:
        return "api_gateway"
    return "direct"


def _handle_api_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle API Gateway query request."""
    path = event.get("path", "/")
    http_method = event.get("httpMethod", "GET")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body) if body else {}

    # POST /query - Execute new query
    if path.endswith("/query") and http_method == "POST":
        return _execute_query(body)

    # GET /query/{id} - Get query status
    elif "/query/" in path and http_method == "GET":
        query_execution_id = path_params.get("query_execution_id")
        if not query_execution_id:
            return _error_response(400, "Query execution ID required", "MISSING_ID")

        if path.endswith("/results"):
            return _get_query_results(query_execution_id, query_params)
        else:
            return _get_query_status(query_execution_id)

    # DELETE /query/{id} - Cancel query
    elif "/query/" in path and http_method == "DELETE":
        query_execution_id = path_params.get("query_execution_id")
        if not query_execution_id:
            return _error_response(400, "Query execution ID required", "MISSING_ID")
        return _cancel_query(query_execution_id)

    # POST /query/imaging - Pre-built imaging query
    elif path.endswith("/query/imaging") and http_method == "POST":
        return _query_imaging(body)

    # POST /query/cohort - ML cohort extraction
    elif path.endswith("/query/cohort") and http_method == "POST":
        return _extract_cohort(body)

    # GET /query/statistics - Get modality statistics
    elif path.endswith("/query/statistics") and http_method == "GET":
        return _get_statistics()

    else:
        return _error_response(404, "Not found", "NOT_FOUND")


def _handle_direct_invocation(event: dict[str, Any]) -> dict[str, Any]:
    """Handle direct Lambda invocation."""
    action = event.get("action", "execute")
    athena_service = get_athena_service()

    if action == "execute":
        query = event.get("query")
        if not query:
            return {"error": "Query required"}

        result = athena_service.execute_query(
            query,
            wait=event.get("wait", True),
            timeout=event.get("timeout"),
        )
        return result.model_dump(mode="json")

    elif action == "status":
        query_execution_id = event.get("query_execution_id")
        if not query_execution_id:
            return {"error": "query_execution_id required"}

        result = athena_service.get_query_execution(query_execution_id)
        return result.model_dump(mode="json")

    elif action == "results":
        query_execution_id = event.get("query_execution_id")
        if not query_execution_id:
            return {"error": "query_execution_id required"}

        return athena_service.get_query_results(
            query_execution_id,
            max_results=event.get("max_results", 1000),
            next_token=event.get("next_token"),
        )

    elif action == "cancel":
        query_execution_id = event.get("query_execution_id")
        if not query_execution_id:
            return {"error": "query_execution_id required"}

        athena_service.cancel_query(query_execution_id)
        return {"message": "Query cancelled"}

    else:
        return {"error": f"Unknown action: {action}"}


def _execute_query(body: dict[str, Any]) -> dict[str, Any]:
    """Execute a new SQL query."""
    athena_service = get_athena_service()

    query = body.get("query")
    if not query:
        return _error_response(400, "Query required", "MISSING_QUERY")

    wait = body.get("wait", False)
    timeout = body.get("timeout", settings.athena_query_timeout)

    result = athena_service.execute_query(query, wait=wait, timeout=timeout)

    metrics.add_metric(name="QueriesExecuted", unit=MetricUnit.Count, value=1)

    response_data = {
        "query_execution_id": result.query_execution_id,
        "state": result.state.value,
    }

    if result.state == QueryState.SUCCEEDED:
        response_data["execution_time_ms"] = result.execution_time_ms
        response_data["data_scanned_bytes"] = result.data_scanned_bytes
        response_data["data_scanned_gb"] = result.data_scanned_gb
        response_data["estimated_cost_usd"] = result.estimated_cost_usd

        metrics.add_metric(
            name="DataScannedBytes",
            unit=MetricUnit.Bytes,
            value=result.data_scanned_bytes or 0,
        )

        # Include results if requested and query succeeded
        if body.get("include_results", False):
            results = athena_service.get_query_results(result.query_execution_id)
            response_data["results"] = results

    elif result.state == QueryState.FAILED:
        response_data["error_message"] = result.error_message

    return _api_response(200 if wait else 202, response_data)


def _get_query_status(query_execution_id: str) -> dict[str, Any]:
    """Get query execution status."""
    athena_service = get_athena_service()

    result = athena_service.get_query_execution(query_execution_id)

    return _api_response(
        200,
        {
            "query_execution_id": result.query_execution_id,
            "state": result.state.value,
            "execution_time_ms": result.execution_time_ms,
            "data_scanned_bytes": result.data_scanned_bytes,
            "data_scanned_gb": result.data_scanned_gb,
            "estimated_cost_usd": result.estimated_cost_usd,
            "error_message": result.error_message,
            "submitted_at": result.submitted_at,
            "completed_at": result.completed_at,
        },
    )


def _get_query_results(
    query_execution_id: str,
    query_params: dict[str, Any],
) -> dict[str, Any]:
    """Get query results with pagination."""
    athena_service = get_athena_service()

    max_results = int(query_params.get("max_results", 1000))
    next_token = query_params.get("next_token")

    results = athena_service.get_query_results(
        query_execution_id,
        max_results=max_results,
        next_token=next_token,
    )

    return _api_response(
        200,
        {
            "query_execution_id": query_execution_id,
            "columns": results["columns"],
            "rows": results["rows"],
            "row_count": results["row_count"],
            "next_token": results.get("next_token"),
        },
    )


def _cancel_query(query_execution_id: str) -> dict[str, Any]:
    """Cancel a running query."""
    athena_service = get_athena_service()

    athena_service.cancel_query(query_execution_id)

    return _api_response(
        200,
        {
            "query_execution_id": query_execution_id,
            "message": "Query cancelled",
        },
    )


def _query_imaging(body: dict[str, Any]) -> dict[str, Any]:
    """Execute pre-built imaging query."""
    athena_service = get_athena_service()

    condition_codes = body.get("condition_codes", [])
    modality = body.get("modality")
    body_part = body.get("body_part")
    limit = body.get("limit", 1000)

    if not condition_codes:
        return _error_response(
            400, "condition_codes required", "MISSING_CONDITION_CODES"
        )

    result = athena_service.query_imaging_by_condition(
        condition_codes=condition_codes,
        modality=modality,
        body_part=body_part,
        limit=limit,
    )

    metrics.add_metric(name="ImagingQueries", unit=MetricUnit.Count, value=1)

    response_data = {
        "query_execution_id": result.query_execution_id,
        "state": result.state.value,
        "execution_time_ms": result.execution_time_ms,
        "data_scanned_gb": result.data_scanned_gb,
    }

    if result.state == QueryState.SUCCEEDED:
        results = athena_service.get_query_results(result.query_execution_id)
        response_data["results"] = results

    return _api_response(200, response_data)


def _extract_cohort(body: dict[str, Any]) -> dict[str, Any]:
    """Extract balanced ML training cohort."""
    athena_service = get_athena_service()

    positive_codes = body.get("positive_condition_codes", [])
    negative_codes = body.get("negative_condition_codes")
    modality = body.get("modality", "CT")
    body_part = body.get("body_part", "CHEST")
    samples_per_class = body.get("samples_per_class", 5000)

    if not positive_codes:
        return _error_response(
            400, "positive_condition_codes required", "MISSING_POSITIVE_CODES"
        )

    result = athena_service.extract_ml_cohort(
        positive_condition_codes=positive_codes,
        negative_condition_codes=negative_codes,
        modality=modality,
        body_part=body_part,
        samples_per_class=samples_per_class,
    )

    metrics.add_metric(name="CohortExtractions", unit=MetricUnit.Count, value=1)

    response_data = {
        "query_execution_id": result.query_execution_id,
        "state": result.state.value,
        "execution_time_ms": result.execution_time_ms,
        "data_scanned_gb": result.data_scanned_gb,
        "estimated_cost_usd": result.estimated_cost_usd,
    }

    if result.state == QueryState.SUCCEEDED:
        results = athena_service.get_query_results(result.query_execution_id)
        response_data["cohort_size"] = results["row_count"]
        response_data["results"] = results

    return _api_response(200, response_data)


def _get_statistics() -> dict[str, Any]:
    """Get modality statistics."""
    athena_service = get_athena_service()

    result = athena_service.get_statistics_by_modality()

    response_data = {
        "query_execution_id": result.query_execution_id,
        "state": result.state.value,
    }

    if result.state == QueryState.SUCCEEDED:
        results = athena_service.get_query_results(result.query_execution_id)
        response_data["statistics"] = results["rows"]

    return _api_response(200, response_data)


def _api_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def _error_response(
    status_code: int,
    message: str,
    error_code: str,
    query_execution_id: str | None = None,
) -> dict[str, Any]:
    """Create error response."""
    body: dict[str, Any] = {"error": message, "error_code": error_code}
    if query_execution_id:
        body["query_execution_id"] = query_execution_id

    return _api_response(status_code, body)
