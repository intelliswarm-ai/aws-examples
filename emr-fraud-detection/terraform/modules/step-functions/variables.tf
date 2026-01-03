variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "sfn_role_arn" {
  description = "Step Functions execution role ARN"
  type        = string
}

variable "emr_cluster_config" {
  description = "EMR cluster configuration"
  type = object({
    release_label        = string
    master_instance_type = string
    core_instance_type   = string
    core_instance_count  = number
    logs_bucket          = string
    scripts_bucket       = string
    subnet_id            = string
    master_sg_id         = string
    slave_sg_id          = string
    use_spot             = bool
    spot_bid_percentage  = number
    service_role         = optional(string, "EMR_DefaultRole")
    instance_profile     = optional(string, "EMR_EC2_DefaultRole")
  })
}

variable "orchestration_lambda_arn" {
  description = "Orchestration Lambda ARN"
  type        = string
}

variable "alert_lambda_arn" {
  description = "Alert Lambda ARN"
  type        = string
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
}

variable "scripts_bucket" {
  description = "S3 bucket for Spark scripts"
  type        = string
}

variable "raw_bucket" {
  description = "S3 bucket for raw data"
  type        = string
}

variable "features_bucket" {
  description = "S3 bucket for features"
  type        = string
}

variable "models_bucket" {
  description = "S3 bucket for models"
  type        = string
}

variable "predictions_bucket" {
  description = "S3 bucket for predictions"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
