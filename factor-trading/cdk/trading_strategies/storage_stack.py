from aws_cdk import (
    NestedStack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_glue as glue,
    aws_athena as athena,
)
from constructs import Construct

class StorageStack(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for backtest results
        # CDK will generate unique names automatically
        results_bucket = s3.Bucket(
            self, "BacktestResultsBucket",
            removal_policy=RemovalPolicy.RETAIN,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True
        )

        # Create S3 bucket for MWAA DAGs and plugins
        dags_bucket = s3.Bucket(
            self, "MwaaDagsBucket",
            removal_policy=RemovalPolicy.RETAIN,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True
        )

        # Create S3 bucket for Athena query results
        athena_results_bucket = s3.Bucket(
            self, "AthenaResultsBucket",
            removal_policy=RemovalPolicy.RETAIN,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True
        )

        # Create Athena workgroup
        athena_workgroup = athena.CfnWorkGroup(
            self, "TradingStrategiesWorkgroup",
            name="trading-strategies",
            description="Workgroup for querying trading strategies backtest results",
            recursive_delete_option=True,
            state="ENABLED",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results_bucket.bucket_name}/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3"
                    )
                )
            )
        )

        # Export resources
        self.results_bucket = results_bucket
        self.dags_bucket = dags_bucket
        self.athena_results_bucket = athena_results_bucket
        self.athena_workgroup = athena_workgroup
