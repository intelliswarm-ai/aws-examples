################################################################################
# S3 Module - Encrypted Storage for Healthcare Imaging
################################################################################

# Images Bucket
resource "aws_s3_bucket" "images" {
  bucket = var.images_bucket_name

  tags = merge(var.tags, {
    Name    = var.images_bucket_name
    Purpose = "medical-images"
  })
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "images" {
  bucket = aws_s3_bucket.images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    id     = "archive-old-images"
    status = "Enabled"

    transition {
      days          = var.lifecycle_rules.transition_to_ia_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.lifecycle_rules.transition_to_glacier_days
      storage_class = "GLACIER_IR"
    }
  }
}

# Metadata Bucket
resource "aws_s3_bucket" "metadata" {
  bucket = var.metadata_bucket_name

  tags = merge(var.tags, {
    Name    = var.metadata_bucket_name
    Purpose = "metadata"
  })
}

resource "aws_s3_bucket_versioning" "metadata" {
  bucket = aws_s3_bucket.metadata.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "metadata" {
  bucket = aws_s3_bucket.metadata.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "metadata" {
  bucket = aws_s3_bucket.metadata.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Results Bucket
resource "aws_s3_bucket" "results" {
  bucket = var.results_bucket_name

  tags = merge(var.tags, {
    Name    = var.results_bucket_name
    Purpose = "query-results"
  })
}

resource "aws_s3_bucket_versioning" "results" {
  bucket = aws_s3_bucket.results.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "results" {
  bucket = aws_s3_bucket.results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  rule {
    id     = "cleanup-old-results"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# Access Logging Bucket (conditional)
resource "aws_s3_bucket" "access_logs" {
  count  = var.enable_access_logging ? 1 : 0
  bucket = "${var.name_prefix}-access-logs"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-access-logs"
    Purpose = "access-logging"
  })
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  count  = var.enable_access_logging ? 1 : 0
  bucket = aws_s3_bucket.access_logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "images" {
  count         = var.enable_access_logging ? 1 : 0
  bucket        = aws_s3_bucket.images.id
  target_bucket = aws_s3_bucket.access_logs[0].id
  target_prefix = "images/"
}

resource "aws_s3_bucket_logging" "metadata" {
  count         = var.enable_access_logging ? 1 : 0
  bucket        = aws_s3_bucket.metadata.id
  target_bucket = aws_s3_bucket.access_logs[0].id
  target_prefix = "metadata/"
}
