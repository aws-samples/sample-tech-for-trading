#!/usr/bin/env python3
"""
deploy_all.py - Complete System Deployment
"""

import subprocess
import sys
from pathlib import Path
from config import Config

def run_cmd(cmd, cwd=None):
    """Execute command"""
    print(f"🔄 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Failed: {cmd}")
        return False
    print(f"✅ Completed: {cmd}")
    return True

def deploy_step(name, commands):
    """Execute deployment step"""
    print(f"\n🎯 {name}")
    for cmd, cwd in commands:
        if not run_cmd(cmd, cwd):
            response = input("Do you want to continue? (y/N): ")
            if response.lower() != 'y':
                return False
    return True

def main():
    print("🚀 AI Fund Manager System Deployment")
    print(f"📍 Deployment Region: {Config.REGION}")
    print(f"🏗️ Agent Configuration: {Config.FINANCIAL_ANALYST_NAME}, {Config.PORTFOLIO_ARCHITECT_NAME}, {Config.RISK_MANAGER_NAME}, {Config.FUND_MANAGER_NAME}")
    
    # AWS verification
    if not run_cmd("aws sts get-caller-identity"):
        print("❌ Please configure AWS credentials: aws configure")
        return 1
    
    # Deployment steps
    steps = [
        ("Lab 1: Financial Analyst", [
            ("python deploy.py", "financial_analyst")
        ]),
        ("Lab 2: Portfolio Architect", [
            ("python deploy_mcp.py", "portfolio_architect/mcp_server"),
            ("python deploy.py", "portfolio_architect")
        ]),
        ("Lab 3: Risk Manager", [
            ("python deploy_lambda_layer.py", "risk_manager/lambda_layer"),
            ("python deploy_lambda.py", "risk_manager/lambda"),
            ("python deploy_gateway.py", "risk_manager/gateway"),
            ("python deploy.py", "risk_manager")
        ]),
        ("Lab 4: Fund Manager", [
            ("python deploy_agentcore_memory.py", "fund_manager/agentcore_memory"),
            ("python deploy.py", "fund_manager")
        ])
    ]
    
    for name, commands in steps:
        if not deploy_step(name, commands):
            return 1
    
    print("\n🎉 Deployment Complete!")
    print("Run web app: cd fund_manager && streamlit run app.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())