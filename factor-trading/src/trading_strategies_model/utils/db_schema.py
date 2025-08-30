"""
Database schema definitions for ClickHouse tables to store backtest data.
"""

# SQL statements to create the necessary tables in ClickHouse

# Strategy definition table
CREATE_STRATEGY_TABLE = """
CREATE TABLE IF NOT EXISTS strategy_definitions (
    strategy_id UUID DEFAULT generateUUIDv4(),
    strategy_name String,
    strategy_class String,
    strategy_description String,
    strategy_parameters String, -- JSON string of parameters
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now(),
    created_by String,
    is_active UInt8 DEFAULT 1,
    PRIMARY KEY (strategy_id)
) ENGINE = MergeTree()
ORDER BY (strategy_id, created_at);
"""

# Backtest table - stores backtest parameters and performance metrics
CREATE_BACKTEST_TABLE = """
CREATE TABLE IF NOT EXISTS backtests (
    backtest_id UUID DEFAULT generateUUIDv4(),
    strategy_id UUID,
    start_date Date,
    end_date Date,
    initial_capital Float64,
    final_capital Float64,
    rebalance_period UInt16,
    take_profit_pct Float32 DEFAULT NULL,
    stop_loss_pct Float32 DEFAULT NULL,
    cooldown_period UInt16 DEFAULT 0,
    max_position_size Float32,
    factors Array(String),
    weighting_method String,
    sharpe_ratio Float64,
    max_drawdown Float64,
    max_drawdown_date Date,
    total_return Float64,
    annual_return Float64,
    num_trades UInt32,
    win_rate Float32,
    profit_factor Float64,
    strategy_parameters String, -- JSON string of strategy-specific parameters
    created_at DateTime DEFAULT now(),
    run_by String,
    notes String DEFAULT '',
    PRIMARY KEY (backtest_id)
) ENGINE = MergeTree()
ORDER BY (backtest_id, strategy_id, start_date);
"""

# Backtest portfolio - stores portfolio snapshots during backtest
CREATE_BACKTEST_PORTFOLIO_TABLE = """
CREATE TABLE IF NOT EXISTS backtest_portfolios (
    portfolio_id UUID DEFAULT generateUUIDv4(),
    backtest_id UUID,
    date Date,
    portfolio_value Float64,
    cash Float64,
    equity Float64,
    is_initial UInt8 DEFAULT 0, -- 1 if this is the initial portfolio
    is_final UInt8 DEFAULT 0,   -- 1 if this is the final portfolio
    portfolio_snapshot String,  -- JSON string of portfolio positions
    PRIMARY KEY (backtest_id, date, portfolio_id)
) ENGINE = MergeTree()
ORDER BY (backtest_id, date, portfolio_id);
"""

# Backtest orders - stores all orders generated during backtest
CREATE_BACKTEST_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS backtest_orders (
    order_id UUID DEFAULT generateUUIDv4(),
    backtest_id UUID,
    date DateTime,
    symbol String,
    order_type String, -- 'BUY', 'SELL'
    order_price Float64,
    order_size Float64,
    order_value Float64,
    execution_status String DEFAULT 'PENDING', -- 'PENDING', 'EXECUTED', 'CANCELED', 'REJECTED'
    execution_price Float64 DEFAULT NULL,
    reason String DEFAULT '', -- e.g., 'REBALANCE', 'TAKE_PROFIT', 'STOP_LOSS'
    PRIMARY KEY (backtest_id, date, symbol, order_id)
) ENGINE = MergeTree()
ORDER BY (backtest_id, date, symbol, order_id);
"""

# Backtest trades - stores all completed trades during backtest
CREATE_BACKTEST_TRADES_TABLE = """
CREATE TABLE IF NOT EXISTS backtest_trades (
    trade_id UUID DEFAULT generateUUIDv4(),
    backtest_id UUID,
    symbol String,
    entry_date DateTime,
    entry_price Float64,
    entry_size Float64,
    entry_value Float64,
    exit_date DateTime,
    exit_price Float64,
    exit_size Float64,
    exit_value Float64,
    pnl Float64,
    pnl_pct Float64,
    duration_days Float32,
    exit_reason String, -- e.g., 'REBALANCE', 'TAKE_PROFIT', 'STOP_LOSS'
    PRIMARY KEY (backtest_id, symbol, entry_date, trade_id)
) ENGINE = MergeTree()
ORDER BY (backtest_id, symbol, entry_date, trade_id);
"""

# All tables in order of creation (for dependencies)
CREATE_TABLES = [
    CREATE_STRATEGY_TABLE,
    CREATE_BACKTEST_TABLE,
    CREATE_BACKTEST_PORTFOLIO_TABLE,
    CREATE_BACKTEST_ORDERS_TABLE,
    CREATE_BACKTEST_TRADES_TABLE
]
