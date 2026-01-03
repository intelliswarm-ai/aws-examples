output "ingestion_function_arn" {
  description = "Ingestion Lambda function ARN"
  value       = aws_lambda_function.ingestion.arn
}

output "ingestion_function_name" {
  description = "Ingestion Lambda function name"
  value       = aws_lambda_function.ingestion.function_name
}

output "stream_processor_function_arn" {
  description = "Stream processor Lambda function ARN"
  value       = aws_lambda_function.stream_processor.arn
}

output "stream_processor_function_name" {
  description = "Stream processor Lambda function name"
  value       = aws_lambda_function.stream_processor.function_name
}

output "orchestration_function_arn" {
  description = "Orchestration Lambda function ARN"
  value       = aws_lambda_function.orchestration.arn
}

output "orchestration_function_name" {
  description = "Orchestration Lambda function name"
  value       = aws_lambda_function.orchestration.function_name
}

output "alert_function_arn" {
  description = "Alert Lambda function ARN"
  value       = aws_lambda_function.alert.arn
}

output "alert_function_name" {
  description = "Alert Lambda function name"
  value       = aws_lambda_function.alert.function_name
}

output "query_function_arn" {
  description = "Query Lambda function ARN"
  value       = aws_lambda_function.query.arn
}

output "query_function_name" {
  description = "Query Lambda function name"
  value       = aws_lambda_function.query.function_name
}

output "function_names" {
  description = "All Lambda function names"
  value = [
    aws_lambda_function.ingestion.function_name,
    aws_lambda_function.stream_processor.function_name,
    aws_lambda_function.orchestration.function_name,
    aws_lambda_function.alert.function_name,
    aws_lambda_function.query.function_name,
  ]
}
