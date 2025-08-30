from typing import Optional
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_iam as iam,
    aws_glue as glue,
    aws_ec2 as ec2,
)
from constructs import Construct
from .batch_stack import BatchStack
from .mwaa_stack import MwaaStack
from .storage_stack import StorageStack

class TradingStrategiesStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        container_image_uri: str,
        existing_vpc_id: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC Configuration - Use existing VPC or create new one
        if existing_vpc_id:
            # Use existing VPC
            vpc = ec2.Vpc.from_lookup(
                self, "ExistingVpc",
                vpc_id=existing_vpc_id
            )
            print(f"Using existing VPC: {existing_vpc_id}")
        else:
            # Create new VPC for the infrastructure
            vpc = ec2.Vpc(
                self, "TradingStrategiesVpc",
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
            print("Created new VPC for trading strategies infrastructure")

        # Create nested stacks
        storage_stack = StorageStack(self, "StorageStack")
        
        # Create batch stack with enhanced configuration
        batch_stack = BatchStack(
            self, "BatchStack", 
            vpc=vpc,
            s3_bucket_arn=storage_stack.results_bucket.bucket_arn,
            container_image_uri=container_image_uri,  # Use the parameter passed from app.py
            maxv_cpus=256,
            minv_cpus=0,
            num_queues=2,  # Create 2 job queues for parallel processing
            container_memory=4096,
            container_cpu=2,
            spot=True  # Use spot instances for cost optimization
        )
        
        # Create MWAA stack with existing VPC and DAGs bucket
        mwaa_stack = MwaaStack(
            self, "MwaaStack", 
            vpc=vpc,
            dags_bucket=storage_stack.dags_bucket
        )

        # Export outputs
        self.vpc = vpc
        self.results_bucket = storage_stack.results_bucket
        self.dags_bucket = storage_stack.dags_bucket
        self.batch_primary_job_queue = batch_stack.primary_job_queue
        self.batch_all_job_queues = batch_stack.all_job_queues
        self.backtest_job_definition = batch_stack.backtest_job_def
        self.mwaa_environment = mwaa_stack.mwaa_environment
        self.mwaa_execution_role = mwaa_stack.execution_role
