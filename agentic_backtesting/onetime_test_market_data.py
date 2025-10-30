#!/usr/bin/env python3
"""
One-time test for Market Data Agent
"""
from dotenv import load_dotenv
from agents.market_data import MarketDataAgent
from mcp import RedshiftMCPClient

def test_market_data():
    print("🧪 Testing Market Data Agent")
    print("=" * 50)
    
    load_dotenv()
    
    try:
        # Initialize MCP client and agent
        mcp_client = RedshiftMCPClient()
        agent = MarketDataAgent(mcp_client=mcp_client)
        
        # Test parameters
        symbols = ["AMZN"]
        period = "1y"
        
        print(f"📥 Input: symbols={symbols}, period={period}")
        print("🔄 Fetching market data...")
        
        # Process the request
        result = agent.process({
            'symbols': symbols,
            'period': period
        })
        
        print("✅ Market Data Result:")
        print("-" * 50)
        if result:
            print(f"Data type: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys: {list(result.keys())}")
                for key, value in result.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"{key}: {len(value)} records")
                        print(f"Sample: {value[0] if value else 'No data'}")
                    else:
                        print(f"{key}: {value}")
            else:
                print(result)
        else:
            print("No data returned")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    
    test_market_data()
