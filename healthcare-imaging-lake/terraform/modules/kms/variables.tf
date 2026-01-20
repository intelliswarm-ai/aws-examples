variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "enable_key_rotation" {
  description = "Enable automatic key rotation"
  type        = bool
  default     = true
}

variable "deletion_window" {
  description = "Key deletion window in days"
  type        = number
  default     = 30
}

variable "multi_region" {
  description = "Enable multi-region key"
  type        = bool
  default     = false
}

variable "admin_role_arns" {
  description = "ARNs of roles that can administer the key"
  type        = list(string)
  default     = []
}

variable "usage_role_arns" {
  description = "ARNs of roles that can use the key"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
