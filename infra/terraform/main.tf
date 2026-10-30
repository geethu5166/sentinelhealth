# SentinelHealth AWS Pilot Infrastructure
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. VPC and Subnets
resource "aws_vpc" "sentinel_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "sentinelhealth-pilot-vpc"
  }
}

# 2. RDS PostgreSQL with PostGIS
resource "aws_db_instance" "sentinel_db" {
  identifier          = "sentinelhealth-db"
  allocated_storage   = 50
  engine              = "postgres"
  engine_version      = "17.1"
  instance_class      = "db.t4g.medium"
  db_name             = "sentinelhealth"
  username            = var.db_username
  password            = var.db_password
  skip_final_snapshot = true
  storage_encrypted   = true
}

# 3. ElastiCache Redis Cluster
resource "aws_elasticache_cluster" "sentinel_redis" {
  cluster_id           = "sentinelhealth-redis"
  engine               = "redis"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}

# 4. S3 Bucket for Encrypted Aggregate Exports
resource "aws_s3_bucket" "exports_bucket" {
  bucket        = "sentinelhealth-exports-${var.environment}"
  force_destroy = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exports_encryption" {
  bucket = aws_s3_bucket.exports_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

