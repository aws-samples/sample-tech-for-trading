from typing import Optional
import requests
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    CfnOutput,
)
from constructs import Construct
import os

class VisualizationStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        vpc_id: str,
        your_ip: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import the existing VPC using VPC ID
        vpc = ec2.Vpc.from_lookup(
            self, "ExistingVpc",
            vpc_id=vpc_id
        )

        # Get your current IP if not provided
        if not your_ip:
            try:
                your_ip = requests.get('https://ipv4.icanhazip.com', timeout=10).text.strip()
                print(f"Detected your IP: {your_ip}")
            except:
                print("Could not detect your IP. Please provide it manually.")
                your_ip = "0.0.0.0"  # Fallback - you should replace this

        # We'll deploy the app code directly via user data instead of S3

        # Create security group for Streamlit
        streamlit_sg = ec2.SecurityGroup(
            self, "StreamlitSecurityGroup",
            vpc=vpc,
            description="Security group for Streamlit visualization server",
            allow_all_outbound=True
        )

        # Allow SSH access from your IP
        streamlit_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(f"{your_ip}/32"),
            connection=ec2.Port.tcp(22),
            description="SSH access from your IP"
        )

        # Allow Streamlit access from your IP
        streamlit_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(f"{your_ip}/32"),
            connection=ec2.Port.tcp(8501),
            description="Streamlit access from your IP"
        )

        # Create IAM role for EC2 instance
        ec2_role = iam.Role(
            self, "StreamlitEC2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ]
        )

        # EC2 role doesn't need S3 access for this simplified version

        # Create key pair for SSH access
        key_pair = ec2.KeyPair(
            self, "StreamlitKeyPair",
            key_pair_name="streamlit-visualization-key",
            type=ec2.KeyPairType.RSA,
            format=ec2.KeyPairFormat.PEM
        )

        # User data script to install and configure Streamlit
        user_data_script = ec2.UserData.for_linux()
        user_data_script.add_commands(
            # Update system
            "yum update -y",
            
            # Install Python 3.11 and pip
            "yum install -y python3.11 python3.11-pip git awscli",
            
            # Create application directory
            "mkdir -p /opt/streamlit-app",
            "cd /opt/streamlit-app",
            
            # Create application directory and basic files
            "mkdir -p /opt/streamlit-app",
            "cd /opt/streamlit-app",
            
            # Create requirements.txt
            "cat > requirements.txt << 'EOF'",
            "streamlit",
            "pandas", 
            "plotly",
            "clickhouse-connect",
            "python-dotenv",
            "EOF",
            
            # Create a simple placeholder app that we'll replace
            "echo 'import streamlit as st; st.write(\"Setting up...\")' > app.py",
            
            # Install Python dependencies
            "python3.11 -m pip install --upgrade pip",
            "python3.11 -m pip install -r requirements.txt",
            
            # Create systemd service for Streamlit
            "cat > /etc/systemd/system/streamlit.service << 'EOF'",
            "[Unit]",
            "Description=Streamlit Factor Trading Dashboard",
            "After=network.target",
            "",
            "[Service]",
            "Type=simple",
            "User=ec2-user",
            "WorkingDirectory=/opt/streamlit-app",
            "Environment=PATH=/usr/bin:/usr/local/bin",
            "ExecStart=/usr/bin/python3.11 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true",
            "Restart=always",
            "RestartSec=10",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "EOF",
            
            # Set permissions
            "chown -R ec2-user:ec2-user /opt/streamlit-app",
            
            # Enable and start the service
            "systemctl daemon-reload",
            "systemctl enable streamlit",
            "systemctl start streamlit",
            
            # Install CloudWatch agent (optional, for monitoring)
            "yum install -y amazon-cloudwatch-agent",
        )

        # Create EC2 instance
        instance = ec2.Instance(
            self, "StreamlitInstance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MEDIUM
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_group=streamlit_sg,
            role=ec2_role,
            key_pair=key_pair,
            user_data=user_data_script,
            user_data_causes_replacement=True
        )

        # No dependency needed since we're embedding files in user data

        # Outputs
        CfnOutput(
            self, "StreamlitURL",
            value=f"http://{instance.instance_public_ip}:8501",
            description="Streamlit Dashboard URL"
        )

        CfnOutput(
            self, "InstanceId",
            value=instance.instance_id,
            description="EC2 Instance ID"
        )

        CfnOutput(
            self, "SSHCommand",
            value=f"ssh -i streamlit-visualization-key.pem ec2-user@{instance.instance_public_ip}",
            description="SSH command to connect to the instance"
        )

        CfnOutput(
            self, "KeyPairId",
            value=key_pair.key_pair_id,
            description="Key Pair ID for SSH access"
        )

        CfnOutput(
            self, "YourIP",
            value=your_ip,
            description="Your IP address (allowed in security group)"
        )

        # Store instance reference
        self.instance = instance
        self.security_group = streamlit_sg
        self.key_pair = key_pair
