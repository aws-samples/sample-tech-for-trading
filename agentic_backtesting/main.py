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
    
    while True:
        user_input = input("\n> ")
        
        if user_input.lower() in ['quit', 'exit']:
            break
            
        # Orchestrator automatically determines which tools to use
        response = orchestrator.process(user_input)
        print(f"📋 {response}")

if __name__ == "__main__":
    main()
