variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "enable_point_in_time" {
  description = "Enable point-in-time recovery"
  type        = bool
  default     = false
}

variable "alerts_ttl_days" {
  description = "TTL in days for alerts"
  type        = number
  default     = 90
}

variable "predictions_ttl_days" {
  description = "TTL in days for predictions"
  type        = number
  default     = 365
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
