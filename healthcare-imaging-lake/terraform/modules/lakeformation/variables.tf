variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "database_name" {
  description = "Name of the Glue database"
  type        = string
}

variable "admin_arns" {
  description = "ARNs of Lake Formation administrators"
  type        = list(string)
  default     = []
}

variable "images_bucket_arn" {
  description = "ARN of the images S3 bucket"
  type        = string
}

variable "metadata_bucket_arn" {
  description = "ARN of the metadata S3 bucket"
  type        = string
}

variable "lakeformation_role_arn" {
  description = "ARN of the Lake Formation service role"
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

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
