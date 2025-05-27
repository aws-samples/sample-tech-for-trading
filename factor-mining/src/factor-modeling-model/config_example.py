import os
# from dotenv import load_dotenv
import ast

# Load environment variables from .env file
# load_dotenv()

# ClickHouse configuration
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'your_clickhouse_host')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'your_username')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'your_password')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'factor_model_tick_data_database')

# Factor analysis configuration
START_DATE = os.getenv('START_DATE', '2020-01-01')
END_DATE = os.getenv('END_DATE', '2025-03-31')

# DJIA tickers
DJIA_TICKERS_STR = os.getenv('DJIA_TICKERS', 'AAPL,AMGN,AMZN,AXP,BA,CAT,CRM,CSCO,CVX,DIS,GS,HD,HON,IBM,JNJ,JPM,KO,MCD,MMM,MRK,MSFT,NKE,NVDA,PG,SHW,TRV,UNH,V,VZ,WMT')
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
