################################################################################
# EMR Module - Spark Clusters
################################################################################

locals {
  spark_config = jsonencode([
    {
      Classification = "spark-defaults"
      Properties = {
        "spark.dynamicAllocation.enabled"          = "true"
        "spark.shuffle.service.enabled"            = "true"
        "spark.sql.adaptive.enabled"               = "true"
        "spark.sql.adaptive.coalescePartitions.enabled" = "true"
        "spark.serializer"                         = "org.apache.spark.serializer.KryoSerializer"
        "spark.sql.parquet.compression.codec"      = "snappy"
        "spark.hadoop.fs.s3a.connection.maximum"   = "200"
        "spark.hadoop.fs.s3a.fast.upload"          = "true"
      }
    },
    {
      Classification = "spark-hive-site"
      Properties = {
        "hive.metastore.client.factory.class" = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
      }
    },
    {
      Classification = "yarn-site"
      Properties = {
        "yarn.nodemanager.vmem-check-enabled" = "false"
        "yarn.nodemanager.pmem-check-enabled" = "false"
      }
    }
  ])
}

################################################################################
# Batch Processing Cluster (Transient - created by Step Functions)
################################################################################

# Note: The actual cluster is created by Step Functions
# This resource defines the cluster configuration template

resource "aws_emr_cluster" "batch" {
  count = var.environment == "dev" ? 0 : 0  # Disabled - managed by Step Functions

  name          = "${var.name_prefix}-batch-cluster"
  release_label = var.release_label
  applications  = ["Spark", "Hadoop", "Hive"]

  service_role = var.emr_service_role_arn

  ec2_attributes {
    instance_profile                  = var.emr_instance_profile
    subnet_id                         = var.subnet_id
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_slave.id
  }

  master_instance_group {
    instance_type  = var.master_instance_type
    instance_count = 1

    ebs_config {
      size                 = 100
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  core_instance_group {
    instance_type  = var.core_instance_type
    instance_count = var.core_instance_count

    ebs_config {
      size                 = 200
      type                 = "gp3"
      volumes_per_instance = 2
    }
  }

  log_uri = "s3://${var.logs_bucket}/emr-logs/"

  configurations_json = local.spark_config

  auto_termination_policy {
    idle_timeout = 3600
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-batch-cluster"
    Type = "batch"
  })
}

################################################################################
# Streaming Cluster (Long-running for Structured Streaming)
################################################################################

resource "aws_emr_cluster" "streaming" {
  count = var.streaming_enabled ? 1 : 0

  name          = "${var.name_prefix}-streaming-cluster"
  release_label = var.release_label
  applications  = ["Spark", "Hadoop", "Hive"]

  service_role = var.emr_service_role_arn

  ec2_attributes {
    instance_profile                  = var.emr_instance_profile
    subnet_id                         = var.subnet_id
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_slave.id
  }

  master_instance_group {
    instance_type  = var.streaming_master_instance_type
    instance_count = 1

    ebs_config {
      size                 = 100
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  core_instance_group {
    instance_type  = var.streaming_core_instance_type
    instance_count = var.streaming_core_instance_count

    ebs_config {
      size                 = 200
      type                 = "gp3"
      volumes_per_instance = 2
    }
  }

  log_uri = "s3://${var.logs_bucket}/emr-logs/"

  configurations_json = local.spark_config

  keep_job_flow_alive_when_no_steps = true
  termination_protection            = var.environment == "prod"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-streaming-cluster"
    Type = "streaming"
  })

  lifecycle {
    ignore_changes = [
      step,
      configurations_json,
    ]
  }
}

################################################################################
# Security Groups
################################################################################

resource "aws_security_group" "emr_master" {
  name_prefix = "${var.name_prefix}-emr-master-"
  description = "EMR Master security group"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-emr-master-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "emr_slave" {
  name_prefix = "${var.name_prefix}-emr-slave-"
  description = "EMR Slave security group"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-emr-slave-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Allow all traffic between master and slave nodes
resource "aws_security_group_rule" "emr_master_ingress_self" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "-1"
  security_group_id        = aws_security_group.emr_master.id
  source_security_group_id = aws_security_group.emr_master.id
}

resource "aws_security_group_rule" "emr_master_ingress_slave" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "-1"
  security_group_id        = aws_security_group.emr_master.id
  source_security_group_id = aws_security_group.emr_slave.id
}

resource "aws_security_group_rule" "emr_slave_ingress_self" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "-1"
  security_group_id        = aws_security_group.emr_slave.id
  source_security_group_id = aws_security_group.emr_slave.id
}

resource "aws_security_group_rule" "emr_slave_ingress_master" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "-1"
  security_group_id        = aws_security_group.emr_slave.id
  source_security_group_id = aws_security_group.emr_master.id
}
