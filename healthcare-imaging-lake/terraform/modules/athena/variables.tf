variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "workgroup_name" {
  description = "Name of the Athena workgroup"
  type        = string
}

variable "database_name" {
  description = "Name of the Glue database"
  type        = string
  default     = "healthcare_imaging"
}

variable "results_bucket_name" {
  description = "Name of the results S3 bucket"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  type        = string
}

variable "bytes_scanned_cutoff" {
  description = "Maximum bytes scanned per query"
  type        = number
  default     = 107374182400  # 100 GB
}

variable "query_timeout" {
  description = "Query timeout in seconds"
  type        = number
  default     = 300
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
