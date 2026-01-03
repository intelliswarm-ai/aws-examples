################################################################################
# EMR Spark Fraud Detection Pipeline - Variables
################################################################################

# General
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "fraud-detection"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# VPC
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT gateway (cost savings for non-prod)"
  type        = bool
  default     = true
}

# Kinesis
variable "kinesis_shard_count" {
  description = "Number of shards for Kinesis stream"
  type        = number
  default     = 4

  validation {
    condition     = var.kinesis_shard_count >= 1 && var.kinesis_shard_count <= 500
    error_message = "Shard count must be between 1 and 500."
  }
}

variable "kinesis_retention_hours" {
  description = "Kinesis data retention period in hours"
  type        = number
  default     = 24

  validation {
    condition     = var.kinesis_retention_hours >= 24 && var.kinesis_retention_hours <= 8760
    error_message = "Retention period must be between 24 and 8760 hours."
  }
}

# EMR - Batch Cluster
variable "emr_release_label" {
  description = "EMR release label"
  type        = string
  default     = "emr-7.0.0"
}

variable "emr_master_instance_type" {
  description = "Instance type for EMR master node"
  type        = string
  default     = "m5.xlarge"
}

variable "emr_core_instance_type" {
  description = "Instance type for EMR core nodes"
  type        = string
  default     = "m5.2xlarge"
}

variable "emr_core_instance_count" {
  description = "Number of EMR core instances"
  type        = number
  default     = 2

  validation {
    condition     = var.emr_core_instance_count >= 1 && var.emr_core_instance_count <= 50
    error_message = "Core instance count must be between 1 and 50."
  }
}

variable "emr_use_spot" {
  description = "Use spot instances for EMR task nodes"
  type        = bool
  default     = true
}

variable "emr_spot_bid_percentage" {
  description = "Spot bid percentage of on-demand price"
  type        = number
  default     = 50

  validation {
    condition     = var.emr_spot_bid_percentage >= 1 && var.emr_spot_bid_percentage <= 100
    error_message = "Spot bid percentage must be between 1 and 100."
  }
}

# EMR - Streaming Cluster
variable "streaming_enabled" {
  description = "Enable streaming EMR cluster for real-time scoring"
  type        = bool
  default     = true
}

variable "streaming_master_instance_type" {
  description = "Instance type for streaming EMR master node"
  type        = string
  default     = "m5.xlarge"
}

variable "streaming_core_instance_type" {
  description = "Instance type for streaming EMR core nodes"
  type        = string
  default     = "m5.xlarge"
}

variable "streaming_core_instance_count" {
  description = "Number of streaming EMR core instances"
  type        = number
  default     = 2
}

# ML Configuration
variable "fraud_threshold" {
  description = "Threshold for classifying as fraud (0.0-1.0)"
  type        = number
  default     = 0.7

  validation {
    condition     = var.fraud_threshold >= 0 && var.fraud_threshold <= 1
    error_message = "Fraud threshold must be between 0 and 1."
  }
}

variable "suspicious_threshold" {
  description = "Threshold for classifying as suspicious (0.0-1.0)"
  type        = number
  default     = 0.5

  validation {
    condition     = var.suspicious_threshold >= 0 && var.suspicious_threshold <= 1
    error_message = "Suspicious threshold must be between 0 and 1."
  }
}

variable "model_version" {
  description = "ML model version to use"
  type        = string
  default     = "v1.0"
}

# API Configuration
variable "enable_api_key" {
  description = "Require API key for API Gateway"
  type        = bool
  default     = true
}

variable "api_rate_limit" {
  description = "API Gateway rate limit (requests per second)"
  type        = number
  default     = 1000
}

variable "api_burst_limit" {
  description = "API Gateway burst limit"
  type        = number
  default     = 2000
}

# Alerting
variable "fraud_alert_email" {
  description = "Email address for fraud alerts"
  type        = string
  default     = ""
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "enable_sms_alerts" {
  description = "Enable SMS alerts for critical fraud"
  type        = bool
  default     = false
}

variable "sms_phone_number" {
  description = "Phone number for SMS alerts (E.164 format)"
  type        = string
  default     = ""
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}
