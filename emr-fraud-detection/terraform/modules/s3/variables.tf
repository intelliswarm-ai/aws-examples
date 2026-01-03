variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "raw_bucket_name" {
  description = "Name for raw data bucket"
  type        = string
}

variable "features_bucket_name" {
  description = "Name for features bucket"
  type        = string
}

variable "models_bucket_name" {
  description = "Name for models bucket"
  type        = string
}

variable "predictions_bucket_name" {
  description = "Name for predictions bucket"
  type        = string
}

variable "scripts_bucket_name" {
  description = "Name for scripts bucket"
  type        = string
}

variable "logs_bucket_name" {
  description = "Name for logs bucket"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning on buckets"
  type        = bool
  default     = false
}

variable "lifecycle_glacier_days" {
  description = "Days before transitioning to Glacier"
  type        = number
  default     = 90
}

variable "lifecycle_expire_days" {
  description = "Days before expiring objects"
  type        = number
  default     = 365
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
