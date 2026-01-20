variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "images_bucket_name" {
  description = "Name for the images bucket"
  type        = string
}

variable "metadata_bucket_name" {
  description = "Name for the metadata bucket"
  type        = string
}

variable "results_bucket_name" {
  description = "Name for the results bucket"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
}

variable "enable_versioning" {
  description = "Enable bucket versioning"
  type        = bool
  default     = true
}

variable "enable_access_logging" {
  description = "Enable access logging"
  type        = bool
  default     = true
}

variable "lifecycle_rules" {
  description = "Lifecycle rules configuration"
  type = object({
    transition_to_ia_days      = number
    transition_to_glacier_days = number
    expiration_days            = number
  })
  default = {
    transition_to_ia_days      = 90
    transition_to_glacier_days = 365
    expiration_days            = 2555
  }
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
