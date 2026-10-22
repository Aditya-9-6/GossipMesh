terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "GossipMesh"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# 1. VPC Network & Subnets
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "gossipmesh-vpc-${var.environment}" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  map_public_ip_on_launch = true
  tags = { Name = "gossipmesh-public-${count.index}-${var.environment}" }
}

resource "aws_subnet" "private" {
  count      = 2
  vpc_id     = aws_vpc.main.id
  cidr_block = cidrsubnet(var.vpc_cidr, 4, count.index + 2)
  tags = { Name = "gossipmesh-private-${count.index}-${var.environment}" }
}

# 2. Managed PostgreSQL with pgvector
resource "aws_db_instance" "postgres" {
  identifier          = "gossipmesh-db-${var.environment}"
  engine              = "postgres"
  engine_version      = "16.1"
  instance_class      = var.db_instance_class
  allocated_storage   = 50
  storage_encrypted   = true
  username            = "gossipmesh_admin"
  manage_master_user_password = true
  skip_final_snapshot = var.environment != "production"
  backup_retention_period = 30
}

# 3. Managed ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "gossipmesh-redis-${var.environment}"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}

# 4. Encrypted S3 Artifact Storage
resource "aws_s3_bucket" "artifacts" {
  bucket        = "gossipmesh-artifacts-${var.environment}"
  force_destroy = var.environment != "production"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 5. Secrets Manager
resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "gossipmesh/${var.environment}/credentials"
  description = "GossipMesh LLM provider keys and webhook secrets"
}
