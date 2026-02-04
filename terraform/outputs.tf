output "alb_dns_name" {
  description = "DNS name of the Load Balancer"
  value       = aws_lb.web.dns_name
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.assets.id
}

output "rds_endpoint" {
  description = "RDS Endpoint"
  value       = aws_db_instance.default.endpoint
}
