import os

try:
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()
    dotenv_loaded = True
except ImportError:
    print("Warning: python-dotenv package not found. Using environment variables directly.")
    dotenv_loaded = False
import ast

# ClickHouse configuration
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'your-default-host')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'your-default-user')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'your-default-pass')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'your-default-db')

# Factor analysis configuration
START_DATE = os.getenv('START_DATE', '2020-01-01')
END_DATE = os.getenv('END_DATE', '2025-03-31')

# DJIA tickers
DJIA_TICKERS_STR = os.getenv('DJIA_TICKERS',
                             'AAPL,AMGN,AMZN,AXP,BA,CAT,CRM,CSCO,CVX,DIS,GS,HD,HON,IBM,JNJ,JPM,KO,MCD,MMM,MRK,MSFT,NKE,NVDA,PG,SHW,TRV,UNH,V,VZ,WMT')
DJIA_TICKERS = DJIA_TICKERS_STR.split(',')

# Strategy configuration - Long-Short Strategy
LS_LONG_PCT = float(os.getenv('LS_LONG_PCT', '0.4'))
LS_SHORT_PCT = float(os.getenv('LS_SHORT_PCT', '0.2'))
LS_LONG_ALLOCATION = float(os.getenv('LS_LONG_ALLOCATION', '0.8'))
LS_SHORT_ALLOCATION = float(os.getenv('LS_SHORT_ALLOCATION', '0.5'))

# Strategy configuration - Long-Only Strategy
LO_SELECTION_PCT = float(os.getenv('LO_SELECTION_PCT', '0.5'))
LO_MIN_STOCKS = int(os.getenv('LO_MIN_STOCKS', '5'))
LO_EQUAL_WEIGHT = os.getenv('LO_EQUAL_WEIGHT', 'False').lower() == 'true'

# Risk management
STOP_LOSS = float(os.getenv('STOP_LOSS', '0.05')) if os.getenv('STOP_LOSS') else None
TAKE_PROFIT = float(os.getenv('TAKE_PROFIT', '0.10')) if os.getenv('TAKE_PROFIT') else None

# Rebalancing configuration
REBALANCE_FREQ = os.getenv('REBALANCE_FREQ', 'M')

# Factor weights
FACTOR_WEIGHTS_STR = os.getenv('FACTOR_WEIGHTS', '')
FACTOR_WEIGHTS = {}
if FACTOR_WEIGHTS_STR:
    for item in FACTOR_WEIGHTS_STR.split(','):
        if ':' in item:
            factor, weight = item.split(':')
            FACTOR_WEIGHTS[factor.strip()] = float(weight.strip())

# Parallel processing
NUM_PROCESSES = int(os.getenv('NUM_PROCESSES', '4'))
SPLIT_BY = os.getenv('SPLIT_BY', 'tickers')


def print_config():
    """Print all configuration values to verify .env loading"""
    print("\n=== CONFIGURATION VALUES ===\n")

    if dotenv_loaded:
        print("✅ .env file loaded successfully")
    else:
        print("⚠️ Using environment variables directly (dotenv not loaded)")

    print("\n=== ClickHouse Configuration ===")
    print(f"CLICKHOUSE_HOST: {CLICKHOUSE_HOST}")
    print(f"CLICKHOUSE_PORT: {CLICKHOUSE_PORT}")
    print(f"CLICKHOUSE_USER: {CLICKHOUSE_USER}")
    print(f"CLICKHOUSE_PASSWORD: {'*' * len(CLICKHOUSE_PASSWORD)}")  # Masked for security
    print(f"CLICKHOUSE_DATABASE: {CLICKHOUSE_DATABASE}")

    print("\n=== Factor Analysis Configuration ===")
    print(f"START_DATE: {START_DATE}")
    print(f"END_DATE: {END_DATE}")

    print("\n=== DJIA Tickers ===")
    print(f"Number of tickers: {len(DJIA_TICKERS)}")
    print(f"Tickers: {', '.join(DJIA_TICKERS)}")

    print("\n=== Long-Short Strategy Configuration ===")
    print(f"LS_LONG_PCT: {LS_LONG_PCT}")
    print(f"LS_SHORT_PCT: {LS_SHORT_PCT}")
    print(f"LS_LONG_ALLOCATION: {LS_LONG_ALLOCATION}")
    print(f"LS_SHORT_ALLOCATION: {LS_SHORT_ALLOCATION}")

    print("\n=== Long-Only Strategy Configuration ===")
    print(f"LO_SELECTION_PCT: {LO_SELECTION_PCT}")
    print(f"LO_MIN_STOCKS: {LO_MIN_STOCKS}")
    print(f"LO_EQUAL_WEIGHT: {LO_EQUAL_WEIGHT}")

    print("\n=== Risk Management ===")
    print(f"STOP_LOSS: {STOP_LOSS}")
    print(f"TAKE_PROFIT: {TAKE_PROFIT}")

    print("\n=== Rebalancing Configuration ===")
    print(f"REBALANCE_FREQ: {REBALANCE_FREQ}")

    print("\n=== Factor Weights ===")
    if FACTOR_WEIGHTS:
        for factor, weight in FACTOR_WEIGHTS.items():
            print(f"{factor}: {weight}")
    else:
        print("No factor weights defined")

    print("\n=== Parallel Processing ===")
    print(f"NUM_PROCESSES: {NUM_PROCESSES}")
    print(f"SPLIT_BY: {SPLIT_BY}")

    print("\n=== END CONFIGURATION ===\n")


if __name__ == "__main__":
    print_config()