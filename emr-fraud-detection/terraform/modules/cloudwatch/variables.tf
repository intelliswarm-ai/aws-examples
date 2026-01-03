variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "kinesis_stream_name" {
  description = "Kinesis stream name"
  type        = string
}

variable "lambda_function_names" {
  description = "List of Lambda function names"
  type        = list(string)
}

variable "api_gateway_name" {
  description = "API Gateway name"
  type        = string
}

variable "emr_cluster_id" {
  description = "EMR cluster ID"
  type        = string
}

variable "streaming_cluster_id" {
  description = "Streaming EMR cluster ID"
  type        = string
  default     = null
}

variable "alerts_table_name" {
  description = "Alerts DynamoDB table name"
  type        = string
}

variable "predictions_table_name" {
  description = "Predictions DynamoDB table name"
  type        = string
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for fraud alerts"
  type        = string
}

variable "alarm_email" {
  description = "Email for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "enable_anomaly_detection" {
  description = "Enable anomaly detection"
  type        = bool
  default     = false
}

variable "lambda_error_threshold" {
  description = "Lambda error threshold"
  type        = number
  default     = 5
}

variable "lambda_duration_threshold" {
  description = "Lambda duration threshold in ms"
  type        = number
  default     = 30000
}

variable "kinesis_iterator_age_threshold" {
  description = "Kinesis iterator age threshold in ms"
  type        = number
  default     = 60000
}

variable "emr_step_failure_threshold" {
  description = "EMR step failure threshold"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
