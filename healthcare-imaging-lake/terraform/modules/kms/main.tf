################################################################################
# KMS Module - Customer Managed Key for HIPAA Encryption
################################################################################

resource "aws_kms_key" "main" {
  description             = "${var.name_prefix} - HIPAA compliant encryption key"
  deletion_window_in_days = var.deletion_window
  enable_key_rotation     = var.enable_key_rotation
  multi_region            = var.multi_region

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "${var.name_prefix}-key-policy"
    Statement = concat(
      [
        {
          Sid    = "EnableRootAccountAccess"
          Effect = "Allow"
          Principal = {
            AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
          }
          Action   = "kms:*"
          Resource = "*"
        }
      ],
      length(var.admin_role_arns) > 0 ? [
        {
          Sid    = "AllowKeyAdministration"
          Effect = "Allow"
          Principal = {
            AWS = var.admin_role_arns
          }
          Action = [
            "kms:Create*",
            "kms:Describe*",
            "kms:Enable*",
            "kms:List*",
            "kms:Put*",
            "kms:Update*",
            "kms:Revoke*",
            "kms:Disable*",
            "kms:Get*",
            "kms:Delete*",
            "kms:TagResource",
            "kms:UntagResource",
            "kms:ScheduleKeyDeletion",
            "kms:CancelKeyDeletion"
          ]
          Resource = "*"
        }
      ] : [],
      length(var.usage_role_arns) > 0 ? [
        {
          Sid    = "AllowKeyUsage"
          Effect = "Allow"
          Principal = {
            AWS = var.usage_role_arns
          }
          Action = [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:DescribeKey"
          ]
          Resource = "*"
        }
      ] : [],
      [
        {
          Sid    = "AllowAWSServices"
          Effect = "Allow"
          Principal = {
            Service = [
              "s3.amazonaws.com",
              "glue.amazonaws.com",
              "athena.amazonaws.com",
              "logs.amazonaws.com",
              "lambda.amazonaws.com"
            ]
          }
          Action = [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:DescribeKey"
          ]
          Resource = "*"
          Condition = {
            StringEquals = {
              "kms:CallerAccount" = data.aws_caller_identity.current.account_id
            }
          }
        }
      ]
    )
  })

  tags = merge(var.tags, {
    Name       = "${var.name_prefix}-kms-key"
    Compliance = "HIPAA"
  })
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.name_prefix}"
  target_key_id = aws_kms_key.main.key_id
}

data "aws_caller_identity" "current" {}
