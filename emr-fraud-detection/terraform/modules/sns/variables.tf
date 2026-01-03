variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "fraud_alert_email" {
  description = "Email for fraud alerts"
  type        = string
  default     = ""
}

variable "enable_sms_alerts" {
  description = "Enable SMS alerts"
  type        = bool
  default     = false
}

variable "sms_phone_number" {
  description = "Phone number for SMS alerts"
  type        = string
  default     = ""
}

variable "lambda_dlq_enabled" {
  description = "Enable Lambda DLQ topic"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
