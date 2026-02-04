variable "aws_region" {
  description = "AWS Region to deploy resources"
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Project name alias"
  type        = string
  default     = "webmarket-plus"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_password" {
  description = "Password for the RDS database"
  type        = string
  sensitive   = true
  default     = "Sup3rS3cr3tP4ssw0rd!"
}
