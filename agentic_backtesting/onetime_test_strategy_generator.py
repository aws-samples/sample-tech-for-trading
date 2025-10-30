#!/usr/bin/env python3
"""
One-time test for Strategy Generator Agent
"""

import json
from agents.strategy_generator import StrategyGeneratorAgent

def test_strategy_generator():
    # Sample JSON strategy configuration
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
            },
            {
                "indicator": "ROC",
                "param": 10,
                "operator": ">",
                "compare_type": "value",
                "compare_value": 2
            }
        ],
        "sell_conditions": [
            {
                "indicator": "EMA",
                "param": 50,
                "operator": "<",
                "compare_type": "indicator",
                "compare_indicator": "EMA",
                "compare_param": 250
            },
            {
                "indicator": "RSI",
                "param": 14,
                "operator": ">",
                "compare_type": "value",
                "compare_value": 70
            }
        ]
    }
    
    print("🧪 Testing Strategy Generator Agent")
    print("=" * 50)
    print("📥 Input JSON:")
    print(json.dumps(test_strategy, indent=2))
    print("\n" + "=" * 50)
    
    try:
        # Initialize agent
        agent = StrategyGeneratorAgent()
        
        # Process the strategy
        print("🔄 Generating strategy code...")
        result = agent.process(test_strategy)
        
        print("✅ Generated Strategy Code:")
        print("-" * 50)
        print(result)
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_strategy_generator()
