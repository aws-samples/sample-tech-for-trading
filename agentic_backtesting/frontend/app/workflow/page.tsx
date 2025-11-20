'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import AnimatedButton from '@/components/ui/AnimatedButton';

function WorkflowProgressContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);

  // No auto-navigation on workflow page - user controls when to view results

  const handleViewResults = () => {
    const strategyParam = searchParams.get('strategy');
    const jobId = searchParams.get('jobId');
    
    if (strategyParam && jobId) {
      // Navigate to results page with strategy and jobId
      router.push(`/results?strategy=${strategyParam}&jobId=${jobId}`);
    } else {
      // Fallback to home if missing data
      router.push('/');
    }
  };

  const getComponentInfo = (componentId: string) => {
    const components: Record<string, any> = {
      client: {
        title: "Client Frontend",
        icon: "💻",
        color: "#6b7280",
        description: "Here is where you are.",
        details: [],
        agentCoreRole: ""
      },
      orchestrator: {
        title: "Orchestrator Agent",
        icon: "🤖",
        color: "#00d4ff",
        description: "The intelligent central coordinator that analyzes your request and dynamically selects the right tools and agents to execute your trading strategy analysis.",
        details: [
          "Analyzes strategy requirements intelligently",
          "Makes real-time decisions about tool selection",
          "Coordinates multiple specialized agents",
          "Adapts execution based on strategy complexity",
          "Handles error recovery and retry logic"
        ],
        agentCoreRole: "Powered by AgentCore Runtime - serverless, scalable agent execution with dedicated microVM isolation for security."
      },
      gateway: {
        title: "Market Data Tool",
        icon: "📊",
        color: "#10b981",
        description: "Provides access to historical market data, technical indicators, and price information through AgentCore Gateway's seamless API integration.",
        details: [
          "Fetches historical price data",
          "Calculates technical indicators (EMA, SMA, RSI)",
          "Handles rate limiting and authentication",
          "Transforms raw data into agent-friendly format"
        ],
        agentCoreRole: "AgentCore Gateway transforms external market data APIs into MCP-compatible tools, eliminating integration complexity."
      },
      strategy_agent: {
        title: "Strategy Generation Agent",
        icon: "⚙️",
        color: "#00d4ff",
        description: "A specialized AI agent that converts your natural language trading conditions into executable Python code using the Backtrader framework.",
        details: [
          "Interprets buy/sell conditions from natural language",
          "Generates optimized Backtrader strategy code",
          "Implements risk management rules",
          "Handles position sizing and portfolio management"
        ],
        agentCoreRole: "Another agent running on AgentCore Runtime, demonstrating multi-agent coordination capabilities."
      },
      backtest_tool: {
        title: "Backtest Tool (Strands)",
        icon: "🔬",
        color: "#f59e0b",
        description: "Executes the trading strategy simulation using the Strands framework, running comprehensive backtests against historical market data.",
        details: [
          "Simulates trades over historical periods",
          "Calculates comprehensive performance metrics",
          "Evaluates risk parameters and drawdowns",
          "Generates detailed execution reports"
        ],
        agentCoreRole: "Integrated as a tool within AgentCore Runtime, showing the platform's flexibility with different frameworks."
      },
      summary_agent: {
        title: "Result Summary Agent",
        icon: "📈",
        color: "#00d4ff",
        description: "Analyzes backtest results and generates comprehensive insights, recommendations, and performance summaries for easy understanding.",
        details: [
          "Processes raw backtest data",
          "Generates human-readable analysis",
          "Provides actionable recommendations",
          "Creates performance summaries and insights"
        ],
        agentCoreRole: "Final agent in the orchestration, running on AgentCore Runtime to provide intelligent analysis of results."
      },
      memory: {
        title: "AgentCore Memory",
        icon: "💾",
        color: "#8b5cf6",
        description: "Persistent knowledge storage that maintains strategy history, results, and learnings across sessions for continuous improvement.",
        details: [
          "Stores backtest results persistently",
          "Enables semantic search of past strategies",
          "Maintains execution history and patterns",
          "Supports cross-session learning and optimization"
        ],
        agentCoreRole: "AgentCore Memory provides the knowledge foundation, allowing the orchestrator to learn from past executions."
      }
    };
    return components[componentId];
  };

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
            🏗️ AgentCore Architecture
          </h1>
          <p className="text-xl text-gray-300">
            Explore the intelligent orchestrator architecture powering your trading strategy analysis
          </p>
        </motion.div>

        {/* Interactive Architecture Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-16"
        >
          <GlassCard className="p-4 md:p-8">
            <div className="text-center mb-6 md:mb-8">
              <h3 className="text-xl md:text-2xl font-bold text-white mb-2">Interactive Architecture Diagram</h3>
              <p className="text-sm md:text-base text-gray-400">Tap any component to learn more about its role</p>
            </div>

            {/* Mobile: Show components as a list */}
            <div className="block md:hidden space-y-4 mb-8">
              {[
                { id: 'client', name: 'Client Frontend', icon: '💻', color: '#6b7280' },
                { id: 'orchestrator', name: 'Orchestrator Agent', icon: '🤖', color: '#00d4ff' },
                { id: 'gateway', name: 'Market Data Tool', icon: '📊', color: '#10b981' },
                { id: 'strategy_agent', name: 'Strategy Agent', icon: '⚙️', color: '#00d4ff' },
                { id: 'backtest_tool', name: 'Backtest Tool', icon: '🔬', color: '#f59e0b' },
                { id: 'summary_agent', name: 'Result Summary Agent', icon: '📈', color: '#00d4ff' },
                { id: 'memory', name: 'AgentCore Memory', icon: '💾', color: '#8b5cf6' }
              ].map((component) => (
                <motion.button
                  key={component.id}
                  className="w-full p-4 rounded-xl border-2 text-left transition-all duration-200 hover:scale-105"
                  style={{ 
                    backgroundColor: component.color + '15',
                    borderColor: component.color + '40'
                  }}
                  onClick={() => setSelectedComponent(component.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-center space-x-4">
                    <div 
                      className="w-12 h-12 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: component.color + '30' }}
                    >
                      <span className="text-2xl">{component.icon}</span>
                    </div>
                    <div>
                      <h4 className="text-white font-semibold text-lg">{component.name}</h4>
                      <p className="text-gray-400 text-sm">Tap to learn more</p>
                    </div>
                  </div>
                </motion.button>
              ))}
            </div>

            {/* Desktop: Show SVG diagram */}
            <div className="hidden md:block relative w-full max-w-7xl mx-auto">
              <svg viewBox="0 0 1400 900" className="w-full h-auto min-h-[500px] lg:min-h-[600px]">
                {/* Background */}
                <rect width="1400" height="900" fill="transparent" />

                {/* Client */}
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <rect x="40" y="340" width="140" height="90" rx="10" 
                        fill="#1f2937" stroke="#6b7280" strokeWidth="2"
                        className="cursor-pointer hover:stroke-accent-blue transition-colors"
                        onClick={() => setSelectedComponent('client')}
                  />
                  <text x="110" y="380" textAnchor="middle" fill="#e5e7eb" fontSize="16" fontWeight="bold">
                    Client
                  </text>
                  <text x="110" y="405" textAnchor="middle" fill="#9ca3af" fontSize="14">
                    Frontend
                  </text>
                </motion.g>

                {/* Orchestrator Agent (Central) */}
                <motion.g
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  {/* Outer AgentCore Runtime container with dashed border */}
                  <rect x="460" y="320" width="280" height="180" rx="20" 
                        fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="600" y="340" textAnchor="middle" fill="#8b5cf6" fontSize="14" fontWeight="bold">
                    AgentCore Runtime
                  </text>
                  
                  {/* Inner agent box - smaller and centered */}
                  <rect x="490" y="370" width="220" height="100" rx="15" 
                        fill="#00d4ff20" stroke="#00d4ff" strokeWidth="3"
                        className="cursor-pointer hover:fill-accent-blue/30 transition-colors"
                        onClick={() => setSelectedComponent('orchestrator')}
                  />
                  <text x="600" y="425" textAnchor="middle" fill="#00d4ff" fontSize="18" fontWeight="bold">
                    🤖 Orchestrator Agent
                  </text>
                  

                </motion.g>

                {/* Market Data Tool (Gateway) */}
                <motion.g
                  initial={{ opacity: 0, x: -50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  {/* Outer AgentCore Gateway container with dashed border */}
                  <rect x="900" y="120" width="240" height="150" rx="15" 
                        fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="1020" y="140" textAnchor="middle" fill="#10b981" fontSize="12" fontWeight="bold">
                    AgentCore Gateway
                  </text>
                  
                  {/* Inner tool box - smaller and centered */}
                  <rect x="920" y="160" width="200" height="80" rx="10" 
                        fill="#10b98120" stroke="#10b981" strokeWidth="2"
                        className="cursor-pointer hover:fill-accent-green/30 transition-colors"
                        onClick={() => setSelectedComponent('gateway')}
                  />
                  <text x="1020" y="205" textAnchor="middle" fill="#10b981" fontSize="16" fontWeight="bold">
                    📊 Market Data Tool
                  </text>
                </motion.g>

                {/* Strategy Generation Agent */}
                <motion.g
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 }}
                >
                  {/* Outer AgentCore Runtime container with dashed border */}
                  <rect x="900" y="320" width="240" height="150" rx="15" 
                        fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="1020" y="340" textAnchor="middle" fill="#8b5cf6" fontSize="12" fontWeight="bold">
                    AgentCore Runtime
                  </text>
                  
                  {/* Inner agent box - smaller and centered */}
                  <rect x="920" y="360" width="200" height="80" rx="10" 
                        fill="#00d4ff20" stroke="#00d4ff" strokeWidth="2"
                        className="cursor-pointer hover:fill-accent-blue/30 transition-colors"
                        onClick={() => setSelectedComponent('strategy_agent')}
                  />
                  <text x="1020" y="405" textAnchor="middle" fill="#00d4ff" fontSize="16" fontWeight="bold">
                    ⚙️ Strategy Agent
                  </text>
                  

                </motion.g>

                {/* Backtest Tool (Strands) */}
                <motion.g
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 }}
                >
                  <rect x="920" y="520" width="200" height="110" rx="10" 
                        fill="#f59e0b20" stroke="#f59e0b" strokeWidth="2"
                        className="cursor-pointer hover:fill-yellow-500/30 transition-colors"
                        onClick={() => setSelectedComponent('backtest_tool')}
                  />
                  <text x="1020" y="580" textAnchor="middle" fill="#f59e0b" fontSize="16" fontWeight="bold">
                    🔬 Backtest Tool
                  </text>
                </motion.g>

                {/* Result Summary Agent */}
                <motion.g
                  initial={{ opacity: 0, y: 50 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 }}
                >
                  {/* Outer AgentCore Runtime container with dashed border */}
                  <rect x="460" y="620" width="280" height="150" rx="15" 
                        fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="600" y="640" textAnchor="middle" fill="#8b5cf6" fontSize="12" fontWeight="bold">
                    AgentCore Runtime
                  </text>
                  
                  {/* Inner agent box - smaller and centered */}
                  <rect x="490" y="660" width="220" height="80" rx="10" 
                        fill="#00d4ff20" stroke="#00d4ff" strokeWidth="2"
                        className="cursor-pointer hover:fill-accent-blue/30 transition-colors"
                        onClick={() => setSelectedComponent('summary_agent')}
                  />
                  <text x="600" y="705" textAnchor="middle" fill="#00d4ff" fontSize="16" fontWeight="bold">
                    📈 Summary Agent
                  </text>
                  

                </motion.g>

                {/* AgentCore Memory */}
                <motion.g
                  initial={{ opacity: 0, y: 50 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.9 }}
                >
                  {/* Outer AgentCore Memory container with dashed border */}
                  <rect x="120" y="620" width="240" height="150" rx="15" 
                        fill="none" stroke="#ec4899" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="240" y="640" textAnchor="middle" fill="#ec4899" fontSize="12" fontWeight="bold">
                    AgentCore Memory
                  </text>
                  
                  {/* Inner memory box - smaller and centered */}
                  <rect x="140" y="660" width="200" height="80" rx="10" 
                        fill="#ec489920" stroke="#ec4899" strokeWidth="2"
                        className="cursor-pointer hover:fill-pink-500/30 transition-colors"
                        onClick={() => setSelectedComponent('memory')}
                  />
                  <text x="240" y="705" textAnchor="middle" fill="#ec4899" fontSize="16" fontWeight="bold">
                    💾 Memory Storage
                  </text>
                </motion.g>

                {/* Connection Lines */}
                <g stroke="#6b7280" strokeWidth="2" fill="none" strokeDasharray="5,5">
                  {/* Client to Orchestrator */}
                  <line x1="180" y1="385" x2="460" y2="420" />
                  
                  {/* Orchestrator to Tools */}
                  <line x1="740" y1="400" x2="900" y2="200" />
                  <line x1="740" y1="420" x2="900" y2="400" />
                  <line x1="740" y1="440" x2="920" y2="575" />
                  
                  {/* Orchestrator to Summary Agent */}
                  <line x1="600" y1="500" x2="600" y2="620" />
                  
                  {/* Summary Agent to Memory */}
                  <line x1="460" y1="700" x2="360" y2="700" />
                </g>

                {/* Data Flow Animation */}
                {selectedComponent && (
                  <motion.circle r="4" fill="#00d4ff" opacity="0.8">
                    <animateMotion dur="3s" repeatCount="indefinite">
                      <path d="M170,390 Q350,400 460,420 Q650,410 900,400" />
                    </animateMotion>
                  </motion.circle>
                )}
              </svg>
            </div>

            {/* Component Information Popup - Mobile Optimized */}
            <AnimatePresence>
              {selectedComponent && (
                <motion.div
                  className="fixed inset-0 bg-black/70 flex items-end md:items-center justify-center z-50 p-0 md:p-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setSelectedComponent(null)}
                >
                  <motion.div
                    className="w-full md:max-w-4xl md:w-full max-h-[85vh] md:max-h-[90vh] overflow-y-auto"
                    initial={{ y: "100%", opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: "100%", opacity: 0 }}
                    transition={{ type: "spring", damping: 25, stiffness: 200 }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="bg-dark-secondary md:bg-dark-secondary/95 md:backdrop-blur-xl border-t-4 md:border md:rounded-2xl border-gray-600 md:border-gray-600/50">
                      {(() => {
                        const info = getComponentInfo(selectedComponent);
                        return (
                          <div className="p-6 md:p-8">
                            {/* Header */}
                            <div className="flex items-start justify-between mb-6">
                              <div className="flex items-center space-x-4 flex-1">
                                <div 
                                  className="w-16 h-16 md:w-20 md:h-20 rounded-2xl flex items-center justify-center shadow-lg flex-shrink-0"
                                  style={{ 
                                    backgroundColor: info.color + '25',
                                    boxShadow: `0 8px 32px ${info.color}40`
                                  }}
                                >
                                  <span className="text-3xl md:text-4xl">{info.icon}</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h3 
                                    className="text-xl md:text-2xl font-bold mb-1 leading-tight"
                                    style={{ color: info.color }}
                                  >
                                    {info.title}
                                  </h3>
                                  <p className="text-gray-400 text-sm md:text-base">Component Details</p>
                                </div>
                              </div>
                              
                              {/* Close button - Mobile */}
                              <button
                                onClick={() => setSelectedComponent(null)}
                                className="md:hidden w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-gray-300 hover:text-white hover:bg-gray-600 transition-colors flex-shrink-0 ml-4"
                              >
                                ✕
                              </button>
                            </div>

                            {/* Description */}
                            <div className="mb-8">
                              <p className="text-gray-200 text-base md:text-lg leading-relaxed">
                                {info.description}
                              </p>
                            </div>

                            {/* Content - Only show for non-client components */}
                            {selectedComponent !== 'client' && (
                              <div className="space-y-8 md:space-y-0 md:grid md:grid-cols-2 md:gap-8 mb-8">
                                {/* Key Capabilities */}
                                <div>
                                  <h4 className="text-white font-bold mb-4 text-lg md:text-xl flex items-center">
                                    <span className="w-2 h-2 rounded-full mr-3" style={{ backgroundColor: info.color }}></span>
                                    Key Capabilities
                                  </h4>
                                  <div className="space-y-4">
                                    {info.details.map((detail: string, index: number) => (
                                      <div key={index} className="flex items-start space-x-3">
                                        <div 
                                          className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                                          style={{ backgroundColor: info.color + '30' }}
                                        >
                                          <span className="text-white text-xs font-bold">{index + 1}</span>
                                        </div>
                                        <p className="text-gray-200 leading-relaxed text-sm md:text-base">{detail}</p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                                
                                {/* AgentCore Integration */}
                                <div>
                                  <h4 className="text-white font-bold mb-4 text-lg md:text-xl flex items-center">
                                    <span className="w-2 h-2 rounded-full mr-3" style={{ backgroundColor: info.color }}></span>
                                    AgentCore Integration
                                  </h4>
                                  <div 
                                    className="p-5 md:p-6 rounded-2xl border-2 shadow-lg"
                                    style={{ 
                                      backgroundColor: info.color + '15',
                                      borderColor: info.color + '50',
                                      boxShadow: `0 4px 20px ${info.color}20`
                                    }}
                                  >
                                    <p className="text-gray-100 leading-relaxed text-sm md:text-base">
                                      {info.agentCoreRole}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Close button - Desktop */}
                            <div className="hidden md:flex justify-end">
                              <AnimatedButton
                                onClick={() => setSelectedComponent(null)}
                                variant="secondary"
                                size="sm"
                              >
                                Close
                              </AnimatedButton>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>


          </GlassCard>
        </motion.div>

        {/* Navigation Button */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="flex justify-center"
        >
          <AnimatedButton
            onClick={handleViewResults}
            variant="accent"
            size="lg"
            glow={true}
            className="text-xl px-8 py-4"
          >
            📈 View Results
          </AnimatedButton>
        </motion.div>
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