"""
config.py

Global Project Configuration
Manages common configuration values used by all deployment scripts.
"""

class Config:
    """Global project configuration"""
    
    # AWS region setting (commonly used by all agents)
    REGION = "us-west-2"
    
    # Agent name settings
    FINANCIAL_ANALYST_NAME = "financial_analyst"
    PORTFOLIO_ARCHITECT_NAME = "portfolio_architect"
    RISK_MANAGER_NAME = "risk_manager"
    FUND_MANAGER_NAME = "fund_manager"
    
    # MCP Server settings
    MCP_SERVER_NAME = "mcp_server"
    
    # Gateway settings
    GATEWAY_NAME = "gateway-risk-manager"
    TARGET_NAME = "target-risk-manager"
    
    # Lambda settings
    LAMBDA_FUNCTION_NAME = "lambda-agentcore-risk-manager"
    LAMBDA_LAYER_NAME = "layer-yfinance"
    
    # Memory settings
    MEMORY_NAME = "FundManager_Memory"
