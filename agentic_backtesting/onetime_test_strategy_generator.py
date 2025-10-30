#!/usr/bin/env python3
"""
One-time test for Strategy Generator Agent with Market Data
"""

import json
from agents.strategy_generator import StrategyGeneratorAgent
from agents.market_data import MarketDataAgent
from mcp import RedshiftMCPClient

def test_strategy_generator_with_market_data():
    print("🧪 Testing Strategy Generator with Market Data")
    print("=" * 60)
    
    try:
        # Step 1: Fetch Market Data
        print("📊 Step 1: Fetching Market Data")
        print("-" * 30)
        
        mcp_client = RedshiftMCPClient()
        market_data_agent = MarketDataAgent(mcp_client=mcp_client)
        
        # Fetch market data for AMZN
        market_data_input = {
            'symbols': ['AMZN'],
            'period': '1y'
        }
        
        print(f"📥 Market Data Input: {market_data_input}")
        market_data_result = market_data_agent.process(market_data_input)
        
        if not market_data_result:
            print("❌ Failed to fetch market data")
            return
            
        print(f"✅ Market Data fetched: {list(market_data_result.keys()) if market_data_result else 'None'}")
        
        # Step 2: Generate Strategy with Market Data
        print("\n🔧 Step 2: Generating Strategy Code")
        print("-" * 30)
        
        strategy_agent = StrategyGeneratorAgent()
        
        # Create input with query and market data
        strategy_input = {
            'query': 'Create an EMA crossover strategy with RSI filter for AMZN',
            'market_data': market_data_result
        }
        
        print(f"📥 Strategy Input Query: {strategy_input['query']}")
        print(f"📥 Market Data Keys: {list(strategy_input['market_data'].keys()) if strategy_input['market_data'] else 'None'}")
        
        # Generate strategy
        print("🔄 Generating strategy code...")
        strategy_code = strategy_agent.process(strategy_input)
        
        print("\n✅ Generated Strategy Code:")
        print("=" * 60)
        print(strategy_code)
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_strategy_generator_with_json_config():
    print("\n🧪 Testing Strategy Generator with JSON Config")
    print("=" * 60)
    
    # Sample JSON strategy configuration with database
    test_strategy = {
        "name": "EMA Crossover Strategy",
        "stock_symbol": "AMZN",
        "backtest_window": "1Y",
        "database": {
            "PGPASSWORD": "Awsuser123!",
            "PGHOST": "trading-redshift-cluster.cwep8drv40mu.us-east-1.redshift.amazonaws.com",
            "PGPORT": 5439,
            "PGUSER": "awsuser",
            "PGDATABASE": "quantdb"
        },
        "max_positions": 1,
        "stop_loss": 5.0,
        "take_profit": 10.0,
        "buy_conditions": [
            {
                "indicator": "EMA",
                "param": 50,
                "operator": ">",
                "compare_type": "indicator",
                "compare_indicator": "EMA",
                "compare_param": 250
            }
        ],
        "sell_conditions": [
            {
                "indicator": "RSI",
                "param": 14,
                "operator": ">",
                "compare_type": "value",
                "compare_value": 70
            }
        ]
    }
    
    try:
        strategy_agent = StrategyGeneratorAgent()
        
        print("📥 Input JSON Config:")
        print(json.dumps(test_strategy, indent=2))
        print("\n🔄 Generating strategy code...")
        
        result = strategy_agent.process(test_strategy)
        
        print("\n✅ Generated Strategy Code:")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test both approaches
    test_strategy_generator_with_market_data()
    test_strategy_generator_with_json_config()
