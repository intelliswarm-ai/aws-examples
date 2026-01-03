output "alerts_table_name" {
  description = "Alerts table name"
  value       = aws_dynamodb_table.alerts.name
}

output "alerts_table_arn" {
  description = "Alerts table ARN"
  value       = aws_dynamodb_table.alerts.arn
}

output "predictions_table_name" {
  description = "Predictions table name"
  value       = aws_dynamodb_table.predictions.name
}

output "predictions_table_arn" {
  description = "Predictions table ARN"
  value       = aws_dynamodb_table.predictions.arn
}

output "executions_table_name" {
  description = "Executions table name"
  value       = aws_dynamodb_table.executions.name
}

output "executions_table_arn" {
  description = "Executions table ARN"
  value       = aws_dynamodb_table.executions.arn
}
