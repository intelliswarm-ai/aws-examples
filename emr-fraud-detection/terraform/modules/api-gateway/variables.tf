variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "ingestion_lambda_arn" {
  description = "Ingestion Lambda ARN"
  type        = string
}

variable "ingestion_lambda_name" {
  description = "Ingestion Lambda name"
  type        = string
}

variable "query_lambda_arn" {
  description = "Query Lambda ARN"
  type        = string
}

variable "query_lambda_name" {
  description = "Query Lambda name"
  type        = string
}

variable "enable_api_key" {
  description = "Enable API key requirement"
  type        = bool
  default     = false
}

variable "throttle_rate_limit" {
  description = "Rate limit per second"
  type        = number
  default     = 1000
}

variable "throttle_burst_limit" {
  description = "Burst limit"
  type        = number
  default     = 2000
}

variable "enable_access_logging" {
  description = "Enable access logging"
  type        = bool
  default     = true
}

variable "access_log_retention_days" {
  description = "Access log retention days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
