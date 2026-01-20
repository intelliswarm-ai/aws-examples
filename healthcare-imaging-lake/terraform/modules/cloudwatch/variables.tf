variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# Lambda Function Names
variable "api_handler_name" {
  description = "Name of the API handler Lambda function"
  type        = string
}

variable "ingestion_handler_name" {
  description = "Name of the ingestion handler Lambda function"
  type        = string
}

variable "catalog_handler_name" {
  description = "Name of the catalog handler Lambda function"
  type        = string
}

variable "query_handler_name" {
  description = "Name of the query handler Lambda function"
  type        = string
}

variable "api_handler_log_group" {
  description = "CloudWatch log group for API handler"
  type        = string
}

# Resource Names
variable "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  type        = string
}

variable "images_bucket_name" {
  description = "Name of the images S3 bucket"
  type        = string
}

variable "glue_crawler_name" {
  description = "Name of the Glue crawler"
  type        = string
}

# Alarm Thresholds
variable "error_threshold" {
  description = "Error count threshold for Lambda alarms"
  type        = number
  default     = 5
}

variable "api_duration_threshold" {
  description = "Duration threshold for API handler in milliseconds"
  type        = number
  default     = 5000
}

variable "ingestion_duration_threshold" {
  description = "Duration threshold for ingestion handler in milliseconds"
  type        = number
  default     = 60000
}

variable "query_duration_threshold" {
  description = "Duration threshold for query handler in milliseconds"
  type        = number
  default     = 120000
}

variable "athena_timeout_threshold" {
  description = "Athena query timeout threshold in milliseconds"
  type        = number
  default     = 300000
}

variable "athena_data_scanned_threshold" {
  description = "Athena data scanned threshold in bytes (for cost control)"
  type        = number
  default     = 107374182400  # 100 GB
}

variable "access_denied_threshold" {
  description = "Access denied events threshold for security alarm"
  type        = number
  default     = 10
}

# Alarm Actions
variable "alarm_actions" {
  description = "List of ARNs to notify when alarm triggers"
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "List of ARNs to notify when alarm returns to OK"
  type        = list(string)
  default     = []
}

# SNS Topic
variable "create_sns_topic" {
  description = "Whether to create an SNS topic for alarms"
  type        = bool
  default     = true
}

variable "sns_kms_key_id" {
  description = "KMS key ID for SNS topic encryption"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
