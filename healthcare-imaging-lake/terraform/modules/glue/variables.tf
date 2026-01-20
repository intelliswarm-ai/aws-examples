variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "database_name" {
  description = "Name of the Glue database"
  type        = string
}

variable "imaging_table_name" {
  description = "Name of the imaging metadata table"
  type        = string
}

variable "clinical_table_name" {
  description = "Name of the clinical records table"
  type        = string
}

variable "metadata_bucket_name" {
  description = "Name of the metadata S3 bucket"
  type        = string
}

variable "glue_role_arn" {
  description = "ARN of the Glue service role"
  type        = string
}

variable "crawler_schedule" {
  description = "Cron expression for crawler schedule"
  type        = string
  default     = "cron(0 */6 * * ? *)"
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
