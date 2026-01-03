variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "stream_name" {
  description = "Name of the Kinesis stream"
  type        = string
}

variable "shard_count" {
  description = "Number of shards"
  type        = number
  default     = 4
}

variable "retention_period" {
  description = "Data retention period in hours"
  type        = number
  default     = 24
}

variable "stream_mode" {
  description = "Stream mode (PROVISIONED or ON_DEMAND)"
  type        = string
  default     = "PROVISIONED"
}

variable "iterator_age_threshold" {
  description = "Iterator age threshold in milliseconds"
  type        = number
  default     = 60000
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
