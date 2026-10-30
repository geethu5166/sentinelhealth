variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "ap-south-1"  # Mumbai / India default
}

variable "environment" {
  description = "Deployment tier (pilot or staging)"
  type        = string
  default     = "pilot"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "sentinel"
}

variable "db_password" {
  description = "RDS master password (managed via AWS Secrets Manager in production)"
  type        = string
  sensitive   = true
}

