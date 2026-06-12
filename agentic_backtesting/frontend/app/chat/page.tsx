'use client';

import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import AnimatedButton from '@/components/ui/AnimatedButton';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    const prompt = input.trim();
    if (!prompt || isLoading) return;

    const userMessage: Message = { role: 'user', content: prompt, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH || ''}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.success ? data.message : `Error: ${data.error}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Connection error: ${error.message}`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const suggestedQuestions = [
    'Show me all my backtest results',
    'Which strategy had the best Sharpe ratio?',
    'How can I improve my last strategy?',
    'Compare my EMA strategies by max drawdown',
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex flex-col">
      {/* Header */}
      <motion.div
        className="px-6 py-6 border-b border-white/5"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="container mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent">
              Quant Research Chat
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Analyze historical backtests and get strategy improvement suggestions
            </p>
          </div>
          <a
            href="/"
            className="text-gray-400 hover:text-white transition-colors text-sm border border-gray-600 rounded-lg px-4 py-2"
          >
            Back to Backtester
          </a>
        </div>
      </motion.div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="container mx-auto max-w-4xl space-y-4">
          {messages.length === 0 && (
            <motion.div
              className="text-center py-16"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <p className="text-gray-400 text-lg mb-6">
                Ask questions about your backtest history
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(q); }}
                    className="text-left text-sm text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg px-4 py-3 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <GlassCard
                className={`p-4 max-w-[80%] ${
                  msg.role === 'user'
                    ? 'bg-accent-blue/10 border-accent-blue/20'
                    : 'bg-white/5 border-white/10'
                }`}
              >
                <div className="text-xs text-gray-500 mb-1">
                  {msg.role === 'user' ? 'You' : 'Quant Assistant'}
                </div>
                <div className="text-gray-200 text-sm whitespace-pre-wrap">
                  {msg.content}
                </div>
              </GlassCard>
            </motion.div>
          ))}

          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <GlassCard className="p-4 bg-white/5 border-white/10">
                <div className="text-xs text-gray-500 mb-1">Quant Assistant</div>
                <div className="flex items-center space-x-2 text-gray-400">
                  <div className="animate-pulse">Analyzing backtest history...</div>
                </div>
              </GlassCard>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-white/5 px-6 py-4">
        <div className="container mx-auto max-w-4xl">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your backtest results, strategy performance, or improvements..."
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-accent-blue/50 transition-colors"
              rows={2}
              disabled={isLoading}
            />
            <AnimatedButton
              onClick={sendMessage}
              variant="accent"
              disabled={!input.trim() || isLoading}
              loading={isLoading}
              className="self-end px-6"
            >
              Send
            </AnimatedButton>
          </div>
          <p className="text-xs text-gray-600 mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}
