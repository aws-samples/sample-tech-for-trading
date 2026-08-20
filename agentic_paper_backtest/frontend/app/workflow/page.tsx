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
        description: "Here is where you are. Next.js app where the quant strategist uploads a research paper and sets the target stock and backtest window.",
        details: [],
        agentCoreRole: ""
      },
      identity: {
        title: "Identity (Authn & Authz)",
        icon: "🔐",
        color: "#38bdf8",
        description: "Authenticates users before any request reaches the orchestrator, and authorizes agent-to-tool calls across the system.",
        details: [
          "User login with username/password (Cognito user pool)",
          "JWT access token verified on every page and API request",
          "OAuth client_credentials flow secures Gateway tool calls"
        ],
        agentCoreRole: "AgentCore Identity provides authentication and authorization for agents and tools, integrating with Cognito as the identity provider."
      },
      orchestrator: {
        title: "Orchestrator Agent (Quant Research Agent)",
        icon: "🤖",
        color: "#00d4ff",
        description: "The central coordinator: parses the uploaded research paper PDF, extracts the trading idea, then drives the 4-step workflow — strategy generation, market data, backtest, summary.",
        details: [
          "Extracts the paper's trading idea into a testable strategy config",
          "Coordinates specialized agents and tools in strict order",
          "Backed by its own Amazon Bedrock model (model 1)"
        ],
        agentCoreRole: "Powered by AgentCore Runtime - serverless, scalable agent execution with dedicated microVM isolation for security."
      },
      policy: {
        title: "Policy (Quant Allowlist)",
        icon: "🛡️",
        color: "#f59e0b",
        description: "Policy engine that governs which tools the orchestrator may call — a quant allowlist evaluated before Gateway tool invocations.",
        details: [
          "Allowlist-based control over tool access",
          "Evaluated at the Gateway boundary before execution",
          "Least-privilege guardrail for agent behavior"
        ],
        agentCoreRole: "AgentCore Policy enforces fine-grained authorization policies on agent tool calls, keeping the orchestrator within approved boundaries."
      },
      gateway: {
        title: "Market Data Tool",
        icon: "📊",
        color: "#10b981",
        description: "Fetches historical market data from an S3 Table via a Lambda function, exposed through AgentCore Gateway.",
        details: [
          "Historical OHLCV daily data stored in S3 Tables",
          "Lambda function as the Gateway target",
          "Cognito client_credentials authentication"
        ],
        agentCoreRole: "AgentCore Gateway transforms the Lambda-backed data API into an MCP-compatible tool, eliminating integration complexity."
      },
      strategy_agent: {
        title: "Strategy Generation Agent",
        icon: "⚙️",
        color: "#00d4ff",
        description: "Converts the extracted trading idea into executable Python code for the Backtrader framework (Agent-as-Tool pattern).",
        details: [
          "Interprets buy/sell conditions extracted from the paper",
          "Generates Backtrader strategy code",
          "Runs on its own Bedrock model (model 2)"
        ],
        agentCoreRole: "A second agent on AgentCore Runtime, invoked as a tool by the orchestrator — demonstrating multi-agent coordination."
      },
      backtest_tool: {
        title: "Run Backtest Tool",
        icon: "🔬",
        color: "#f59e0b",
        description: "Executes the generated Backtrader Python code against the market data in an isolated sandbox.",
        details: [
          "Runs untrusted generated code safely in a sandbox",
          "Backtrader engine with configurable cash/commission",
          "Returns trades, returns, Sharpe, drawdown metrics"
        ],
        agentCoreRole: "AgentCore Code Interpreter provides a secure, isolated sandbox to execute the generated strategy code — no local exec()."
      },
      summary_agent: {
        title: "Result Summary Agent",
        icon: "📈",
        color: "#00d4ff",
        description: "Analyzes backtest results and generates the final report with recommendations (Agent-as-Tool pattern).",
        details: [
          "Processes raw backtest data into an executive summary",
          "Provides actionable recommendations",
          "Runs on a lightweight Bedrock model (Nova Lite)"
        ],
        agentCoreRole: "Final agent in the orchestration, running on AgentCore Runtime to provide intelligent analysis of results."
      },
      memory: {
        title: "AgentCore Memory",
        icon: "💾",
        color: "#ec4899",
        description: "Persistent knowledge storage that maintains backtest results across sessions.",
        details: [
          "Stores backtest results (trades, metrics, strategy code)",
          "Powers the chat assistant's historical analysis",
          "Short-term and long-term memory features"
        ],
        agentCoreRole: "AgentCore Memory provides both short and long memory features."
      },
      observability: {
        title: "Observability",
        icon: "🔭",
        color: "#f43f5e",
        description: "End-to-end tracing of every agent invocation: each tool call, model call, and latency is captured as OTEL spans.",
        details: [
          "OTEL spans emitted to CloudWatch Transaction Search",
          "GenAI Observability dashboard for traces and logs",
          "Session-level visibility across the multi-agent workflow"
        ],
        agentCoreRole: "AgentCore Observability instruments the runtime automatically (ADOT), giving full-fidelity traces without code changes."
      },
      evaluations: {
        title: "Evaluations",
        icon: "🧪",
        color: "#a78bfa",
        description: "LLM-as-a-judge evaluation of real agent sessions: builtin evaluators plus custom ones for this workflow.",
        details: [
          "Builtin: GoalSuccessRate, Helpfulness, ToolSelectionAccuracy",
          "Custom: workflow completeness, metrics faithfulness, paper extraction fidelity",
          "Runs on demand per session or continuously on live traffic"
        ],
        agentCoreRole: "AgentCore Evaluations judges agent quality from Observability traces — see the eval/ directory in this repo."
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
            🏗️ Multi-Agent Architecture by Strands and AgentCore
          </h1>
          <p className="text-xl text-gray-300">
            Explore the intelligent orchestrator architecture powering your research paper backtesting
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

            {/* Interactive SVG Diagram */}
            <div className="relative w-full max-w-7xl mx-auto overflow-x-auto">
              <svg viewBox="0 0 1400 950" className="w-full h-auto min-h-[500px] lg:min-h-[620px]">
                {/* Background */}
                <rect width="1400" height="950" fill="transparent" />

                {/* Client */}
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <rect x="30" y="400" width="140" height="90" rx="10"
                        fill="#1f2937" stroke="#6b7280" strokeWidth="2"
                        className="cursor-pointer hover:stroke-accent-blue transition-colors"
                        onClick={() => setSelectedComponent('client')}
                  />
                  <text x="100" y="440" textAnchor="middle" fill="#e5e7eb" fontSize="16" fontWeight="bold">
                    Client
                  </text>
                  <text x="100" y="465" textAnchor="middle" fill="#9ca3af" fontSize="14">
                    Frontend
                  </text>
                </motion.g>

                {/* AgentCore Identity (on the client -> orchestrator path) */}
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  <rect x="210" y="390" width="180" height="110" rx="12"
                        fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="300" y="410" textAnchor="middle" fill="#38bdf8" fontSize="12" fontWeight="bold">
                    AgentCore Identity
                  </text>
                  <rect x="225" y="420" width="150" height="65" rx="8"
                        fill="#38bdf820" stroke="#38bdf8" strokeWidth="2"
                        className="cursor-pointer hover:fill-sky-400/30 transition-colors"
                        onClick={() => setSelectedComponent('identity')}
                  />
                  <text x="300" y="448" textAnchor="middle" fill="#38bdf8" fontSize="14" fontWeight="bold">
                    🔐 Authn &amp; Authz
                  </text>
                  <text x="300" y="470" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Cognito + JWT
                  </text>
                </motion.g>

                {/* Orchestrator Agent (Central) */}
                <motion.g
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  <rect x="440" y="360" width="280" height="180" rx="20"
                        fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="580" y="382" textAnchor="middle" fill="#8b5cf6" fontSize="14" fontWeight="bold">
                    AgentCore Runtime
                  </text>

                  <rect x="470" y="400" width="220" height="110" rx="15"
                        fill="#00d4ff20" stroke="#00d4ff" strokeWidth="3"
                        className="cursor-pointer hover:fill-accent-blue/30 transition-colors"
                        onClick={() => setSelectedComponent('orchestrator')}
                  />
                  <text x="580" y="448" textAnchor="middle" fill="#00d4ff" fontSize="17" fontWeight="bold">
                    🤖 Orchestrator Agent
                  </text>
                  <text x="580" y="475" textAnchor="middle" fill="#9ca3af" fontSize="12">
                    Paper parsing + 4-step workflow
                  </text>
                </motion.g>

                {/* AgentCore Policy (in front of Gateway) */}
                <motion.g
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <rect x="770" y="95" width="150" height="80" rx="10"
                        fill="#f59e0b20" stroke="#f59e0b" strokeWidth="2"
                        className="cursor-pointer hover:fill-yellow-500/30 transition-colors"
                        onClick={() => setSelectedComponent('policy')}
                  />
                  <text x="845" y="128" textAnchor="middle" fill="#f59e0b" fontSize="14" fontWeight="bold">
                    🛡️ Policy
                  </text>
                  <text x="845" y="150" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Quant Allowlist
                  </text>
                </motion.g>

                {/* Market Data Tool (Gateway) */}
                <motion.g
                  initial={{ opacity: 0, x: -50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <rect x="960" y="70" width="310" height="140" rx="15"
                        fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="1115" y="92" textAnchor="middle" fill="#10b981" fontSize="12" fontWeight="bold">
                    AgentCore Gateway
                  </text>

                  <rect x="985" y="105" width="260" height="80" rx="10"
                        fill="#10b98120" stroke="#10b981" strokeWidth="2"
                        className="cursor-pointer hover:fill-accent-green/30 transition-colors"
                        onClick={() => setSelectedComponent('gateway')}
                  />
                  <text x="1115" y="140" textAnchor="middle" fill="#10b981" fontSize="15" fontWeight="bold">
                    📊 Market Data Tool
                  </text>
                  <text x="1115" y="165" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Lambda → S3 Table
                  </text>
                </motion.g>

                {/* Strategy Generation Agent */}
                <motion.g
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 }}
                >
                  <rect x="960" y="260" width="310" height="140" rx="15"
                        fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="1115" y="282" textAnchor="middle" fill="#8b5cf6" fontSize="12" fontWeight="bold">
                    AgentCore Runtime
                  </text>

                  <rect x="985" y="295" width="260" height="80" rx="10"
                        fill="#00d4ff20" stroke="#00d4ff" strokeWidth="2"
                        className="cursor-pointer hover:fill-accent-blue/30 transition-colors"
                        onClick={() => setSelectedComponent('strategy_agent')}
                  />
                  <text x="1115" y="330" textAnchor="middle" fill="#00d4ff" fontSize="15" fontWeight="bold">
                    ⚙️ Strategy Agent
                  </text>
                  <text x="1115" y="355" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Agent as Tool
                  </text>
                </motion.g>

                {/* Backtest Tool (Code Interpreter) */}
                <motion.g
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 }}
                >
                  <rect x="960" y="450" width="310" height="130" rx="15"
                        fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="1115" y="472" textAnchor="middle" fill="#f59e0b" fontSize="12" fontWeight="bold">
                    AgentCore Code Interpreter
                  </text>

                  <rect x="985" y="485" width="260" height="75" rx="10"
                        fill="#f59e0b20" stroke="#f59e0b" strokeWidth="2"
                        className="cursor-pointer hover:fill-yellow-500/30 transition-colors"
                        onClick={() => setSelectedComponent('backtest_tool')}
                  />
                  <text x="1115" y="518" textAnchor="middle" fill="#f59e0b" fontSize="15" fontWeight="bold">
                    🔬 Backtest Tool
                  </text>
                  <text x="1115" y="542" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Backtrader in sandbox
                  </text>
                </motion.g>

                {/* Result Summary Agent */}
                <motion.g
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 }}
                >
                  <rect x="960" y="630" width="310" height="140" rx="15"
                        fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="1115" y="652" textAnchor="middle" fill="#8b5cf6" fontSize="12" fontWeight="bold">
                    AgentCore Runtime
                  </text>

                  <rect x="985" y="665" width="260" height="80" rx="10"
                        fill="#00d4ff20" stroke="#00d4ff" strokeWidth="2"
                        className="cursor-pointer hover:fill-accent-blue/30 transition-colors"
                        onClick={() => setSelectedComponent('summary_agent')}
                  />
                  <text x="1115" y="700" textAnchor="middle" fill="#00d4ff" fontSize="15" fontWeight="bold">
                    📈 Summary Agent
                  </text>
                  <text x="1115" y="725" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Agent as Tool
                  </text>
                </motion.g>

                {/* AgentCore Memory */}
                <motion.g
                  initial={{ opacity: 0, y: 50 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.9 }}
                >
                  <rect x="60" y="640" width="250" height="150" rx="15"
                        fill="none" stroke="#ec4899" strokeWidth="2" strokeDasharray="6,6"
                  />
                  <text x="185" y="662" textAnchor="middle" fill="#ec4899" fontSize="12" fontWeight="bold">
                    AgentCore Memory
                  </text>

                  <rect x="85" y="678" width="200" height="80" rx="10"
                        fill="#ec489920" stroke="#ec4899" strokeWidth="2"
                        className="cursor-pointer hover:fill-pink-500/30 transition-colors"
                        onClick={() => setSelectedComponent('memory')}
                  />
                  <text x="185" y="712" textAnchor="middle" fill="#ec4899" fontSize="15" fontWeight="bold">
                    💾 Memory Storage
                  </text>
                  <text x="185" y="737" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    Backtest Results
                  </text>
                </motion.g>

                {/* AgentCore Observability */}
                <motion.g
                  initial={{ opacity: 0, y: 50 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.0 }}
                >
                  <rect x="400" y="660" width="180" height="110" rx="12"
                        fill="#f43f5e15" stroke="#f43f5e" strokeWidth="2" strokeDasharray="6,6"
                        className="cursor-pointer hover:fill-rose-500/20 transition-colors"
                        onClick={() => setSelectedComponent('observability')}
                  />
                  <text x="490" y="705" textAnchor="middle" fill="#f43f5e" fontSize="15" fontWeight="bold">
                    🔭 Observability
                  </text>
                  <text x="490" y="730" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    OTEL traces
                  </text>
                </motion.g>

                {/* AgentCore Evaluations */}
                <motion.g
                  initial={{ opacity: 0, y: 50 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.1 }}
                >
                  <rect x="620" y="660" width="180" height="110" rx="12"
                        fill="#a78bfa15" stroke="#a78bfa" strokeWidth="2" strokeDasharray="6,6"
                        className="cursor-pointer hover:fill-violet-400/20 transition-colors"
                        onClick={() => setSelectedComponent('evaluations')}
                  />
                  <text x="710" y="705" textAnchor="middle" fill="#a78bfa" fontSize="15" fontWeight="bold">
                    🧪 Evaluations
                  </text>
                  <text x="710" y="730" textAnchor="middle" fill="#9ca3af" fontSize="11">
                    LLM-as-a-judge
                  </text>
                </motion.g>

                {/* Connection Lines */}
                <g stroke="#6b7280" strokeWidth="2" fill="none" strokeDasharray="5,5">
                  {/* Client -> Identity -> Orchestrator */}
                  <line x1="170" y1="445" x2="210" y2="445" />
                  <line x1="390" y1="445" x2="440" y2="450" />

                  {/* Orchestrator -> Policy -> Gateway */}
                  <line x1="720" y1="400" x2="770" y2="150" />
                  <line x1="920" y1="135" x2="960" y2="135" />

                  {/* Orchestrator -> Strategy Agent */}
                  <line x1="720" y1="430" x2="960" y2="330" />

                  {/* Orchestrator -> Code Interpreter */}
                  <line x1="720" y1="470" x2="960" y2="515" />

                  {/* Orchestrator -> Summary Agent */}
                  <line x1="720" y1="500" x2="960" y2="695" />

                  {/* Orchestrator -> Memory */}
                  <line x1="480" y1="540" x2="310" y2="690" />

                  {/* Runtime -> Observability -> Evaluations (trace flow) */}
                  <line x1="545" y1="540" x2="500" y2="660" />
                  <line x1="580" y1="715" x2="620" y2="715" />
                </g>

                {/* Data Flow Animation */}
                {selectedComponent && (
                  <motion.circle r="4" fill="#00d4ff" opacity="0.8">
                    <animateMotion dur="3s" repeatCount="indefinite">
                      <path d="M170,445 Q300,445 440,450 Q700,430 960,330" />
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
