"""
target_config.py

Gateway Target Configuration
Defines MCP tool schemas to be used in Risk Manager Gateway.
"""

TARGET_CONFIGURATION = {
    "mcp": {
        "lambda": {
            "lambdaArn": "",  # Lambda ARN will be automatically injected during deployment
            "toolSchema": {
                "inlinePayload": [
                    # ETF news retrieval tool
                    {
                        "name": "get_product_news",
                        "description": "Retrieves the latest news information for the selected ETF ticker. Returns recent news articles including title, summary, and publication date for risk analysis and market sentiment evaluation.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "ticker": {
                                    "type": "string",
                                    "description": "ETF ticker symbol to retrieve news for (e.g., 'QQQ', 'SPY', 'GLD')"
                                }
                            },
                            "required": ["ticker"]
                        }
                    },
                    
                    # Macroeconomic indicator retrieval tool  
                    {
                        "name": "get_market_data",
                        "description": "Retrieves major macroeconomic indicator data including US Dollar Index, Treasury yields, VIX volatility index, and oil prices. Returns real-time market data for economic scenario planning and risk assessment.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    
                    # Geopolitical risk indicator retrieval tool
                    {
                        "name": "get_geopolitical_indicators",
                        "description": "Analyzes geopolitical risks by retrieving major regional ETF data from China, emerging markets, Europe, Japan, Korea, and other regions. Returns real-time regional ETF price data to assess market conditions and geopolitical tensions in each region.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
            }
        }
    }
}