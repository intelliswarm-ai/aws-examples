variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "lambda_role_arn" {
  description = "Lambda execution role ARN"
  type        = string
}

variable "kinesis_stream_arn" {
  description = "Kinesis stream ARN"
  type        = string
}

variable "kinesis_stream_name" {
  description = "Kinesis stream name"
  type        = string
}

variable "raw_bucket_name" {
  description = "Raw data bucket name"
  type        = string
}

variable "predictions_bucket_name" {
  description = "Predictions bucket name"
  type        = string
}

variable "alerts_table_name" {
  description = "Alerts DynamoDB table name"
  type        = string
}

variable "predictions_table_name" {
  description = "Predictions DynamoDB table name"
  type        = string
}

variable "fraud_alerts_topic_arn" {
  description = "Fraud alerts SNS topic ARN"
  type        = string
}

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs for Lambda"
  type        = list(string)
}

variable "vpc_security_group_ids" {
  description = "VPC security group IDs for Lambda"
  type        = list(string)
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention days"
  type        = number
  default     = 30
}

variable "fraud_threshold" {
  description = "Fraud detection threshold"
  type        = number
  default     = 0.7
}

variable "suspicious_threshold" {
  description = "Suspicious detection threshold"
  type        = number
  default     = 0.5
}

variable "model_version" {
  description = "ML model version"
  type        = string
  default     = "v1.0"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
