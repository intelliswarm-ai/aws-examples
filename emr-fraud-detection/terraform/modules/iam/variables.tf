variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "raw_bucket_arn" {
  description = "ARN of the raw data bucket"
  type        = string
}

variable "features_bucket_arn" {
  description = "ARN of the features bucket"
  type        = string
}

variable "models_bucket_arn" {
  description = "ARN of the models bucket"
  type        = string
}

variable "predictions_bucket_arn" {
  description = "ARN of the predictions bucket"
  type        = string
}

variable "scripts_bucket_arn" {
  description = "ARN of the scripts bucket"
  type        = string
}

variable "logs_bucket_arn" {
  description = "ARN of the logs bucket"
  type        = string
}

variable "kinesis_stream_arn" {
  description = "ARN of the Kinesis stream"
  type        = string
}

variable "dynamodb_alerts_arn" {
  description = "ARN of the alerts DynamoDB table"
  type        = string
}

variable "dynamodb_predictions_arn" {
  description = "ARN of the predictions DynamoDB table"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
