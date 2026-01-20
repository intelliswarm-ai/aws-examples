output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alarms"
  value       = var.create_sns_topic ? aws_sns_topic.alarms[0].arn : null
}

output "alarm_arns" {
  description = "ARNs of CloudWatch alarms"
  value = {
    lambda_errors = {
      for k, v in aws_cloudwatch_metric_alarm.lambda_errors : k => v.arn
    }
    lambda_duration = {
      for k, v in aws_cloudwatch_metric_alarm.lambda_duration : k => v.arn
    }
    athena_query_timeout = aws_cloudwatch_metric_alarm.athena_query_timeout.arn
    athena_data_scanned  = aws_cloudwatch_metric_alarm.athena_data_scanned.arn
    access_denied        = aws_cloudwatch_metric_alarm.access_denied.arn
  }
}

output "metric_filter_names" {
  description = "Names of CloudWatch log metric filters"
  value = {
    access_denied = aws_cloudwatch_log_metric_filter.access_denied.name
    phi_access    = aws_cloudwatch_log_metric_filter.phi_access.name
  }
}
