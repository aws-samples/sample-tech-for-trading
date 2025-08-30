# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from dataclasses import dataclass
from typing import Dict, Optional, List
from math import floor

from aws_cdk import (
    NestedStack,
    Size,
    RemovalPolicy,
    aws_batch as batch,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


@dataclass
class S3BucketArnConfig:
    """Configuration for S3 Bucket ARNs"""
    s3_standard_bucket_arn: str
    s3_express_bucket_arn: Optional[str] = None
    custom_s3_arns: Optional[List[str]] = None


@dataclass
class BatchJobConstructConfig:
    """Configuration for Batch Job Construct"""
    namespace: str
    s3_bucket_config: S3BucketArnConfig


class BatchJobConstruct(Construct):
    """Base construct for creating IAM roles and policies for Batch jobs"""
    
    MOUNT_PATH: str = "/fsx"

    def __init__(
        self, scope: Construct, construct_id: str, config: BatchJobConstructConfig
    ):
        super().__init__(scope, construct_id)

        self.s3_bucket_config = config.s3_bucket_config
        self.namespace = config.namespace

        self.job_role = self.create_job_role()
        self.instance_role = self.create_instance_role()
        self.task_execution_role = self.create_task_execution_role()

    @property
    def region(self) -> str:
        """Get the current AWS region."""
        return NestedStack.of(self).region

    @property
    def account(self) -> str:
        """Get the current AWS account ID."""
        return NestedStack.of(self).account

    def create_job_role(self) -> iam.Role:
        """Creates an IAM role for AWS Batch jobs with conditional policies."""
        return iam.Role(
            self,
            "BatchJobRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            inline_policies=self._get_job_role_policies(),
        )

    def _get_job_role_policies(self) -> Dict[str, iam.PolicyDocument]:
        """Assembles all required policies for the job role."""
        policies = {}

        # Add S3 Standard policy if configured
        if s3_standard_policy := self._create_s3_standard_policy():
            policies.update(s3_standard_policy)

        # Add S3 Express policy if configured
        if s3_express_policy := self._create_s3_express_policy():
            policies.update(s3_express_policy)

        # Add S3 custom arn policies if configured
        if s3_custom_policy := self._create_s3_custom_policies():
            policies.update(s3_custom_policy)

        # Add required Glue policy
        policies.update(self._create_glue_policy())

        # Add required Batch policy
        policies.update(self._create_batch_policy())

        # Add required CloudWatch policy
        policies.update(self._create_cloudwatch_policy())

        # Add Athena policy for querying results
        policies.update(self._create_athena_policy())

        return policies

    def _create_s3_custom_policies(self) -> Optional[Dict[str, iam.PolicyDocument]]:
        """Creates S3 custom arn policies if configured."""
        if (
            not hasattr(self, "s3_bucket_config")
            or not self.s3_bucket_config.custom_s3_arns
        ):
            return None

        return {
            "ReadWriteS3CustomLocations": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="CustomS3Access",
                        actions=[
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                        ],
                        resources=self.s3_bucket_config.custom_s3_arns,
                    ),
                ]
            )
        }

    def _create_s3_standard_policy(self) -> Optional[Dict[str, iam.PolicyDocument]]:
        """Creates S3 standard bucket policy if configured."""
        if (
            not hasattr(self, "s3_bucket_config")
            or not self.s3_bucket_config.s3_standard_bucket_arn
        ):
            return None

        return {
            "ReadWriteS3Standard": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="StandardS3Access",
                        actions=[
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                        ],
                        resources=[
                            self.s3_bucket_config.s3_standard_bucket_arn,
                            f"{self.s3_bucket_config.s3_standard_bucket_arn}/*",
                        ],
                    )
                ]
            )
        }

    def _create_s3_express_policy(self) -> Optional[Dict[str, iam.PolicyDocument]]:
        """Creates S3 Express bucket policy if configured."""
        if (
            not hasattr(self, "s3_bucket_config")
            or not self.s3_bucket_config.s3_express_bucket_arn
        ):
            return None

        return {
            "ReadWriteS3Express": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="S3ExpressAccess",
                        actions=[
                            "s3express:ListBucket",
                            "s3express:GetObject",
                            "s3express:PutObject",
                            "s3express:DeleteObject",
                        ],
                        resources=[
                            self.s3_bucket_config.s3_express_bucket_arn,
                            f"{self.s3_bucket_config.s3_express_bucket_arn}/*",
                        ],
                    )
                ]
            )
        }

    def _create_glue_policy(self) -> Dict[str, iam.PolicyDocument]:
        """Creates Glue access policy."""
        return {
            "ReadGlue": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="GlueReadAccess",
                        actions=[
                            "glue:GetTable",
                            "glue:GetDatabase",
                            "glue:GetPartitions",
                            "glue:GetTableVersions",
                        ],
                        resources=[
                            f"arn:aws:glue:{self.region}:{self.account}:catalog",
                            f"arn:aws:glue:{self.region}:{self.account}:database/*",
                            f"arn:aws:glue:{self.region}:{self.account}:table/*",
                        ],
                    )
                ]
            )
        }

    def _create_batch_policy(self) -> Dict[str, iam.PolicyDocument]:
        """Creates Batch access policy."""
        return {
            "BatchJobAccess": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="BatchJobAccess",
                        actions=[
                            "batch:SubmitJob",
                            "batch:DescribeJobs",
                            "batch:TerminateJob",
                            "batch:ListJobs",
                        ],
                        resources=[
                            f"arn:aws:batch:{self.region}:{self.account}:job-queue/*",
                            f"arn:aws:batch:{self.region}:{self.account}:job-definition/*",
                        ],
                    )
                ]
            )
        }

    def _create_cloudwatch_policy(self) -> Dict[str, iam.PolicyDocument]:
        """Creates CloudWatch Logs access policy."""
        return {
            "CloudWatchLogsAccess": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="CloudWatchLogsAccess",
                        actions=[
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:DescribeLogStreams",
                        ],
                        resources=[
                            f"arn:aws:logs:{self.region}:{self.account}:log-group:/{self.namespace}/*"
                        ],
                    )
                ]
            )
        }

    def _create_athena_policy(self) -> Dict[str, iam.PolicyDocument]:
        """Creates Athena access policy for querying backtest results."""
        return {
            "AthenaAccess": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="AthenaAccess",
                        actions=[
                            "athena:StartQueryExecution",
                            "athena:GetQueryExecution",
                            "athena:GetQueryResults",
                            "athena:StopQueryExecution",
                            "athena:GetWorkGroup",
                        ],
                        resources=[
                            f"arn:aws:athena:{self.region}:{self.account}:workgroup/*"
                        ],
                    )
                ]
            )
        }

    def create_task_execution_role(self) -> iam.Role:
        """Creates an ECS task execution role for AWS Batch."""
        return iam.Role(
            self,
            "BatchJobTaskExecutionRole",
            description=f"ECS task execution role for AWS Batch with {self.namespace}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
            inline_policies={
                "LogAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="CloudWatchLogsAccess",
                            actions=[
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DescribeLogStreams",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/{self.namespace}/*"
                            ],
                        )
                    ]
                ),
            },
        )

    def create_instance_role(self) -> iam.Role:
        """Creates an EC2 instance role for AWS Batch."""
        return iam.Role(
            self,
            "BatchJobInstanceRole",
            description=f"EC2 instance role for AWS Batch with {self.namespace}",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ecs.amazonaws.com"),
                iam.ServicePrincipal("ec2.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonEC2ContainerServiceforEC2Role"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchAgentAdminPolicy"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )


class BatchStack(NestedStack):
    """Enhanced Batch Stack for Factor Trading Strategies"""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        vpc: ec2.IVpc,
        s3_bucket_arn: str,
        container_image_uri: str = "amazon/aws-cli:latest",
        maxv_cpus: int = 256,
        minv_cpus: int = 0,
        num_queues: int = 1,
        container_memory: int = 4096,
        container_cpu: int = 2,
        container_command: Optional[List[str]] = None,
        instance_classes: Optional[List[str]] = None,
        allocation_strategy: str = "BEST_FIT_PROGRESSIVE",
        spot: bool = False,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.namespace = "factor-trading"
        self.job_queues = {}
        self.compute_environments = {}

        # Configure S3 bucket access
        s3_bucket_config = S3BucketArnConfig(
            s3_standard_bucket_arn=s3_bucket_arn
        )

        # Building IAM permissions
        self.batch_job_construct = BatchJobConstruct(
            self,
            "BatchJobIAMPermissions",
            config=BatchJobConstructConfig(
                namespace=self.namespace,
                s3_bucket_config=s3_bucket_config,
            ),
        )

        # Create security group for Batch
        self.batch_sg = ec2.SecurityGroup(
            self, "BatchSecurityGroup",
            vpc=vpc,
            description="Security group for AWS Batch compute environment",
            allow_all_outbound=True
        )

        # Allow internal communication within the security group
        self.batch_sg.add_ingress_rule(
            peer=self.batch_sg,
            connection=ec2.Port.all_tcp(),
            description="Allow internal TCP traffic"
        )

        # Building the compute environment and job queues
        self.build_compute_environment(
            vpc=vpc,
            maxv_cpus=maxv_cpus,
            minv_cpus=minv_cpus,
            num_queues=num_queues,
            instance_classes=instance_classes,
            allocation_strategy=allocation_strategy,
            spot=spot
        )

        # Building job definitions
        self.backtest_job_def = self.build_job_definition(
            job_name="backtest",
            container_image_uri=container_image_uri,
            container_memory=container_memory,
            container_cpu=container_cpu,
            container_command=container_command or ["python3", "src/batch_jobs/backtest_job.py"]
        )

        # Add dependencies for orchestrating infrastructure build
        self.backtest_job_def.node.add_dependency(
            *list(self.job_queues.values()),
            *list(self.compute_environments.values()),
        )

    def build_job_definition(
        self, 
        job_name: str,
        container_image_uri: str,
        container_memory: int,
        container_cpu: int,
        container_command: List[str]
    ) -> batch.EcsJobDefinition:
        """Creates AWS Batch job definition for Fargate"""
        return batch.EcsJobDefinition(
            self,
            f"BatchJobDefinition{job_name.title().replace('-', '')}",
            propagate_tags=True,
            job_definition_name=f"{self.namespace}-{job_name}",
            container=batch.EcsFargateContainerDefinition(
                self,
                f"BatchJobContainerDefinition{job_name.title().replace('-', '')}",
                image=ecs.ContainerImage.from_registry(container_image_uri),
                command=container_command,
                memory=Size.mebibytes(container_memory),
                cpu=container_cpu,
                job_role=self.batch_job_construct.job_role,
                execution_role=self.batch_job_construct.task_execution_role,
                logging=ecs.LogDriver.aws_logs(
                    stream_prefix=f"{self.namespace}-{job_name}",
                    log_group=logs.LogGroup(
                        self,
                        f"BatchJobLogGroup{job_name.title().replace('-', '')}",
                        log_group_name=f"/{self.namespace}/batch-job/{job_name}",
                        retention=logs.RetentionDays.ONE_MONTH,
                        removal_policy=RemovalPolicy.DESTROY,
                    ),
                    mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                    max_buffer_size=Size.mebibytes(128),
                ),
            ),
        )

    def build_compute_environment(
        self,
        vpc: ec2.IVpc,
        maxv_cpus: int,
        minv_cpus: int,
        num_queues: int,
        instance_classes: Optional[List[str]],
        allocation_strategy: str,
        spot: bool
    ):
        """Creates AWS Batch Fargate compute environment and job queues."""
        for i in range(num_queues):
            self.compute_environments[i] = batch.FargateComputeEnvironment(
                self,
                f"BatchJobFargateComputeEnvironment_{i:02}",
                compute_environment_name=f"{self.namespace}-fargate-compute-env-{i:02}",
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                vpc=vpc,
                security_groups=[self.batch_sg],
                maxv_cpus=floor(maxv_cpus / num_queues),
            )

            self.job_queues[i] = batch.JobQueue(
                self,
                f"BatchJobFargateQueue_{i:02}",
                job_queue_name=f"{self.namespace}-fargate-job-queue-{i:02}",
                compute_environments=[
                    batch.OrderedComputeEnvironment(
                        compute_environment=self.compute_environments[i], order=1
                    )
                ],
            )

    # Export properties for use in other stacks
    @property
    def primary_job_queue(self) -> batch.JobQueue:
        """Returns the primary job queue (index 0)"""
        return self.job_queues[0]

    @property
    def all_job_queues(self) -> Dict[int, batch.JobQueue]:
        """Returns all job queues"""
        return self.job_queues
