#!/usr/bin/env python3

import os
import sys
from aws_cdk import App, Environment
from trading_strategies.trading_strategies_stack import TradingStrategiesStack
from visualization_stack import VisualizationStack

app = App()

# Define your AWS environment with explicit account and region
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "123456789012"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

# Get VPC configuration from environment or context
existing_vpc_id = app.node.try_get_context("existing_vpc_id") or os.environ.get("EXISTING_VPC_ID")

# Get container image URI from environment or context, with default fallback
container_image_uri = (
    app.node.try_get_context("container_image_uri") or 
    os.environ.get("CONTAINER_IMAGE_URI")
)

# Get visualization parameters
your_ip = app.node.try_get_context('your_ip') or os.environ.get('YOUR_IP')

# Get deployment mode - can be 'all', 'trading', or 'visualization'
deploy_mode = app.node.try_get_context('deploy_mode') or os.environ.get('DEPLOY_MODE', 'all')

# Create the main trading strategies stack (unless mode is 'visualization' only)
if deploy_mode in ['all', 'trading']:
    trading_strategies_stack = TradingStrategiesStack(
        app, 
        "TradingStrategiesStack", 
        container_image_uri=container_image_uri,
        existing_vpc_id=existing_vpc_id,
        env=env
    )

# Create the visualization stack if VPC ID is provided (unless mode is 'trading' only)
if deploy_mode in ['all', 'visualization'] and existing_vpc_id:
    visualization_stack = VisualizationStack(
        app, "FactorTradingVisualization",
        vpc_id=existing_vpc_id,
        your_ip=your_ip,
        env=env,
        description="Factor Trading Streamlit Visualization Dashboard"
    )
elif deploy_mode in ['all', 'visualization'] and not existing_vpc_id:
    print("Note: Visualization stack not created. To deploy visualization, provide existing_vpc_id:")
    print("  cdk deploy -c existing_vpc_id=vpc-xxxxxxxxx")

app.synth()
