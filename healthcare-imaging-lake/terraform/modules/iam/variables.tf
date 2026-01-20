variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "images_bucket_arn" {
  description = "ARN of the images S3 bucket"
  type        = string
}

variable "metadata_bucket_arn" {
  description = "ARN of the metadata S3 bucket"
  type        = string
}

variable "results_bucket_arn" {
  description = "ARN of the results S3 bucket"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key"
  type        = string
}

variable "glue_database" {
  description = "Name of the Glue database"
  type        = string
}

variable "enable_lakeformation" {
  description = "Enable Lake Formation resources"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
