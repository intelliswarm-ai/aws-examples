################################################################################
# Step Functions Module - ML Pipeline Orchestration
################################################################################

locals {
  state_machine_definition = jsonencode({
    Comment = "Fraud Detection ML Pipeline"
    StartAt = "ValidateInput"
    States = {
      ValidateInput = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.orchestration_lambda_arn
          Payload = {
            "action" = "validate"
            "input.$" = "$"
          }
        }
        ResultPath = "$.validation"
        Next       = "CheckMode"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "NotifyFailure"
          ResultPath  = "$.error"
        }]
      }

      CheckMode = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.mode"
            StringEquals  = "TRAINING"
            Next          = "CreateEMRCluster"
          },
          {
            Variable      = "$.mode"
            StringEquals  = "SCORING_ONLY"
            Next          = "CreateEMRCluster"
          }
        ]
        Default = "CreateEMRCluster"
      }

      CreateEMRCluster = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:createCluster.sync"
        Parameters = {
          Name                    = "FraudDetection-Pipeline"
          ReleaseLabel            = var.emr_cluster_config.release_label
          LogUri                  = "s3://${var.emr_cluster_config.logs_bucket}/emr-logs/"
          VisibleToAllUsers       = true
          JobFlowRole             = "${var.emr_cluster_config.instance_profile}"
          ServiceRole             = "${var.emr_cluster_config.service_role}"
          Applications = [
            { Name = "Spark" },
            { Name = "Hadoop" },
            { Name = "Hive" }
          ]
          Instances = {
            Ec2SubnetId = var.emr_cluster_config.subnet_id
            EmrManagedMasterSecurityGroup = var.emr_cluster_config.master_sg_id
            EmrManagedSlaveSecurityGroup  = var.emr_cluster_config.slave_sg_id
            KeepJobFlowAliveWhenNoSteps = true
            InstanceGroups = [
              {
                Name          = "Master"
                InstanceRole  = "MASTER"
                InstanceType  = var.emr_cluster_config.master_instance_type
                InstanceCount = 1
              },
              {
                Name          = "Core"
                InstanceRole  = "CORE"
                InstanceType  = var.emr_cluster_config.core_instance_type
                InstanceCount = var.emr_cluster_config.core_instance_count
              }
            ]
          }
          AutoTerminationPolicy = {
            IdleTimeout = 3600
          }
        }
        ResultPath = "$.cluster"
        Next       = "SubmitFeatureEngineering"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "NotifyFailure"
          ResultPath  = "$.error"
        }]
      }

      SubmitFeatureEngineering = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
        Parameters = {
          "ClusterId.$" = "$.cluster.ClusterId"
          Step = {
            Name            = "Feature Engineering"
            ActionOnFailure = "CONTINUE"
            HadoopJarStep = {
              Jar = "command-runner.jar"
              Args = [
                "spark-submit",
                "--deploy-mode", "cluster",
                "--driver-memory", "4g",
                "--executor-memory", "8g",
                "--executor-cores", "4",
                "s3://${var.scripts_bucket}/spark/jobs/feature_engineering.py",
                "--input-path", "s3://${var.raw_bucket}/raw/transactions/",
                "--output-path", "s3://${var.features_bucket}/features/",
                "--date.$", "$.date"
              ]
            }
          }
        }
        ResultPath = "$.featureStep"
        Next       = "CheckTrainingMode"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "TerminateCluster"
          ResultPath  = "$.error"
        }]
      }

      CheckTrainingMode = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.mode"
            StringEquals  = "SCORING_ONLY"
            Next          = "SubmitBatchScoring"
          }
        ]
        Default = "SubmitModelTraining"
      }

      SubmitModelTraining = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
        Parameters = {
          "ClusterId.$" = "$.cluster.ClusterId"
          Step = {
            Name            = "Model Training"
            ActionOnFailure = "CONTINUE"
            HadoopJarStep = {
              Jar = "command-runner.jar"
              Args = [
                "spark-submit",
                "--deploy-mode", "cluster",
                "--driver-memory", "8g",
                "--executor-memory", "16g",
                "--executor-cores", "4",
                "s3://${var.scripts_bucket}/spark/jobs/model_training.py",
                "--input-path", "s3://${var.features_bucket}/features/",
                "--output-path", "s3://${var.models_bucket}/models/",
                "--model-version.$", "$.modelVersion"
              ]
            }
          }
        }
        ResultPath = "$.trainingStep"
        Next       = "SubmitBatchScoring"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "TerminateCluster"
          ResultPath  = "$.error"
        }]
      }

      SubmitBatchScoring = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:addStep.sync"
        Parameters = {
          "ClusterId.$" = "$.cluster.ClusterId"
          Step = {
            Name            = "Batch Scoring"
            ActionOnFailure = "CONTINUE"
            HadoopJarStep = {
              Jar = "command-runner.jar"
              Args = [
                "spark-submit",
                "--deploy-mode", "cluster",
                "--driver-memory", "4g",
                "--executor-memory", "8g",
                "--executor-cores", "4",
                "s3://${var.scripts_bucket}/spark/jobs/batch_scoring.py",
                "--features-path", "s3://${var.features_bucket}/features/",
                "--model-path", "s3://${var.models_bucket}/models/",
                "--output-path", "s3://${var.predictions_bucket}/predictions/",
                "--date.$", "$.date"
              ]
            }
          }
        }
        ResultPath = "$.scoringStep"
        Next       = "ProcessResults"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "TerminateCluster"
          ResultPath  = "$.error"
        }]
      }

      ProcessResults = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.alert_lambda_arn
          Payload = {
            "action"         = "process_results"
            "predictions_path.$" = "$.predictions_path"
            "date.$"         = "$.date"
          }
        }
        ResultPath = "$.results"
        Next       = "TerminateCluster"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "TerminateCluster"
          ResultPath  = "$.error"
        }]
      }

      TerminateCluster = {
        Type     = "Task"
        Resource = "arn:aws:states:::elasticmapreduce:terminateCluster.sync"
        Parameters = {
          "ClusterId.$" = "$.cluster.ClusterId"
        }
        Next = "CheckError"
      }

      CheckError = {
        Type = "Choice"
        Choices = [
          {
            Variable  = "$.error"
            IsPresent = true
            Next      = "NotifyFailure"
          }
        ]
        Default = "NotifySuccess"
      }

      NotifySuccess = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = var.sns_topic_arn
          Message = {
            "status"   = "SUCCESS"
            "pipeline" = "fraud-detection"
            "details.$" = "$"
          }
        }
        End = true
      }

      NotifyFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = var.sns_topic_arn
          Message = {
            "status"   = "FAILED"
            "pipeline" = "fraud-detection"
            "error.$"  = "$.error"
          }
        }
        End = true
      }
    }
  })
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.name_prefix}-fraud-detection-pipeline"
  role_arn = var.sfn_role_arn

  definition = local.state_machine_definition

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-fraud-detection-pipeline"
  })
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/vendedlogs/states/${var.name_prefix}-fraud-detection-pipeline"
  retention_in_days = 30

  tags = var.tags
}
