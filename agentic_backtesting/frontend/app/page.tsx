'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import GlassInput from '@/components/ui/GlassInput';
import GlassSelect from '@/components/ui/GlassSelect';
import AnimatedButton from '@/components/ui/AnimatedButton';
import { AVAILABLE_STOCKS, ValidationResult } from '@/types/strategy';

export default function StrategyBuilder() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: 'My Trading Strategy',
    stock_symbol: 'AMZN',
    backtest_window: '1Y',
    max_positions: 1,
    stop_loss: 5,
    take_profit: 10,
    buy_conditions: '10 SMA crosses above 30 SMA',
    sell_conditions: '10 SMA crosses below 30 SMA'
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validation, setValidation] = useState<ValidationResult>({
    isValid: true,
    errors: []
  });

  const stockOptions = AVAILABLE_STOCKS.map(stock => ({
    value: stock.symbol,
    label: `${stock.symbol} - ${stock.name}`,
    disabled: stock.symbol !== 'AMZN' // Only AMZN has data available
  }));

  const windowOptions = [
    { value: '1M', label: '1 Month' },
    { value: '3M', label: '3 Months' },
    { value: '6M', label: '6 Months' },
    { value: '1Y', label: '1 Year' },
    { value: '2Y', label: '2 Years' }
  ];

  const handleInputChange = (field: keyof typeof formData, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    validateForm({ ...formData, [field]: value });
  };

  const validateForm = (data: typeof formData = formData): ValidationResult => {
    const errors: string[] = [];

    if (!data.name?.trim()) errors.push('Strategy name is required');
    if (!data.stock_symbol) errors.push('Please select a stock');
    if (!data.buy_conditions?.trim()) errors.push('Buy conditions are required');
    if (!data.sell_conditions?.trim()) errors.push('Sell conditions are required');
    if (data.max_positions < 1) errors.push('Max positions must be at least 1');
    if (data.stop_loss < 0 || data.stop_loss > 100) errors.push('Stop loss must be between 0 and 100');
    if (data.take_profit < 0 || data.take_profit > 100) errors.push('Take profit must be between 0 and 100');

    const result = { isValid: errors.length === 0, errors };
    setValidation(result);
    return result;
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!validateForm().isValid) return;

    setIsSubmitting(true);

    try {
      // Start the backtest job
      const response = await fetch('/api/execute-backtest-async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const { jobId } = await response.json();
      console.log('[StrategyBuilder] ✅ Job started, ID:', jobId);
      
      // Navigate to workflow page with strategy and jobId
      router.push(`/workflow?strategy=${encodeURIComponent(JSON.stringify(formData))}&jobId=${jobId}`);
      
    } catch (error) {
      console.error('[StrategyBuilder] ❌ Error:', error);
      alert('Failed to start backtest. Please try again.');
      setIsSubmitting(false);
    }
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
            🎯 Trading Strategy Backtesting
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl">
            Multi-agent trading strategy backtesting with Strands agent and Amazon Bedrock AgentCore
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Form */}
          <motion.div
            className="lg:col-span-2"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <GlassCard className="p-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Row 1: Stock Selection & Backtest Window */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <GlassSelect
                    label="📈 Stock Symbol"
                    options={stockOptions}
                    value={formData.stock_symbol}
                    onChange={(value) => handleInputChange('stock_symbol', value)}
                  />

                  <GlassSelect
                    label="📅 Backtest Window"
                    options={windowOptions}
                    value={formData.backtest_window}
                    onChange={(value) => handleInputChange('backtest_window', value)}
                  />
                </div>

                {/* Row 2: Max Positions & Stop Loss */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <GlassInput
                    label="🔢 Max Positions"
                    type="number"
                    min={1}
                    max={10}
                    value={formData.max_positions}
                    onChange={(e) => handleInputChange('max_positions', parseInt(e.target.value) || 1)}
                  />

                  <GlassInput
                    label="🛑 Stop Loss (%)"
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={formData.stop_loss}
                    onChange={(e) => handleInputChange('stop_loss', parseFloat(e.target.value) || 0)}
                  />
                </div>

                {/* Row 3: Take Profit & Strategy Name */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <GlassInput
                    label="💰 Take Profit (%)"
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={formData.take_profit}
                    onChange={(e) => handleInputChange('take_profit', parseFloat(e.target.value) || 0)}
                  />

                  <GlassInput
                    label="📝 Strategy Name"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="e.g., EMA Crossover Strategy"
                    error={validation.errors.find(e => e.includes('name'))}
                  />
                </div>

                {/* Row 4: Buy Conditions & Sell Conditions */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <GlassInput
                    label="📈 Buy Conditions"
                    value={formData.buy_conditions}
                    onChange={(e) => handleInputChange('buy_conditions', e.target.value)}
                    placeholder="e.g., Price above 20-day moving average and RSI below 70"
                    error={validation.errors.find(e => e.includes('Buy'))}
                  />

                  <GlassInput
                    label="📉 Sell Conditions"
                    value={formData.sell_conditions}
                    onChange={(e) => handleInputChange('sell_conditions', e.target.value)}
                    placeholder="e.g., Price below 20-day moving average or RSI above 80"
                    error={validation.errors.find(e => e.includes('Sell'))}
                  />
                </div>

                {/* Submit Button */}
                <div className="pt-6">
                  <AnimatedButton
                    onClick={handleSubmit}
                    variant="accent"
                    size="lg"
                    disabled={!validation.isValid || isSubmitting}
                    loading={isSubmitting}
                    glow={validation.isValid}
                    className="w-full text-xl py-4"
                  >
                    {isSubmitting ? 'Starting Backtest...' : '🚀 Run Backtest'}
                  </AnimatedButton>
                </div>
              </form>
            </GlassCard>
          </motion.div>

          {/* Preview Sidebar */}
          <motion.div
            className="space-y-6"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            {/* Strategy Preview */}
            <GlassCard className="p-6">
              <h3 className="text-xl font-semibold text-white mb-4">📋 Strategy Preview</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Name:</span>
                  <span className="text-white font-medium">{formData.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Stock:</span>
                  <span className="text-white font-medium">{formData.stock_symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Window:</span>
                  <span className="text-white font-medium">{formData.backtest_window}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Max Positions:</span>
                  <span className="text-white font-medium">{formData.max_positions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Stop Loss:</span>
                  <span className="text-red-400 font-medium">{formData.stop_loss}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Take Profit:</span>
                  <span className="text-accent-green font-medium">{formData.take_profit}%</span>
                </div>
                <div className="border-t border-gray-600 pt-3 mt-3">
                  <div className="mb-2">
                    <span className="text-gray-400">Buy:</span>
                    <p className="text-white text-xs mt-1">{formData.buy_conditions}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Sell:</span>
                    <p className="text-white text-xs mt-1">{formData.sell_conditions}</p>
                  </div>
                </div>
              </div>
            </GlassCard>

            {/* Validation Status */}
            <GlassCard className={`p-6 ${validation.isValid ? 'border-accent-green/30' : 'border-red-400/30'}`}>
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${validation.isValid ? 'bg-accent-green' : 'bg-red-400'}`} />
                <span className={`font-medium ${validation.isValid ? 'text-accent-green' : 'text-red-400'}`}>
                  {validation.isValid ? 'Strategy Ready' : 'Please Fix Errors'}
                </span>
              </div>
              {validation.errors.length > 0 && (
                <div className="mt-3 space-y-1">
                  {validation.errors.map((error, index) => (
                    <p key={index} className="text-red-400 text-sm">• {error}</p>
                  ))}
                </div>
              )}
            </GlassCard>
          </motion.div>
        </div>
      </div>
    </div>
  );
}