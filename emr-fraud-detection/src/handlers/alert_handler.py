"""Alert Handler.

This Lambda function processes fraud predictions and generates alerts
for high-risk transactions.
"""

from datetime import datetime
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..common import (
    AlertSeverity,
    AlertType,
    FraudAlert,
    FraudPrediction,
    FraudStatus,
    settings,
)
from ..services.dynamodb_service import DynamoDBService
from ..services.notification_service import NotificationService
from ..services.s3_service import S3Service

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb_service = DynamoDBService()
notification_service = NotificationService()
s3_service = S3Service(settings.predictions_bucket)


@tracer.capture_method
def process_prediction(prediction: FraudPrediction) -> FraudAlert | None:
    """Process a fraud prediction and generate alert if needed.

    Args:
        prediction: Fraud prediction result

    Returns:
        Generated alert or None if not alertable
    """
    # Only create alerts for fraudulent or suspicious transactions
    if prediction.fraud_status not in [FraudStatus.FRAUDULENT, FraudStatus.SUSPICIOUS]:
        return None

    # Determine alert type based on risk factors
    alert_type = _determine_alert_type(prediction.risk_factors)

    # Determine severity based on score
    if prediction.fraud_score >= 0.9:
        severity = AlertSeverity.CRITICAL
        action = "Block transaction and contact customer immediately"
    elif prediction.fraud_score >= 0.8:
        severity = AlertSeverity.HIGH
        action = "Block transaction and request verification"
    elif prediction.fraud_score >= 0.7:
        severity = AlertSeverity.MEDIUM
        action = "Flag for manual review within 1 hour"
    else:
        severity = AlertSeverity.LOW
        action = "Monitor account for suspicious activity"

    risk_summary = ", ".join(prediction.risk_factors[:3]) if prediction.risk_factors else "Pattern anomaly"

    alert = FraudAlert(
        transaction_id=prediction.transaction_id,
        account_id=prediction.account_id,
        fraud_score=prediction.fraud_score,
        alert_type=alert_type,
        severity=severity,
        message=f"Potential fraud detected: {risk_summary}. Score: {prediction.fraud_score:.2f}",
        recommended_action=action,
    )

    return alert


def _determine_alert_type(risk_factors: list[str]) -> AlertType:
    """Determine alert type from risk factors.

    Args:
        risk_factors: List of risk factor identifiers

    Returns:
        Alert type
    """
    factor_mapping = {
        "high_velocity": AlertType.VELOCITY,
        "unusual_location": AlertType.GEOGRAPHIC,
        "distance_anomaly": AlertType.GEOGRAPHIC,
        "high_amount": AlertType.HIGH_VALUE,
        "amount_outlier": AlertType.HIGH_VALUE,
        "pattern_anomaly": AlertType.PATTERN,
        "behavioral_anomaly": AlertType.BEHAVIORAL,
        "blacklist_match": AlertType.BLACKLIST,
    }

    for factor in risk_factors:
        factor_lower = factor.lower()
        for key, alert_type in factor_mapping.items():
            if key in factor_lower:
                return alert_type

    return AlertType.PATTERN


@tracer.capture_method
def process_results(event: dict[str, Any]) -> dict[str, Any]:
    """Process batch scoring results and generate alerts.

    Args:
        event: Event with predictions_path

    Returns:
        Processing summary
    """
    predictions_path = event.get("predictions_path", "")
    date = event.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    if not predictions_path:
        predictions_path = f"predictions/date={date}/"

    logger.info("Processing results", predictions_path=predictions_path)

    # List prediction files
    files = s3_service.list_objects(predictions_path)

    total_processed = 0
    alerts_created = 0
    fraud_count = 0
    suspicious_count = 0

    for file_key in files:
        if not file_key.endswith(".json"):
            continue

        try:
            data = s3_service.get_json(file_key)

            # Handle both single predictions and batches
            predictions_data = data if isinstance(data, list) else [data]

            for pred_data in predictions_data:
                prediction = FraudPrediction(**pred_data)
                total_processed += 1

                # Track counts
                if prediction.fraud_status == FraudStatus.FRAUDULENT:
                    fraud_count += 1
                elif prediction.fraud_status == FraudStatus.SUSPICIOUS:
                    suspicious_count += 1

                # Generate and save alert
                alert = process_prediction(prediction)
                if alert:
                    dynamodb_service.put_alert(alert)
                    alerts_created += 1

                    # Send notification for critical/high severity
                    if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                        notification_service.send_alert(alert)
                        metrics.add_metric(name="AlertNotificationsSent", unit=MetricUnit.Count, value=1)

                # Save prediction to DynamoDB
                dynamodb_service.put_prediction(prediction)

        except Exception as e:
            logger.error("Failed to process file", file_key=file_key, error=str(e))

    # Record metrics
    metrics.add_metric(name="PredictionsProcessed", unit=MetricUnit.Count, value=total_processed)
    metrics.add_metric(name="AlertsCreated", unit=MetricUnit.Count, value=alerts_created)
    metrics.add_metric(name="FraudDetected", unit=MetricUnit.Count, value=fraud_count)
    metrics.add_metric(name="SuspiciousDetected", unit=MetricUnit.Count, value=suspicious_count)

    logger.info(
        "Results processing complete",
        total_processed=total_processed,
        alerts_created=alerts_created,
        fraud_count=fraud_count,
        suspicious_count=suspicious_count,
    )

    return {
        "success": True,
        "total_processed": total_processed,
        "alerts_created": alerts_created,
        "fraud_detected": fraud_count,
        "suspicious_detected": suspicious_count,
        "date": date,
    }


@tracer.capture_method
def send_batch_alert(event: dict[str, Any]) -> dict[str, Any]:
    """Send a batch summary alert.

    Args:
        event: Event with batch summary

    Returns:
        Send result
    """
    fraud_count = event.get("fraud_detected", 0)
    suspicious_count = event.get("suspicious_detected", 0)
    date = event.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    if fraud_count > 0 or suspicious_count > 0:
        message = (
            f"Fraud Detection Summary for {date}\n\n"
            f"Fraudulent transactions: {fraud_count}\n"
            f"Suspicious transactions: {suspicious_count}\n\n"
            f"Please review the alerts dashboard for details."
        )

        notification_service.send_message(
            subject=f"Fraud Detection Alert: {fraud_count} fraudulent transactions detected",
            message=message,
        )

        logger.info("Batch alert sent", fraud_count=fraud_count, suspicious_count=suspicious_count)

    return {"success": True, "message_sent": fraud_count > 0 or suspicious_count > 0}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda handler for alert processing.

    Args:
        event: Event with action and parameters
        context: Lambda context

    Returns:
        Processing result
    """
    action = event.get("action", "process_results")

    logger.info("Alert action", action=action)

    if action == "process_results":
        return process_results(event)
    elif action == "send_batch_alert":
        return send_batch_alert(event)
    else:
        raise ValueError(f"Unknown action: {action}")
