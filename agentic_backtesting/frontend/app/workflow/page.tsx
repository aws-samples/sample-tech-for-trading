'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import AnimatedButton from '@/components/ui/AnimatedButton';
import { StrategyInput } from '@/types/strategy';
import { useBacktest } from '@/lib/BacktestContext';

interface WorkflowStep {
  id: string;
  name: string;
  component: string;
  description: string;
  status: 'pending' | 'active' | 'completed';
  details: string[];
}

interface AgentCoreComponent {
  name: string;
  icon: string;
  color: string;
  description: string;
  keyFeatures: string[];
}

function WorkflowProgressContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [strategyInput, setStrategyInput] = useState<StrategyInput | null>(null);
  const [isWaitingForResult, setIsWaitingForResult] = useState(false);
  const { result, error } = useBacktest();

  // AgentCore components information (simplified)
  const agentCoreComponents: Record<string, AgentCoreComponent> = {
    runtime: {
      name: 'AgentCore Runtime',
      icon: '⚡',
      color: '#00d4ff',
      description: 'Serverless, framework-agnostic hosting for AI agents',
      keyFeatures: [
        'Deploy agents with just a few lines of code',
        'Works with LangGraph, Strands, CrewAI, or custom frameworks',
        'Dedicated microVM isolation for security',
        'Extended execution up to 8 hours',
        'Consumption-based pricing'
      ]
    },
    gateway: {
      name: 'AgentCore Gateway',
      icon: '🌐',
      color: '#10b981',
      description: 'Build, deploy, and connect to tools at scale',
      keyFeatures: [
        'Transform existing APIs/Lambda into MCP-compatible tools',
        '1-click integration with popular services',
        'Comprehensive authentication management',
        'Semantic tool selection for agents',
        'Eliminates weeks of dev work'
      ]
    },
    memory: {
      name: 'AgentCore Memory',
      icon: '🧠',
      color: '#8b5cf6',
      description: 'Persistent knowledge with event and semantic memory',
      keyFeatures: [
        'Store and retrieve conversation history',
        'Semantic search across agent memories',
        'Event-based memory strategies',
        'Long-term context retention',
        'Multi-agent memory sharing'
      ]
    }
  };

  // Workflow steps matching your architecture
  const workflowSteps: WorkflowStep[] = [
    {
      id: 'orchestrator',
      name: 'Orchestrator Agent Triggered',
      component: 'runtime',
      description: 'AgentCore Runtime executes the orchestrator agent',
      status: 'pending',
      details: [
        'Agent deployed via AgentCore Runtime',
        'Serverless execution environment initialized',
        'Orchestrator coordinates the workflow'
      ]
    },
    {
      id: 'market_data',
      name: 'Fetch Market Data',
      component: 'gateway',
      description: 'Market data MCP server accessed through AgentCore Gateway',
      status: 'pending',
      details: [
        'Gateway transforms MCP server into agent tool',
        'Fetches historical price data',
        'Retrieves technical indicators'
      ]
    },
    {
      id: 'strategy_generation',
      name: 'Generate Strategy Code',
      component: 'runtime',
      description: 'Strategy code generation agent creates trading logic',
      status: 'pending',
      details: [
        'Analyzes buy/sell conditions',
        'Generates Python trading strategy',
        'Implements risk management rules'
      ]
    },
    {
      id: 'backtest',
      name: 'Execute Backtest',
      component: 'runtime',
      description: 'Backtest tool runs strategy simulation',
      status: 'pending',
      details: [
        'Simulates trades over historical data',
        'Calculates performance metrics',
        'Evaluates risk parameters'
      ]
    },
    {
      id: 'save_results',
      name: 'Save Results',
      component: 'memory',
      description: 'Results stored in AgentCore Memory',
      status: 'pending',
      details: [
        'Stores backtest results persistently',
        'Enables semantic search of past strategies',
        'Maintains execution history'
      ]
    },
    {
      id: 'collect_results',
      name: 'Collect & Display',
      component: 'runtime',
      description: 'Orchestrator retrieves results from memory',
      status: 'pending',
      details: [
        'Fetches results from AgentCore Memory',
        'Formats performance summary',
        'Returns to frontend for display'
      ]
    }
  ];

  const [steps, setSteps] = useState<WorkflowStep[]>(workflowSteps);

  useEffect(() => {
    // Get strategy from URL params
    const strategyParam = searchParams.get('strategy');
    if (!strategyParam) {
      router.push('/');
      return;
    }

    try {
      const parsedStrategy = JSON.parse(strategyParam);
      if (!parsedStrategy?.name) throw new Error('Invalid strategy data');
      setStrategyInput(parsedStrategy);
    } catch (error) {
      console.error('[Workflow] Parse error:', error);
      router.push('/');
    }
  }, [searchParams, router]);

  // Update step statuses based on current index
  useEffect(() => {
    setSteps(prev => prev.map((step, idx) => ({
      ...step,
      status: idx < currentStepIndex ? 'completed' : idx === currentStepIndex ? 'active' : 'pending'
    })));
  }, [currentStepIndex]);

  // Watch for result or error changes and navigate automatically
  useEffect(() => {
    if (!isWaitingForResult || !strategyInput) return;

    if (result) {
      console.log('[Workflow] ✅ Result found in context, navigating to results');
      setIsWaitingForResult(false);
      router.push(`/results?strategy=${encodeURIComponent(JSON.stringify(strategyInput))}`);
    } else if (error) {
      console.error('[Workflow] ❌ Error found in context:', error);
      setIsWaitingForResult(false);
    }
  }, [result, error, isWaitingForResult, strategyInput, router]);

  const handleNext = () => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const handleExecute = () => {
    if (!strategyInput) return;
    
    console.log('[Workflow] Starting to wait for API result from context...');
    
    // Check if result already exists
    if (result) {
      console.log('[Workflow] ✅ Result already available, navigating immediately');
      router.push(`/results?strategy=${encodeURIComponent(JSON.stringify(strategyInput))}`);
      return;
    }
    
    if (error) {
      console.error('[Workflow] ❌ Error already present:', error);
      return;
    }
    
    // Set waiting state - useEffect will handle navigation when result arrives
    setIsWaitingForResult(true);
  };

  const currentStep = steps[currentStepIndex];
  const currentComponentInfo = currentStep ? agentCoreComponents[currentStep.component] : agentCoreComponents.runtime;
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;
  const hasError = !!error;

  const getProgressPercentage = () => {
    return ((currentStepIndex + 1) / steps.length) * 100;
  };

  if (!strategyInput) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary">
      <div className="container mx-auto px-6 py-12">
        {/* Header */}
        <motion.div 
          className="text-center mb-12"
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-5xl font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent mb-4">
            🔄 AgentCore Workflow in Progress
          </h1>
          <p className="text-xl text-gray-300 mb-4">
            Watch as AgentCore services process your trading strategy
          </p>
          <p className="text-gray-400">
            Strategy: <span className="text-white font-medium">{strategyInput?.name}</span> | 
            Symbol: <span className="text-accent-blue font-medium">{strategyInput?.stock_symbol}</span>
          </p>
        </motion.div>

        {/* Overall Progress */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-12"
        >
          <GlassCard className="p-6">
            <h3 className="text-2xl font-semibold text-white mb-4">📊 Overall Progress</h3>
            <div className="relative h-4 bg-dark-tertiary rounded-full overflow-hidden mb-4">
              <motion.div 
                className="h-full bg-gradient-to-r from-accent-blue to-accent-purple"
                initial={{ width: 0 }}
                animate={{ width: `${getProgressPercentage()}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <div className="text-center text-gray-300">
              {Math.round(getProgressPercentage())}% Complete
            </div>
          </GlassCard>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Current Step Details */}
          <div className="lg:col-span-2 space-y-8">
            <AnimatePresence mode="wait">
              {currentStep && (
                <motion.div
                  key={currentStep.id}
                  initial={{ opacity: 0, x: -50 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 50 }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="glass-card p-8 border-2" style={{ borderColor: currentComponentInfo.color + '40' }}>
                    <div className="flex items-center space-x-4 mb-6">
                      <div 
                        className="w-16 h-16 rounded-full flex items-center justify-center"
                        style={{ backgroundColor: currentComponentInfo.color + '20' }}
                      >
                        <span className="text-3xl">{currentComponentInfo.icon}</span>
                      </div>
                      <div className="flex-1">
                        <h3 className="text-2xl font-semibold text-white">{currentStep.name}</h3>
                        <p className="text-gray-300">{currentStep.description}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-400">Step</div>
                        <div className="text-2xl font-bold text-white">{currentStepIndex + 1}/{steps.length}</div>
                      </div>
                    </div>

                    <div 
                      className="rounded-xl p-6 border"
                      style={{ 
                        backgroundColor: currentComponentInfo.color + '10',
                        borderColor: currentComponentInfo.color + '20'
                      }}
                    >
                      <h4 
                        className="text-lg font-semibold mb-3"
                        style={{ color: currentComponentInfo.color }}
                      >
                        🏗️ {currentComponentInfo.name}
                      </h4>
                      <p className="text-gray-300 mb-4">{currentComponentInfo.description}</p>
                      
                      <div className="space-y-2 mb-4">
                        <h5 className="text-sm font-semibold text-gray-400">Key Features:</h5>
                        <ul className="text-sm text-gray-300 space-y-1">
                          {currentComponentInfo.keyFeatures.map((feature, index) => (
                            <li key={index}>• {feature}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="space-y-2">
                        <h5 className="text-sm font-semibold text-gray-400">Current Step Details:</h5>
                        <ul className="text-sm text-gray-300 space-y-1">
                          {currentStep.details.map((detail, index) => (
                            <motion.li 
                              key={index}
                              initial={{ opacity: 0, x: -20 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: index * 0.2 }}
                            >
                              ✓ {detail}
                            </motion.li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error Display */}
            {hasError && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <GlassCard className="p-6 border-2 border-red-400/50 bg-red-900/10">
                  <div className="flex items-start space-x-3">
                    <div className="text-3xl">❌</div>
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-red-400 mb-2">Error Occurred</h4>
                      <p className="text-gray-300 text-sm">{error}</p>
                      <AnimatedButton
                        onClick={() => router.push('/')}
                        variant="secondary"
                        size="sm"
                        className="mt-4"
                      >
                        ← Back to Strategy Builder
                      </AnimatedButton>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {/* Navigation Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <GlassCard className="p-6">
                <div className="flex items-center justify-between gap-4">
                  <AnimatedButton
                    onClick={handlePrevious}
                    disabled={isFirstStep || isWaitingForResult}
                    variant="secondary"
                    size="lg"
                    className="flex-1"
                  >
                    ← Previous Step
                  </AnimatedButton>

                  {!isLastStep ? (
                    <AnimatedButton
                      onClick={handleNext}
                      disabled={isWaitingForResult}
                      variant="accent"
                      size="lg"
                      glow
                      className="flex-1"
                    >
                      Next Step →
                    </AnimatedButton>
                  ) : (
                    <AnimatedButton
                      onClick={handleExecute}
                      disabled={isWaitingForResult || hasError}
                      loading={isWaitingForResult}
                      variant="accent"
                      size="lg"
                      glow
                      className="flex-1"
                    >
                      {isWaitingForResult ? 'Waiting for Results...' : hasError ? '❌ Error Occurred' : '🚀 View Results'}
                    </AnimatedButton>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </div>

          {/* Workflow Steps */}
          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
            >
              <GlassCard className="p-6">
                <h3 className="text-xl font-semibold text-white mb-4">📋 Workflow Steps</h3>
                <div className="space-y-3">
                  {steps.map((step, index) => (
                    <motion.div 
                      key={step.id} 
                      className={`flex items-center space-x-3 p-3 rounded-lg transition-all cursor-pointer ${
                        step.status === 'active' ? 'bg-white/5' : ''
                      }`}
                      onClick={() => setCurrentStepIndex(index)}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        step.status === 'completed' ? 'bg-accent-green' : 
                        step.status === 'active' ? 'bg-accent-blue' : 
                        'bg-gray-600'
                      }`}>
                        {step.status === 'completed' ? (
                          <span className="text-white text-sm">✓</span>
                        ) : (
                          <span className="text-white text-sm">{index + 1}</span>
                        )}
                      </div>
                      <div className="flex-1">
                        <p className={`text-sm font-medium ${
                          step.status === 'completed' ? 'text-accent-green' : 
                          step.status === 'active' ? 'text-accent-blue' : 
                          'text-gray-400'
                        }`}>
                          {step.name}
                        </p>
                        <p className="text-xs text-gray-500">{agentCoreComponents[step.component].name}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </GlassCard>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}


export default function WorkflowProgress() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading workflow..." />
      </div>
    }>
      <WorkflowProgressContent />
    </Suspense>
  );
}
