resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group-v2"
  subnet_ids = aws_subnet.private_db[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "default" {
  identifier        = "${var.project_name}-db-v2"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = "db.t3.micro" # Cost effective for demo, use larger for prod
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "webmarket"
  username = "adminuser"
  password = var.db_password # Sensitive variable

  multi_az               = true # Requirement for High Availability
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  skip_final_snapshot = true # For demo/dev only. Set to false for PROD!

  tags = {
    Name = "${var.project_name}-rds"
  }
}
