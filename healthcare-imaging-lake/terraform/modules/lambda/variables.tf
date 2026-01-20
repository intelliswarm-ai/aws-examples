variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  type        = string
}

variable "deployment_bucket" {
  description = "S3 bucket containing Lambda deployment package"
  type        = string
}

variable "deployment_key" {
  description = "S3 key for Lambda deployment package"
  type        = string
}

variable "images_bucket_name" {
  description = "Name of the images S3 bucket"
  type        = string
}

variable "metadata_bucket_name" {
  description = "Name of the metadata S3 bucket"
  type        = string
}

variable "results_bucket_name" {
  description = "Name of the results S3 bucket"
  type        = string
}

variable "kms_key_id" {
  description = "ID of the KMS key for encryption"
  type        = string
}

variable "glue_database_name" {
  description = "Name of the Glue database"
  type        = string
}

variable "glue_crawler_name" {
  description = "Name of the Glue crawler"
  type        = string
}

variable "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  type        = string
}

variable "enable_lakeformation" {
  description = "Whether Lake Formation is enabled"
  type        = bool
  default     = true
}

variable "subnet_ids" {
  description = "Subnet IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

variable "logs_kms_key_arn" {
  description = "ARN of KMS key for CloudWatch Logs encryption"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 365
}

variable "log_level" {
  description = "Log level for Lambda functions"
  type        = string
  default     = "INFO"
}

# Timeout and Memory Configuration
variable "api_timeout" {
  description = "Timeout for API handler in seconds"
  type        = number
  default     = 30
}

variable "api_memory_size" {
  description = "Memory size for API handler in MB"
  type        = number
  default     = 512
}

variable "ingestion_timeout" {
  description = "Timeout for ingestion handler in seconds"
  type        = number
  default     = 300
}

variable "ingestion_memory_size" {
  description = "Memory size for ingestion handler in MB"
  type        = number
  default     = 1024
}

variable "catalog_timeout" {
  description = "Timeout for catalog handler in seconds"
  type        = number
  default     = 60
}

variable "catalog_memory_size" {
  description = "Memory size for catalog handler in MB"
  type        = number
  default     = 256
}

variable "query_timeout" {
  description = "Timeout for query handler in seconds"
  type        = number
  default     = 300
}

variable "query_memory_size" {
  description = "Memory size for query handler in MB"
  type        = number
  default     = 512
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
