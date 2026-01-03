variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EMR cluster"
  type        = string
}

variable "emr_service_role_arn" {
  description = "EMR service role ARN"
  type        = string
}

variable "emr_ec2_role_arn" {
  description = "EMR EC2 role ARN"
  type        = string
}

variable "emr_instance_profile" {
  description = "EMR EC2 instance profile name"
  type        = string
}

variable "emr_autoscaling_role_arn" {
  description = "EMR autoscaling role ARN"
  type        = string
}

variable "logs_bucket" {
  description = "S3 bucket for EMR logs"
  type        = string
}

variable "scripts_bucket" {
  description = "S3 bucket for scripts"
  type        = string
}

# Batch cluster settings
variable "release_label" {
  description = "EMR release label"
  type        = string
  default     = "emr-7.0.0"
}

variable "master_instance_type" {
  description = "Master instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "core_instance_type" {
  description = "Core instance type"
  type        = string
  default     = "m5.2xlarge"
}

variable "core_instance_count" {
  description = "Number of core instances"
  type        = number
  default     = 2
}

variable "use_spot_instances" {
  description = "Use spot instances for task nodes"
  type        = bool
  default     = true
}

variable "spot_bid_percentage" {
  description = "Spot bid percentage"
  type        = number
  default     = 50
}

# Streaming cluster settings
variable "streaming_enabled" {
  description = "Enable streaming cluster"
  type        = bool
  default     = true
}

variable "streaming_master_instance_type" {
  description = "Streaming master instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "streaming_core_instance_type" {
  description = "Streaming core instance type"
  type        = string
  default     = "m5.xlarge"
}

variable "streaming_core_instance_count" {
  description = "Streaming core instance count"
  type        = number
  default     = 2
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
