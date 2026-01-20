"""Catalog handler for healthcare imaging data lake."""

import json
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.common.config import settings
from src.common.exceptions import CatalogError, CrawlerError
from src.services import get_glue_service, get_lakeformation_service

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle catalog operations.

    Supports:
    - Table listing and description
    - Crawler management
    - Partition operations
    - Lake Formation permission queries

    Args:
        event: Lambda event.
        context: Lambda context.

    Returns:
        Response with catalog operation results.
    """
    event_type = _get_event_type(event)
    logger.info("Processing catalog event", extra={"event_type": event_type})

    try:
        if event_type == "api_gateway":
            return _handle_api_request(event)
        elif event_type == "schedule":
            return _handle_scheduled_crawl(event)
        else:
            return _handle_direct_invocation(event)

    except CrawlerError as e:
        logger.error(f"Crawler error: {e}")
        return _error_response(500, str(e), e.error_code)

    except CatalogError as e:
        logger.error(f"Catalog error: {e}")
        return _error_response(400, str(e), e.error_code)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return _error_response(500, "Internal server error", "INTERNAL_ERROR")


def _get_event_type(event: dict[str, Any]) -> str:
    """Determine event source type."""
    if "httpMethod" in event or "requestContext" in event:
        return "api_gateway"
    elif "detail-type" in event:
        return "schedule"
    return "direct"


def _handle_api_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle API Gateway catalog request."""
    path = event.get("path", "/")
    http_method = event.get("httpMethod", "GET")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body) if body else {}

    if path.endswith("/tables"):
        if http_method == "GET":
            return _list_tables(query_params)
        return _error_response(405, "Method not allowed", "METHOD_NOT_ALLOWED")

    elif "/tables/" in path:
        table_name = path_params.get("table_name")
        if not table_name:
            return _error_response(400, "Table name required", "MISSING_TABLE")

        if http_method == "GET":
            return _describe_table(table_name)
        return _error_response(405, "Method not allowed", "METHOD_NOT_ALLOWED")

    elif path.endswith("/crawl"):
        if http_method == "POST":
            return _start_crawler(body)
        elif http_method == "GET":
            return _get_crawler_status(query_params)
        return _error_response(405, "Method not allowed", "METHOD_NOT_ALLOWED")

    elif path.endswith("/partitions"):
        if http_method == "GET":
            return _list_partitions(query_params)
        return _error_response(405, "Method not allowed", "METHOD_NOT_ALLOWED")

    elif path.endswith("/permissions"):
        if http_method == "GET":
            return _list_permissions(query_params)
        return _error_response(405, "Method not allowed", "METHOD_NOT_ALLOWED")

    else:
        return _error_response(404, "Not found", "NOT_FOUND")


def _handle_scheduled_crawl(event: dict[str, Any]) -> dict[str, Any]:
    """Handle scheduled crawler run."""
    glue_service = get_glue_service()

    try:
        glue_service.start_crawler()
        metrics.add_metric(name="CrawlerStarted", unit=MetricUnit.Count, value=1)

        # Wait for completion if this is a synchronous invocation
        wait = event.get("detail", {}).get("wait", False)
        if wait:
            result = glue_service.wait_for_crawler_completion()
            return {
                "statusCode": 200,
                "body": json.dumps(result.model_dump(mode="json"), default=str),
            }

        return {
            "statusCode": 202,
            "body": json.dumps({"message": "Crawler started"}),
        }

    except CrawlerError as e:
        logger.error(f"Scheduled crawler failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


def _handle_direct_invocation(event: dict[str, Any]) -> dict[str, Any]:
    """Handle direct Lambda invocation."""
    action = event.get("action", "list_tables")
    glue_service = get_glue_service()

    if action == "list_tables":
        tables = glue_service.list_tables()
        return {"tables": tables}

    elif action == "describe_table":
        table_name = event.get("table_name")
        if not table_name:
            return {"error": "table_name required"}
        table = glue_service.get_table(table_name)
        return table.model_dump(mode="json") if table else {"error": "Table not found"}

    elif action == "start_crawler":
        glue_service.start_crawler(event.get("crawler_name"))
        return {"message": "Crawler started"}

    elif action == "crawler_status":
        status = glue_service.get_crawler_status(event.get("crawler_name"))
        return status.model_dump(mode="json")

    else:
        return {"error": f"Unknown action: {action}"}


def _list_tables(query_params: dict[str, Any]) -> dict[str, Any]:
    """List all tables in the database."""
    glue_service = get_glue_service()
    database = query_params.get("database", settings.glue_database)

    tables = glue_service.list_tables(database)

    # Get details for each table
    table_details = []
    for table_name in tables:
        table = glue_service.get_table(table_name, database)
        if table:
            table_details.append(
                {
                    "name": table.table_name,
                    "location": table.location,
                    "partition_keys": table.partition_keys,
                    "row_count": table.row_count,
                    "size_bytes": table.size_bytes,
                }
            )

    return _api_response(
        200,
        {"database": database, "tables": table_details, "count": len(table_details)},
    )


def _describe_table(table_name: str) -> dict[str, Any]:
    """Describe a specific table."""
    glue_service = get_glue_service()

    table = glue_service.get_table(table_name)
    if not table:
        return _error_response(404, f"Table not found: {table_name}", "NOT_FOUND")

    return _api_response(200, table.model_dump(mode="json"))


def _start_crawler(body: dict[str, Any]) -> dict[str, Any]:
    """Start the Glue crawler."""
    glue_service = get_glue_service()
    crawler_name = body.get("crawler_name", settings.glue_crawler_name)
    wait = body.get("wait", False)

    glue_service.start_crawler(crawler_name)
    metrics.add_metric(name="CrawlerStarted", unit=MetricUnit.Count, value=1)

    if wait:
        result = glue_service.wait_for_crawler_completion(crawler_name)
        return _api_response(200, result.model_dump(mode="json"))

    return _api_response(202, {"message": "Crawler started", "crawler_name": crawler_name})


def _get_crawler_status(query_params: dict[str, Any]) -> dict[str, Any]:
    """Get crawler status."""
    glue_service = get_glue_service()
    crawler_name = query_params.get("crawler_name", settings.glue_crawler_name)

    status = glue_service.get_crawler_status(crawler_name)
    return _api_response(200, status.model_dump(mode="json"))


def _list_partitions(query_params: dict[str, Any]) -> dict[str, Any]:
    """List partitions for a table."""
    glue_service = get_glue_service()
    table_name = query_params.get("table_name", settings.imaging_table)
    expression = query_params.get("filter")

    partitions = glue_service.get_partitions(table_name, expression=expression)

    # Calculate partition statistics
    total_partitions = len(partitions)
    partition_summary = {}
    for p in partitions:
        values = p["values"]
        if len(values) >= 1:
            year = values[0]
            partition_summary[year] = partition_summary.get(year, 0) + 1

    return _api_response(
        200,
        {
            "table_name": table_name,
            "total_partitions": total_partitions,
            "by_year": partition_summary,
            "partitions": partitions[:100],  # Limit response size
        },
    )


def _list_permissions(query_params: dict[str, Any]) -> dict[str, Any]:
    """List Lake Formation permissions."""
    lf_service = get_lakeformation_service()
    principal_arn = query_params.get("principal_arn")
    resource_type = query_params.get("resource_type")

    permissions = lf_service.list_permissions(
        principal_arn=principal_arn,
        resource_type=resource_type,
    )

    return _api_response(
        200,
        {
            "permissions": [p.model_dump(mode="json") for p in permissions],
            "count": len(permissions),
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
        },
        "body": json.dumps(body, default=str),
    }


def _error_response(
    status_code: int,
    message: str,
    error_code: str,
) -> dict[str, Any]:
    """Create error response."""
    return _api_response(
        status_code,
        {"error": message, "error_code": error_code},
    )
