"""Query Handler.

This Lambda function handles API requests for querying fraud predictions
and alerts.
"""

from datetime import datetime
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..common import FraudStatus, QueryRequest, QueryResponse, settings
from ..services.dynamodb_service import DynamoDBService

logger = Logger()
tracer = Tracer()
metrics = Metrics()
app = APIGatewayHttpResolver()

dynamodb_service = DynamoDBService()


@app.get("/predictions")
@tracer.capture_method
def get_predictions() -> dict[str, Any]:
    """Get fraud predictions with optional filters.

    Query parameters:
        - account_id: Filter by account
        - fraud_status: Filter by status (LEGITIMATE, SUSPICIOUS, FRAUDULENT)
        - min_score: Minimum fraud score
        - start_date: Start date (ISO format)
        - end_date: End date (ISO format)
        - limit: Maximum results (default 100)

    Returns:
        List of predictions
    """
    params = app.current_event.query_string_parameters or {}

    request = QueryRequest(
        account_id=params.get("account_id"),
        fraud_status=FraudStatus(params["fraud_status"]) if params.get("fraud_status") else None,
        min_score=float(params["min_score"]) if params.get("min_score") else None,
        start_date=datetime.fromisoformat(params["start_date"]) if params.get("start_date") else None,
        end_date=datetime.fromisoformat(params["end_date"]) if params.get("end_date") else None,
        limit=int(params.get("limit", 100)),
    )

    predictions = dynamodb_service.query_predictions(
        account_id=request.account_id,
        fraud_status=request.fraud_status,
        min_score=request.min_score,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit,
    )

    metrics.add_metric(name="PredictionQueries", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="PredictionResultsReturned", unit=MetricUnit.Count, value=len(predictions))

    response = QueryResponse(
        predictions=predictions,
        total_count=len(predictions),
        has_more=len(predictions) == request.limit,
    )

    return response.model_dump(mode="json")


@app.get("/predictions/<transaction_id>")
@tracer.capture_method
def get_prediction_by_transaction(transaction_id: str) -> dict[str, Any]:
    """Get prediction for a specific transaction.

    Args:
        transaction_id: Transaction identifier

    Returns:
        Prediction details
    """
    prediction = dynamodb_service.get_prediction_by_transaction(transaction_id)

    if not prediction:
        raise NotFoundError(f"Prediction not found for transaction: {transaction_id}")

    metrics.add_metric(name="PredictionLookups", unit=MetricUnit.Count, value=1)

    return prediction.model_dump(mode="json")


@app.get("/alerts")
@tracer.capture_method
def get_alerts() -> dict[str, Any]:
    """Get fraud alerts with optional filters.

    Query parameters:
        - account_id: Filter by account
        - severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
        - acknowledged: Filter by acknowledgement status
        - start_date: Start date (ISO format)
        - end_date: End date (ISO format)
        - limit: Maximum results (default 100)

    Returns:
        List of alerts
    """
    params = app.current_event.query_string_parameters or {}

    account_id = params.get("account_id")
    severity = params.get("severity")
    acknowledged = params.get("acknowledged")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    limit = int(params.get("limit", 100))

    alerts = dynamodb_service.query_alerts(
        account_id=account_id,
        severity=severity,
        acknowledged=acknowledged.lower() == "true" if acknowledged else None,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        limit=limit,
    )

    metrics.add_metric(name="AlertQueries", unit=MetricUnit.Count, value=1)
    metrics.add_metric(name="AlertResultsReturned", unit=MetricUnit.Count, value=len(alerts))

    return {
        "alerts": [alert.model_dump(mode="json") for alert in alerts],
        "total_count": len(alerts),
        "has_more": len(alerts) == limit,
    }


@app.get("/alerts/<account_id>")
@tracer.capture_method
def get_alerts_by_account(account_id: str) -> dict[str, Any]:
    """Get alerts for a specific account.

    Args:
        account_id: Account identifier

    Returns:
        List of alerts for the account
    """
    params = app.current_event.query_string_parameters or {}
    limit = int(params.get("limit", 100))

    alerts = dynamodb_service.query_alerts(
        account_id=account_id,
        limit=limit,
    )

    metrics.add_metric(name="AccountAlertQueries", unit=MetricUnit.Count, value=1)

    return {
        "account_id": account_id,
        "alerts": [alert.model_dump(mode="json") for alert in alerts],
        "total_count": len(alerts),
    }


@app.post("/alerts/<alert_id>/acknowledge")
@tracer.capture_method
def acknowledge_alert(alert_id: str) -> dict[str, Any]:
    """Acknowledge a fraud alert.

    Args:
        alert_id: Alert identifier

    Returns:
        Acknowledgement result
    """
    body = app.current_event.json_body or {}
    acknowledged_by = body.get("acknowledged_by", "system")

    success = dynamodb_service.acknowledge_alert(alert_id, acknowledged_by)

    if not success:
        raise NotFoundError(f"Alert not found: {alert_id}")

    metrics.add_metric(name="AlertsAcknowledged", unit=MetricUnit.Count, value=1)

    logger.info("Alert acknowledged", alert_id=alert_id, acknowledged_by=acknowledged_by)

    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": datetime.utcnow().isoformat(),
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "query"}


@app.get("/stats")
@tracer.capture_method
def get_stats() -> dict[str, Any]:
    """Get fraud detection statistics.

    Returns:
        Statistics summary
    """
    # Get today's date
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Query counts
    predictions = dynamodb_service.query_predictions(limit=1000)
    alerts = dynamodb_service.query_alerts(limit=1000)

    total_predictions = len(predictions)
    fraud_count = sum(1 for p in predictions if p.fraud_status == FraudStatus.FRAUDULENT)
    suspicious_count = sum(1 for p in predictions if p.fraud_status == FraudStatus.SUSPICIOUS)
    unacknowledged_alerts = sum(1 for a in alerts if not a.acknowledged)

    return {
        "date": today,
        "total_predictions": total_predictions,
        "fraud_detected": fraud_count,
        "suspicious_detected": suspicious_count,
        "total_alerts": len(alerts),
        "unacknowledged_alerts": unacknowledged_alerts,
        "fraud_rate": fraud_count / total_predictions if total_predictions > 0 else 0,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda handler for query API.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    return app.resolve(event, context)
