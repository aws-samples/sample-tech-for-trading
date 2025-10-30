import os
from dotenv import load_dotenv
from orchestrator_agent import OrchestratorAgent

def main():
    # Load environment variables from .env
    load_dotenv()
    
    # Read Redshift configuration
    redshift_config = {
        'host': os.getenv('PGHOST'),
        'port': os.getenv('PGPORT'),
        'user': os.getenv('PGUSER'),
        'password': os.getenv('PGPASSWORD'),
        'database': os.getenv('PGDATABASE')
    }
    
    print(f"Redshift Config: {redshift_config['host']}:{redshift_config['port']}/{redshift_config['database']}")
    
    # Initialize orchestrator with specialized agents as tools
    orchestrator = OrchestratorAgent()
    
    print("Multi-Agent Trading System Ready")
    print("Enter your trading ideas or commands:")
    
    user_input = """
    {
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
  "stop_loss": 5,
  "take_profit": 10,
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
      "indicator": "PRICE",
      "param": null,
      "operator": "<",
      "compare_type": "value",
      "compare_value": 200
    }
  ]
}
"""
    # Orchestrator automatically determines which tools to use
    response = orchestrator.process(user_input)
    print(f"📋 {response}")

if __name__ == "__main__":
    main()
