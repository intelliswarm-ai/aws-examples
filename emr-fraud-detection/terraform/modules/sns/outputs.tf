output "fraud_alerts_topic_arn" {
  description = "Fraud alerts SNS topic ARN"
  value       = aws_sns_topic.fraud_alerts.arn
}

output "fraud_alerts_topic_name" {
  description = "Fraud alerts SNS topic name"
  value       = aws_sns_topic.fraud_alerts.name
}

output "pipeline_notifications_topic_arn" {
  description = "Pipeline notifications SNS topic ARN"
  value       = aws_sns_topic.pipeline_notifications.arn
}

output "pipeline_notifications_topic_name" {
  description = "Pipeline notifications SNS topic name"
  value       = aws_sns_topic.pipeline_notifications.name
}

output "lambda_dlq_topic_arn" {
  description = "Lambda DLQ SNS topic ARN"
  value       = var.lambda_dlq_enabled ? aws_sns_topic.lambda_dlq[0].arn : null
}
