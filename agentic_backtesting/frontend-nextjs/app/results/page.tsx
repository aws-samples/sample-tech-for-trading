'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import AnimatedButton from '@/components/ui/AnimatedButton';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { StrategyInput, AgentOutput } from '@/types/strategy';
import { useBacktest } from '@/lib/BacktestContext';

export default function ResultsDisplay() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { result: contextResult, error: contextError } = useBacktest();
  const [results, setResults] = useState<AgentOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [strategyInput, setStrategyInput] = useState<StrategyInput | null>(null);

  useEffect(() => {
    const loadResults = () => {
      const strategyParam = searchParams.get('strategy');
      
      if (!strategyParam) {
        setError('No strategy data provided');
        setLoading(false);
        return;
      }

      try {
        const strategy = JSON.parse(strategyParam);
        
        if (!strategy?.name) {
          throw new Error('Invalid strategy data');
        }
        
        setStrategyInput(strategy);
        
        // Check if we have result from context (workflow page)
        if (contextResult) {
          console.log('[Results] ✅ Using result from context (no API call)');
          setResults(contextResult);
          setLoading(false);
          return;
        }
        
        // Check if there was an error from context
        if (contextError) {
          console.log('[Results] Error from context:', contextError);
          setError(contextError);
          setLoading(false);
          return;
        }
        
        // If no context result, wait for it (API might still be running)
        console.log('[Results] Waiting for API result from workflow...');
        const checkInterval = setInterval(() => {
          if (contextResult) {
            console.log('[Results] ✅ Received result from context');
            setResults(contextResult);
            setLoading(false);
            clearInterval(checkInterval);
          } else if (contextError) {
            setError(contextError);
            setLoading(false);
            clearInterval(checkInterval);
          }
        }, 100);
        
        // No timeout - let it run as long as needed
        
      } catch (err) {
        console.error('[Results] Error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load results');
        setLoading(false);
      }
    };

    loadResults();
  }, [searchParams, contextResult, contextError]);

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
                <div className="text-gray-400 text-sm mb-1">Max Drawdown</div>
                <div className="text-2xl font-bold text-red-400">
                  {results.maximum_drawdown}
                </div>
              </motion.div>
              
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 1.0 }}
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
        {results.analysis_text && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="mb-12"
          >
            <GlassCard className="p-8">
              <h3 className="text-2xl font-semibold text-white mb-6">🤖 AI Agent Analysis</h3>
              <div className="prose prose-invert max-w-none">
                <div className="text-gray-300 whitespace-pre-wrap">
                  {results.analysis_text}
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

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
