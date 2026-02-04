resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", aws_autoscaling_group.app.name]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "CPU Moyen (Auto Scaling Group)"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/AutoScaling", "GroupInServiceInstances", "AutoScalingGroupName", aws_autoscaling_group.app.name]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Nombre d'Instances Actives"
          color  = "#d62728"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.web.arn_suffix]
          ]
          period  = 60
          stat    = "Sum"
          region  = var.aws_region
          title   = "Trafic HTTP (Requêtes sur l'ALB)"
          view    = "timeSeries"
          stacked = false
        }
      }
    ]
  })
}
