"""
MWAA Stack for the Airflow Backtest Framework.

This module defines an MWAA Stack that creates an Amazon Managed Workflows for Apache Airflow
environment with support for existing VPC reuse, S3 bucket for DAG storage, and necessary 
permissions to interact with AWS Batch.
"""

from typing import Optional
from aws_cdk import (
    NestedStack,
    RemovalPolicy,
    CfnOutput,
    Fn,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_mwaa as mwaa,
    aws_logs as logs,
)
from constructs import Construct


class MwaaStack(NestedStack):
    """
    MWAA Stack for creating an Amazon MWAA environment for the Airflow Backtest Framework.
    
    This stack creates:
    - Uses existing VPC or creates a new one
    - Uses existing S3 bucket for DAGs or creates a new one
    - IAM roles with permissions to interact with AWS Batch
    - Security groups for the MWAA environment
    - The MWAA environment itself
    """

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        vpc: Optional[ec2.IVpc] = None,
        dags_bucket: Optional[s3.IBucket] = None,
        **kwargs
    ) -> None:
        """
        Initialize the MWAA Stack.
        
        Args:
            scope: The scope in which to define this construct
            construct_id: The scoped construct ID
            vpc: Optional existing VPC to use. If not provided, a new VPC will be created
            dags_bucket: Optional existing S3 bucket for DAGs. If not provided, a new bucket will be created
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Use existing VPC or create new one
        if vpc is None:
            # Create VPC with public and private subnets
            vpc = ec2.Vpc(
                self, "MwaaVpc",
                max_azs=2,
                nat_gateways=1,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24
                    ),
                    ec2.SubnetConfiguration(
                        name="private",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                        cidr_mask=24
                    )
                ]
            )
            print("Created new VPC for MWAA environment")
        else:
            print(f"Using existing VPC for MWAA environment: {vpc.vpc_id}")
        
        self.vpc = vpc
        
        # Use existing S3 bucket or create new one
        if dags_bucket is None:
            # Create S3 bucket for DAGs and requirements (without deployment)
            dags_bucket = s3.Bucket(
                self, "MwaaDagsBucket",
                removal_policy=RemovalPolicy.DESTROY,
                auto_delete_objects=True,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                versioned=True,
                enforce_ssl=True,
            )
            print("Created new S3 bucket for MWAA DAGs")
        else:
            print(f"Using existing S3 bucket for MWAA DAGs: {dags_bucket.bucket_name}")
        
        self.dags_bucket = dags_bucket
        
        # Create security group for MWAA
        security_group = ec2.SecurityGroup(
            self, "MwaaSecurityGroup",
            vpc=self.vpc,
            description="Security group for MWAA environment",
            allow_all_outbound=True,
        )
        
        # Add self-referencing rule for MWAA components to communicate
        security_group.add_ingress_rule(
            peer=security_group,
            connection=ec2.Port.all_traffic(),
            description="Allow all traffic within the security group",
        )
        
        # Create IAM execution role for MWAA with necessary permissions
        # Use the correct service principal for MWAA
        execution_role = iam.Role(
            self, "MwaaExecutionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("airflow.amazonaws.com"),
                iam.ServicePrincipal("airflow-env.amazonaws.com")
            ),
            description="Execution role for MWAA environment",
        )
        
        # Add MWAA service permissions
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "airflow:PublishMetrics",
                    "airflow:CreateWebLoginToken",
                    "s3:ListAllMyBuckets",
                    "s3:GetBucketLocation",
                    "logs:DescribeLogGroups",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                    "logs:DescribeLogStreams",
                    "logs:GetLogRecord",
                    "logs:FilterLogEvents",
                    "cloudwatch:PutMetricData",
                    "sqs:ChangeMessageVisibility",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:ReceiveMessage",
                    "sqs:SendMessage",
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:GenerateDataKey*",
                    "kms:Encrypt",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            )
        )
        
        # Add permissions to interact with AWS Batch
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "batch:SubmitJob",
                    "batch:DescribeJobs",
                    "batch:TerminateJob",
                    "batch:CancelJob",
                    "batch:ListJobs",
                    "batch:DescribeJobQueues",
                    "batch:DescribeJobDefinitions",
                    "batch:DescribeComputeEnvironments",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            )
        )
        
        # Add permissions to access S3 bucket
        self.dags_bucket.grant_read_write(execution_role)
        
        # Create MWAA environment without requirements_s3_path
        environment = mwaa.CfnEnvironment(
            self, "MwaaEnvironment",
            name="TradingStrategiesMwaaEnvironment",  # Changed to unique name
            airflow_version="2.10.3",
            dag_s3_path="dags",  # This is the folder where you'll upload DAGs manually
            execution_role_arn=execution_role.role_arn,
            source_bucket_arn=self.dags_bucket.bucket_arn,
            webserver_access_mode="PUBLIC_ONLY",
            environment_class="mw1.small",
            max_workers=5,
            network_configuration=mwaa.CfnEnvironment.NetworkConfigurationProperty(
                security_group_ids=[security_group.security_group_id],
                subnet_ids=self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ).subnet_ids,
            ),
            logging_configuration=mwaa.CfnEnvironment.LoggingConfigurationProperty(
                dag_processing_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
                scheduler_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
                webserver_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
                worker_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
            ),
            airflow_configuration_options={
                "core.load_default_connections": "False",
                "core.load_examples": "False",
                "scheduler.min_file_process_interval": "30",
            },
        )
        
        # Create CloudWatch log group for MWAA with unique name
        logs.LogGroup(
            self, "MwaaLogGroup",
            log_group_name=f"/aws/mwaa/TradingStrategiesMwaaEnvironment",  # Changed to unique name
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Output important information
        CfnOutput(
            self, "MwaaWebserverUrl",
            value=Fn.sub("https://${WebServerUrl}", {
                "WebServerUrl": environment.attr_webserver_url
            }),
            description="URL of the MWAA webserver",
        )
        
        CfnOutput(
            self, "DagsBucketName",
            value=self.dags_bucket.bucket_name,
            description="Name of the S3 bucket for Airflow DAGs",
        )
        
        CfnOutput(
            self, "DagsBucketArn",
            value=self.dags_bucket.bucket_arn,
            description="ARN of the S3 bucket for Airflow DAGs",
        )
        
        CfnOutput(
            self, "MwaaExecutionRoleArn",
            value=execution_role.role_arn,
            description="ARN of the execution role for MWAA",
        )
        
        # Export resources for reference
        self.execution_role = execution_role
        self.mwaa_environment = environment