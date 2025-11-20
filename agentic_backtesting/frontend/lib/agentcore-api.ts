/**
 * API service for communicating with AgentCore via Next.js API Routes
 */

import { StrategyInput, AgentOutput, AgentCoreResponse } from '@/types/strategy';

class AgentCoreAPI {
  private useMockData: boolean;

  constructor() {
    // Check if mock mode is enabled (from environment variable)
    this.useMockData = process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true';
  }

  async executeBacktest(strategyInput: StrategyInput): Promise<AgentOutput> {
    if (this.useMockData) {
      console.log('[API] Using mock data');
      return this.generateMockOutput(strategyInput);
    }

    try {
      console.log('[API] Starting async backtest...');
      // Start async job
      const startResponse = await fetch('/api/execute-backtest-async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(strategyInput),
      });

      if (!startResponse.ok) {
        throw new Error(`HTTP ${startResponse.status}`);
      }

      const { jobId } = await startResponse.json();
      console.log('[API] Job started, ID:', jobId);
      
      // Poll for results
      return await this.pollForResults(jobId, strategyInput);
      
    } catch (error) {
      console.error('[API] Error:', error);
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch')) {
          throw new Error('Cannot connect to API');
        }
      }
      throw error;
    }
  }

  private async pollForResults(jobId: string, strategyInput: StrategyInput): Promise<AgentOutput> {
    const maxAttempts = 60; // 5 minutes max
    const pollInterval = 5000; // 5 seconds
    
    for (let i = 0; i < maxAttempts; i++) {
      if (i > 0) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
      
      console.log(`[API] Polling attempt ${i + 1}/${maxAttempts}...`);
      const response = await fetch(`/api/execute-backtest-async?jobId=${jobId}`);
      const result = await response.json();
      console.log('[API] Poll result:', result.status);
      
      if (result.status === 'complete') {
        console.log('[API] Backtest complete!');
        return this.parseAgentResponse(result.data.analysis, strategyInput);
      }
      
      if (result.status === 'error') {
        throw new Error(result.error || 'Backtest failed');
      }
      
      // Still processing, continue polling
    }
    
    throw new Error('Backtest timed out after 5 minutes');
  }

  /**
   * Parse the agent's markdown response to extract performance metrics
   * Public so it can be used with cached results
   */
  parseAgentResponse(analysisText: string, strategyInput: StrategyInput): AgentOutput {
    // Extract metrics using flexible regex patterns
    const extractMetric = (patterns: RegExp[]): string => {
      for (const pattern of patterns) {
        const match = analysisText.match(pattern);
        if (match) {
          return match[1].trim().replace(/\*\*/g, '').replace(/,/g, '');
        }
      }
      return 'N/A';
    };

    // Try multiple patterns for each metric
    const initialCapital = extractMetric([
      /Initial Investment[:\s*]+\$?([\d,]+)/i,
      /Initial Capital[:\s*]+\$?([\d,]+)/i,
    ]) || '100000';
    
    const finalValue = extractMetric([
      /Final Value[:\s*]+\$?([\d,]+\.?\d*)/i,
      /Final Portfolio Value[:\s*]+\$?([\d,]+\.?\d*)/i,
    ]);
    
    const totalReturn = extractMetric([
      /Total Return[:\s*]+([+-]?[\d.]+%)/i,
    ]);
    
    const maxDrawdown = extractMetric([
      /Maximum Drawdown[:\s*]+([\d.]+%)/i,
      /Max Drawdown[:\s*]+([\d.]+%)/i,
    ]);

    return {
      initial_investment: initialCapital,
      final_portfolio_value: finalValue,
      total_return: totalReturn,
      maximum_drawdown: maxDrawdown,
      symbol: strategyInput.stock_symbol,
      strategy_type: strategyInput.name,
      stop_loss: `${strategyInput.stop_loss}%`,
      take_profit: `${strategyInput.take_profit}%`,
      max_positions: strategyInput.max_positions,
      analysis_text: analysisText
    };
  }

  /**
   * Generate mock output for testing UI (temporary - remove when agent is ready)
   */
  private generateMockOutput(strategyInput: StrategyInput): Promise<AgentOutput> {
    // Simulate processing delay
    return new Promise((resolve) => {
      setTimeout(() => {
        const initialInvestment = 100000;
        const returnPct = (Math.random() * 30) - 5; // -5% to +25%
        const finalValue = initialInvestment * (1 + returnPct / 100);
        const maxDrawdown = Math.random() * 10;

        const mockAnalysis = `## Strategy Performance Analysis - ${strategyInput.name}

### Key Performance Metrics:
- **Initial Capital**: $${initialInvestment.toLocaleString()}
- **Final Portfolio Value**: $${finalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
- **Total Return**: ${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%
- **Maximum Drawdown**: ${maxDrawdown.toFixed(2)}%

### Analysis:
This is mock data for testing the UI. Configure your AWS credentials and set NEXT_PUBLIC_USE_MOCK_DATA=false to use the real AgentCore agent.`;

        resolve({
          initial_investment: `${initialInvestment.toLocaleString()}`,
          final_portfolio_value: `${finalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          total_return: `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%`,
          maximum_drawdown: `${maxDrawdown.toFixed(2)}%`,
          symbol: strategyInput.stock_symbol,
          strategy_type: `${strategyInput.name}`,
          stop_loss: `${strategyInput.stop_loss}%`,
          take_profit: `${strategyInput.take_profit}%`,
          max_positions: strategyInput.max_positions,
          analysis_text: mockAnalysis
        });
      }, 2000); // 2 second delay to simulate processing
    });
  }
}

// Export singleton instance
export const agentCoreAPI = new AgentCoreAPI();
export default agentCoreAPI;
