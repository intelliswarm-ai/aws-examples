################################################################################
# Healthcare Imaging Data Lake - Terraform Variables
################################################################################

################################################################################
# Project Configuration
################################################################################

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "healthcare-imaging-lake"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

################################################################################
# S3 Configuration
################################################################################

variable "images_bucket_name" {
  description = "Name for the images S3 bucket (auto-generated if empty)"
  type        = string
  default     = ""
}

variable "metadata_bucket_name" {
  description = "Name for the metadata S3 bucket (auto-generated if empty)"
  type        = string
  default     = ""
}

variable "results_bucket_name" {
  description = "Name for the query results S3 bucket (auto-generated if empty)"
  type        = string
  default     = ""
}

variable "enable_s3_versioning" {
  description = "Enable versioning on S3 buckets"
  type        = bool
  default     = true
}

variable "enable_s3_access_logging" {
  description = "Enable access logging on S3 buckets"
  type        = bool
  default     = true
}

variable "s3_lifecycle_rules" {
  description = "S3 lifecycle rules configuration"
  type = object({
    transition_to_ia_days      = number
    transition_to_glacier_days = number
    expiration_days            = number
  })
  default = {
    transition_to_ia_days      = 90
    transition_to_glacier_days = 365
    expiration_days            = 2555  # 7 years for HIPAA
  }
}

################################################################################
# KMS Configuration
################################################################################

variable "kms_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30

  validation {
    condition     = var.kms_deletion_window >= 7 && var.kms_deletion_window <= 30
    error_message = "KMS deletion window must be between 7 and 30 days."
  }
}

variable "kms_admin_arns" {
  description = "ARNs of IAM principals that can administer the KMS key"
  type        = list(string)
  default     = []
}

variable "kms_usage_arns" {
  description = "Additional ARNs that can use the KMS key for encryption"
  type        = list(string)
  default     = []
}

################################################################################
# Glue Configuration
################################################################################

variable "glue_database" {
  description = "Name of the Glue database"
  type        = string
  default     = "healthcare_imaging"
}

variable "imaging_table_name" {
  description = "Name of the imaging metadata table"
  type        = string
  default     = "imaging_metadata"
}

variable "clinical_table_name" {
  description = "Name of the clinical records table"
  type        = string
  default     = "clinical_records"
}

variable "glue_crawler_schedule" {
  description = "Cron expression for Glue crawler schedule"
  type        = string
  default     = "cron(0 */6 * * ? *)"  # Every 6 hours
}

################################################################################
# Lake Formation Configuration
################################################################################

variable "enable_lakeformation" {
  description = "Enable Lake Formation for fine-grained access control"
  type        = bool
  default     = true
}

variable "lakeformation_admin_arns" {
  description = "ARNs of Lake Formation administrators"
  type        = list(string)
  default     = []
}

################################################################################
# Athena Configuration
################################################################################

variable "athena_workgroup" {
  description = "Name of the Athena workgroup"
  type        = string
  default     = "healthcare_analytics"
}

variable "athena_query_timeout" {
  description = "Athena query timeout in seconds"
  type        = number
  default     = 300
}

variable "athena_bytes_limit" {
  description = "Maximum bytes scanned per query (cost control)"
  type        = number
  default     = 107374182400  # 100 GB
}

################################################################################
# Lambda Configuration
################################################################################

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be DEBUG, INFO, WARNING, or ERROR."
  }
}

################################################################################
# CloudWatch Configuration
################################################################################

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "enable_cloudwatch_dashboards" {
  description = "Create CloudWatch dashboards"
  type        = bool
  default     = true
}
