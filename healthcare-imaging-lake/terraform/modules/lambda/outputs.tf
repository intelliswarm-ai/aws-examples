output "api_handler_arn" {
  description = "ARN of the API handler Lambda function"
  value       = aws_lambda_function.api_handler.arn
}

output "api_handler_name" {
  description = "Name of the API handler Lambda function"
  value       = aws_lambda_function.api_handler.function_name
}

output "api_handler_invoke_arn" {
  description = "Invoke ARN of the API handler Lambda function"
  value       = aws_lambda_function.api_handler.invoke_arn
}

output "ingestion_handler_arn" {
  description = "ARN of the ingestion handler Lambda function"
  value       = aws_lambda_function.ingestion_handler.arn
}

output "ingestion_handler_name" {
  description = "Name of the ingestion handler Lambda function"
  value       = aws_lambda_function.ingestion_handler.function_name
}

output "catalog_handler_arn" {
  description = "ARN of the catalog handler Lambda function"
  value       = aws_lambda_function.catalog_handler.arn
}

output "catalog_handler_name" {
  description = "Name of the catalog handler Lambda function"
  value       = aws_lambda_function.catalog_handler.function_name
}

output "query_handler_arn" {
  description = "ARN of the query handler Lambda function"
  value       = aws_lambda_function.query_handler.arn
}

output "query_handler_name" {
  description = "Name of the query handler Lambda function"
  value       = aws_lambda_function.query_handler.function_name
}

output "query_handler_invoke_arn" {
  description = "Invoke ARN of the query handler Lambda function"
  value       = aws_lambda_function.query_handler.invoke_arn
}

output "lambda_log_groups" {
  description = "CloudWatch log group names for Lambda functions"
  value = {
    api_handler       = aws_cloudwatch_log_group.api_handler.name
    ingestion_handler = aws_cloudwatch_log_group.ingestion_handler.name
    catalog_handler   = aws_cloudwatch_log_group.catalog_handler.name
    query_handler     = aws_cloudwatch_log_group.query_handler.name
  }
}
