// Strategy input matching your agent's expected format
export interface StrategyInput {
  name: string;
  stock_symbol: string;
  backtest_window: string;
  max_positions: number;
  stop_loss: number;
  take_profit: number;
  buy_conditions: string;
  sell_conditions: string;
}

// AgentCore response from API route
export interface AgentCoreResponse {
  success: boolean;
  analysis: string;
  raw_response?: any;
  session_id?: string;
  error?: string;
  error_type?: string;
}

// Agent output format (parsed from AgentCore response)
export interface AgentOutput {
  initial_investment: string;
  final_portfolio_value: string;
  total_return: string;
  maximum_drawdown: string;
  symbol: string;
  strategy_type: string;
  stop_loss: string;
  take_profit: string;
  max_positions: number;
  profit_loss?: string;
  sharpe_ratio?: string;
  executive_summary?: string;
  detailed_analysis?: string;
  concerns_and_recommendations?: {
    highPriority?: string[];
    mediumPriority?: string[];
    considerTesting?: string[];
  };
  analysis_text?: string; // Full markdown analysis from agent
}

export interface StockOption {
  symbol: string;
  name: string;
}

export const AVAILABLE_STOCKS: StockOption[] = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'TSLA', name: 'Tesla, Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'META', name: 'Meta Platforms Inc.' },
  { symbol: 'NFLX', name: 'Netflix Inc.' }
];

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}
