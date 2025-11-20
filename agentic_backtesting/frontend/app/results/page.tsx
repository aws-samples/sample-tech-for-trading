'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import AnimatedButton from '@/components/ui/AnimatedButton';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { AgentOutput } from '@/types/strategy';

function ResultsDisplayContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [results, setResults] = useState<AgentOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const jobId = searchParams.get('jobId');
    const strategyParam = searchParams.get('strategy');
    
    if (!jobId || !strategyParam) {
      setError('Missing job information');
      setLoading(false);
      return;
    }

    let strategy;
    try {
      strategy = JSON.parse(strategyParam);
    } catch (err) {
      setError('Invalid strategy data');
      setLoading(false);
      return;
    }

    // Start polling for results
    pollForResults(jobId, strategy);
  }, [searchParams]);

  const pollForResults = async (jobId: string, strategy: any) => {
    const maxAttempts = 60; // 5 minutes max
    const pollInterval = 5000; // 5 seconds
    
    for (let i = 0; i < maxAttempts; i++) {
      try {
        console.log(`[Results] 🔄 Polling attempt ${i + 1}/${maxAttempts} for job ${jobId}`);
        
        const response = await fetch(`/api/execute-backtest-async?jobId=${jobId}`);
        const result = await response.json();
        
        console.log('[Results] Poll result status:', result.status);
        
        if (result.status === 'complete') {
          console.log('[Results] ✅ Backtest complete!');
          const parsedResult = parseAgentResponse(result.data.analysis, strategy);
          setResults(parsedResult);
          setLoading(false);
          return;
        }
        
        if (result.status === 'error') {
          console.log('[Results] ❌ Backtest failed:', result.error);
          setError(result.error || 'Backtest failed');
          setLoading(false);
          return;
        }
        
        // Still processing, wait and continue
        if (i < maxAttempts - 1) {
          await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
        
      } catch (pollError) {
        console.error('[Results] Polling error:', pollError);
        // Continue polling on network errors
      }
    }
    
    // Timeout
    console.log('[Results] ⏰ Polling timeout');
    setError('Backtest timed out after 5 minutes');
    setLoading(false);
  };

  const parseAgentResponse = (analysisText: string, strategy: any): AgentOutput => {
    try {
      // Try to parse as JSON first
      let jsonData;
      
      // Check if the response contains JSON wrapped in markdown code blocks
      const jsonMatch = analysisText.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        jsonData = JSON.parse(jsonMatch[1]);
      } else {
        // Try parsing the entire text as JSON
        jsonData = JSON.parse(analysisText);
      }

      // Extract data from the new JSON format
      const backtestResult = jsonData.backtestResult || {};
      
      return {
        initial_investment: backtestResult.initialCapital || '100000',
        final_portfolio_value: backtestResult.finalPortfolioValue || 'N/A',
        total_return: backtestResult.totalReturn || 'N/A',
        maximum_drawdown: backtestResult.maxDrawdown || 'N/A',
        symbol: backtestResult.symbolTraded || strategy.stock_symbol,
        strategy_type: backtestResult.strategyName || strategy.name,
        stop_loss: `${strategy.stop_loss}%`,
        take_profit: `${strategy.take_profit}%`,
        max_positions: strategy.max_positions,
        profit_loss: backtestResult.profitLoss || 'N/A',
        sharpe_ratio: backtestResult.SharpeRatio || 'N/A',
        executive_summary: jsonData.executiveSummary || '',
        detailed_analysis: jsonData.detailedAnalysis || '',
        concerns_and_recommendations: jsonData.concernsAndRecommendations || {},
        analysis_text: analysisText
      };
    } catch (error) {
      console.error('[Results] Failed to parse JSON response, falling back to regex:', error);
      
      // Fallback to regex parsing for backward compatibility
      const extractMetric = (patterns: RegExp[]): string => {
        for (const pattern of patterns) {
          const match = analysisText.match(pattern);
          if (match) {
            return match[1].trim().replace(/\*\*/g, '').replace(/,/g, '');
          }
        }
        return 'N/A';
      };

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
        symbol: strategy.stock_symbol,
        strategy_type: strategy.name,
        stop_loss: `${strategy.stop_loss}%`,
        take_profit: `${strategy.take_profit}%`,
        max_positions: strategy.max_positions,
        analysis_text: analysisText
      };
    }
  };

  const handleNewStrategy = () => {
    router.push('/');
  };

  const parsePercentage = (value: string): number => {
    return parseFloat(value.replace('%', '').replace('+', ''));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex items-center justify-center">
        <LoadingSpinner 
          size="lg" 
          text="AgentCore is processing your backtest..." 
          overlay={false}
        />
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex items-center justify-center">
        <GlassCard className="p-8 max-w-md mx-4 text-center">
          <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">❌</span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">Error</h2>
          <p className="text-gray-300 mb-6">{error || 'Failed to load backtest results'}</p>
          <AnimatedButton onClick={handleNewStrategy} variant="primary">
            Try New Strategy
          </AnimatedButton>
        </GlassCard>
      </div>
    );
  }

  const totalReturn = parsePercentage(results.total_return);
  const performanceColor = totalReturn >= 0 ? 'text-accent-green' : 'text-red-400';
  const performanceEmoji = totalReturn >= 20 ? '🚀' : totalReturn >= 10 ? '✅' : totalReturn >= 0 ? '📈' : '⚠️';

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary">
      <div className="container mx-auto px-6 py-12">
        {/* Header */}
        <motion.div 
          className="mb-12"
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-5xl font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent mb-4">
            📈 Backtest Results
          </h1>
          <p className="text-xl text-gray-300">
            Your trading strategy performance powered by AgentCore
          </p>
        </motion.div>

        {/* Performance Overview */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-12"
        >
          <GlassCard className="p-8 text-center">
            <div className="flex items-center justify-center space-x-4 mb-6">
              <span className="text-6xl">{performanceEmoji}</span>
              <div>
                <h2 className="text-3xl font-bold text-white">Performance Overview</h2>
                <motion.div 
                  className={`text-5xl font-bold ${performanceColor}`}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.5 }}
                >
                  {results.total_return}
                </motion.div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.7 }}
              >
                <div className="text-gray-400 text-sm mb-1">Initial Investment</div>
                <div className="text-2xl font-bold text-white">
                  ${results.initial_investment}
                </div>
              </motion.div>
              
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.8 }}
              >
                <div className="text-gray-400 text-sm mb-1">Final Value</div>
                <div className="text-2xl font-bold text-accent-green">
                  ${results.final_portfolio_value}
                </div>
              </motion.div>
              
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.9 }}
              >
                <div className="text-gray-400 text-sm mb-1">Profit/Loss</div>
                <div className={`text-2xl font-bold ${parseFloat(results.profit_loss || '0') >= 0 ? 'text-accent-green' : 'text-red-400'}`}>
                  ${results.profit_loss || 'N/A'}
                </div>
              </motion.div>
              
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 1.0 }}
              >
                <div className="text-gray-400 text-sm mb-1">Max Drawdown</div>
                <div className="text-2xl font-bold text-red-400">
                  {results.maximum_drawdown}
                </div>
              </motion.div>
            </div>
            
            {/* Additional Metrics Row */}
            <div className="grid grid-cols-2 gap-6 mt-6 pt-6 border-t border-white/10">
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 1.1 }}
              >
                <div className="text-gray-400 text-sm mb-1">Sharpe Ratio</div>
                <div className="text-2xl font-bold text-accent-purple">
                  {results.sharpe_ratio || 'N/A'}
                </div>
              </motion.div>
              
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 1.2 }}
              >
                <div className="text-gray-400 text-sm mb-1">Symbol</div>
                <div className="text-2xl font-bold text-accent-blue">
                  {results.symbol}
                </div>
              </motion.div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Strategy Details */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="mb-12"
        >
          <GlassCard className="p-8">
            <h3 className="text-2xl font-semibold text-white mb-6">📋 Strategy Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <span className="text-gray-400">Strategy Type:</span>
                <p className="text-white text-lg font-medium mt-1">{results.strategy_type}</p>
              </div>
              <div>
                <span className="text-gray-400">Symbol:</span>
                <p className="text-white text-lg font-medium mt-1">{results.symbol}</p>
              </div>
              <div>
                <span className="text-gray-400">Stop Loss:</span>
                <p className="text-red-400 text-lg font-medium mt-1">{results.stop_loss}</p>
              </div>
              <div>
                <span className="text-gray-400">Take Profit:</span>
                <p className="text-accent-green text-lg font-medium mt-1">{results.take_profit}</p>
              </div>
              <div>
                <span className="text-gray-400">Max Positions:</span>
                <p className="text-white text-lg font-medium mt-1">{results.max_positions}</p>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* AI Agent Analysis */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mb-12"
        >
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-accent-purple to-accent-blue rounded-lg flex items-center justify-center">
              <span className="text-2xl">🤖</span>
            </div>
            <div>
              <h3 className="text-2xl font-bold text-white">AI Agent Analysis</h3>
              <p className="text-gray-400">Powered by Strands and AgentCore</p>
            </div>
          </div>

          {/* Executive Summary */}
          {results.executive_summary && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
              className="mb-6"
            >
              <GlassCard className="p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <span className="text-2xl">📊</span>
                  <h4 className="text-xl font-semibold text-white">Executive Summary</h4>
                </div>
                <p className="text-gray-300 leading-relaxed">
                  {results.executive_summary}
                </p>
              </GlassCard>
            </motion.div>
          )}

          {/* Detailed Analysis */}
          {results.detailed_analysis && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.7 }}
              className="mb-6"
            >
              <GlassCard className="p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <span className="text-2xl">🔍</span>
                  <h4 className="text-xl font-semibold text-white">Detailed Analysis</h4>
                </div>
                <p className="text-gray-300 leading-relaxed">
                  {results.detailed_analysis}
                </p>
              </GlassCard>
            </motion.div>
          )}

          {/* Concerns and Recommendations */}
          {results.concerns_and_recommendations && Object.keys(results.concerns_and_recommendations).length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
            >
              <GlassCard className="p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <span className="text-2xl">💡</span>
                  <h4 className="text-xl font-semibold text-white">Concerns & Recommendations</h4>
                </div>
                
                <div className="space-y-4">
                  {/* High Priority */}
                  {results.concerns_and_recommendations.highPriority && results.concerns_and_recommendations.highPriority.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-red-400 font-semibold">🔴 High Priority</span>
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-gray-300 ml-4">
                        {results.concerns_and_recommendations.highPriority.map((item: string, index: number) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Medium Priority */}
                  {results.concerns_and_recommendations.mediumPriority && results.concerns_and_recommendations.mediumPriority.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-yellow-400 font-semibold">🟡 Medium Priority</span>
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-gray-300 ml-4">
                        {results.concerns_and_recommendations.mediumPriority.map((item: string, index: number) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Consider Testing */}
                  {results.concerns_and_recommendations.considerTesting && results.concerns_and_recommendations.considerTesting.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-accent-blue font-semibold">🔵 Consider Testing</span>
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-gray-300 ml-4">
                        {results.concerns_and_recommendations.considerTesting.map((item: string, index: number) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          )}
        </motion.div>

        {/* Actions */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="flex justify-center"
        >
          <AnimatedButton
            onClick={handleNewStrategy}
            variant="accent"
            size="lg"
            glow={true}
            className="text-xl px-8 py-4"
          >
            🚀 Try Another Strategy
          </AnimatedButton>
        </motion.div>
      </div>
    </div>
  );
}

export default function ResultsDisplay() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading results..." />
      </div>
    }>
      <ResultsDisplayContent />
    </Suspense>
  );
}