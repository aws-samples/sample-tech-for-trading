'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import GlassInput from '@/components/ui/GlassInput';
import GlassSelect from '@/components/ui/GlassSelect';
import AnimatedButton from '@/components/ui/AnimatedButton';
import { AVAILABLE_STOCKS, ValidationResult } from '@/types/strategy';
import { FRONTEND_VERSION } from '@/lib/version';

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '';
const MAX_PDF_MB = 10;

type InputMode = 'pdf' | 'manual';

export default function PaperBacktestBuilder() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<InputMode>('pdf');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    stock_symbol: 'AMZN',
    backtest_window: '5Y',
    max_positions: 1000,
    stop_loss: 10,
    take_profit: 30,
    // manual mode fields
    name: 'My Trading Strategy',
    buy_conditions: '10 SMA crosses above 30 SMA',
    sell_conditions: '10 SMA crosses below 30 SMA',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validation, setValidation] = useState<ValidationResult>({
    isValid: false,
    errors: ['Please upload a research paper PDF']
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
    { value: '2Y', label: '2 Years' },
    { value: '5Y', label: '5 Years' },
    { value: '10Y', label: '10 Years' },
    { value: '20Y', label: '20 Years' }
  ];

  const validateForm = (data: typeof formData, file: File | null, m: InputMode): ValidationResult => {
    const errors: string[] = [];

    if (m === 'pdf') {
      if (!file) errors.push('Please upload a research paper PDF');
      if (file && file.type !== 'application/pdf') errors.push('File must be a PDF');
      if (file && file.size > MAX_PDF_MB * 1024 * 1024) errors.push(`PDF must be under ${MAX_PDF_MB}MB`);
    } else {
      if (!data.name?.trim()) errors.push('Strategy name is required');
      if (!data.buy_conditions?.trim()) errors.push('Buy conditions are required');
      if (!data.sell_conditions?.trim()) errors.push('Sell conditions are required');
    }
    if (!data.stock_symbol) errors.push('Please select a stock');
    if (data.max_positions < 1) errors.push('Max positions must be at least 1');
    if (data.stop_loss < 0 || data.stop_loss > 100) errors.push('Stop loss must be between 0 and 100');
    if (data.take_profit < 0 || data.take_profit > 100) errors.push('Take profit must be between 0 and 100');

    const result = { isValid: errors.length === 0, errors };
    setValidation(result);
    return result;
  };

  const handleModeChange = (m: InputMode) => {
    setMode(m);
    validateForm(formData, pdfFile, m);
  };

  const handleInputChange = (field: keyof typeof formData, value: string | number) => {
    const next = { ...formData, [field]: value };
    setFormData(next);
    validateForm(next, pdfFile, mode);
  };

  const handleFileChange = (file: File | null) => {
    setPdfFile(file);
    validateForm(formData, file, mode);
  };

  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        resolve(dataUrl.split(',')[1]); // strip "data:application/pdf;base64,"
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!validateForm(formData, pdfFile, mode).isValid) return;
    if (mode === 'pdf' && !pdfFile) return;

    setIsSubmitting(true);

    try {
      const base = {
        stock_symbol: formData.stock_symbol,
        backtest_window: formData.backtest_window,
        max_positions: formData.max_positions,
        stop_loss: formData.stop_loss,
        take_profit: formData.take_profit,
      };

      let body: any;
      let strategySummary: any;

      if (mode === 'pdf') {
        const pdfBase64 = await fileToBase64(pdfFile!);
        body = { ...base, paper_name: pdfFile!.name, pdf_base64: pdfBase64 };
        strategySummary = {
          ...base,
          name: `Paper: ${pdfFile!.name}`,
          buy_conditions: 'Extracted from research paper',
          sell_conditions: 'Extracted from research paper',
        };
      } else {
        // Manual mode: same strategy JSON shape the backend's prompt path expects
        body = {
          ...base,
          name: formData.name,
          buy_conditions: formData.buy_conditions,
          sell_conditions: formData.sell_conditions,
        };
        strategySummary = body;
      }

      const response = await fetch(`${BASE_PATH}/api/execute-backtest-async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const { jobId } = await response.json();
      console.log('[PaperBacktest] ✅ Job started, ID:', jobId);

      router.push(`/workflow?strategy=${encodeURIComponent(JSON.stringify(strategySummary))}&jobId=${jobId}`);

    } catch (error) {
      console.error('[PaperBacktest] ❌ Error:', error);
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
            📄 Research Paper Backtesting
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl">
            Upload a trading research paper (PDF) or describe your own strategy. AI agents will
            extract the trading idea, fetch market data, and backtest it — powered by Strands and
            Amazon Bedrock AgentCore.
          </p>
          <div className="mt-4">
            <a
              href={`${BASE_PATH}/chat`}
              className="inline-flex items-center text-accent-blue hover:text-accent-purple transition-colors text-sm border border-accent-blue/30 hover:border-accent-purple/30 rounded-lg px-4 py-2"
            >
              💬 Chat with Quant Assistant — Analyze past backtests &amp; get improvement suggestions
            </a>
          </div>
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
                {/* Mode Toggle */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Strategy Source
                  </label>
                  <div className="grid grid-cols-2 gap-2 p-1 bg-white/5 border border-white/10 rounded-xl">
                    <button
                      type="button"
                      onClick={() => handleModeChange('pdf')}
                      className={`py-3 px-4 rounded-lg text-sm font-medium transition-all ${
                        mode === 'pdf'
                          ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/40'
                          : 'text-gray-400 hover:text-gray-200 border border-transparent'
                      }`}
                    >
                      📄 Upload Research Paper
                    </button>
                    <button
                      type="button"
                      onClick={() => handleModeChange('manual')}
                      className={`py-3 px-4 rounded-lg text-sm font-medium transition-all ${
                        mode === 'manual'
                          ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/40'
                          : 'text-gray-400 hover:text-gray-200 border border-transparent'
                      }`}
                    >
                      ✍️ Manual Buy/Sell Conditions
                    </button>
                  </div>
                </div>

                {/* PDF Upload (pdf mode) */}
                {mode === 'pdf' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      📄 Research Paper (PDF)
                    </label>
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => {
                        e.preventDefault();
                        const file = e.dataTransfer.files?.[0];
                        if (file) handleFileChange(file);
                      }}
                      className={`cursor-pointer border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                        pdfFile
                          ? 'border-accent-green/60 bg-accent-green/5'
                          : 'border-gray-500/50 hover:border-accent-blue/60 bg-white/5'
                      }`}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="application/pdf"
                        className="hidden"
                        onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                      />
                      {pdfFile ? (
                        <div>
                          <p className="text-accent-green font-medium text-lg">✅ {pdfFile.name}</p>
                          <p className="text-gray-400 text-sm mt-1">
                            {(pdfFile.size / 1024 / 1024).toFixed(2)} MB — click to replace
                          </p>
                        </div>
                      ) : (
                        <div>
                          <p className="text-gray-200 text-lg">Drag &amp; drop your paper here, or click to browse</p>
                          <p className="text-gray-400 text-sm mt-1">Text-based PDF, up to {MAX_PDF_MB}MB</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Manual strategy inputs (manual mode) */}
                {mode === 'manual' && (
                  <div className="space-y-6">
                    <GlassInput
                      label="📝 Strategy Name"
                      value={formData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      placeholder="e.g., EMA Crossover Strategy"
                    />
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <GlassInput
                        label="📈 Buy Conditions"
                        value={formData.buy_conditions}
                        onChange={(e) => handleInputChange('buy_conditions', e.target.value)}
                        placeholder="e.g., Price above 20-day moving average and RSI below 70"
                      />
                      <GlassInput
                        label="📉 Sell Conditions"
                        value={formData.sell_conditions}
                        onChange={(e) => handleInputChange('sell_conditions', e.target.value)}
                        placeholder="e.g., Price below 20-day moving average or RSI above 80"
                      />
                    </div>
                  </div>
                )}

                {/* Row: Stock Selection & Backtest Window */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <GlassSelect
                    label="📈 Target Stock"
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

                {/* Row: Risk parameters */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <GlassInput
                    label="🔢 Max Positions"
                    type="number"
                    min={1}
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

                  <GlassInput
                    label="💰 Take Profit (%)"
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={formData.take_profit}
                    onChange={(e) => handleInputChange('take_profit', parseFloat(e.target.value) || 0)}
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
                    {isSubmitting
                      ? (mode === 'pdf' ? 'Uploading Paper & Starting Backtest...' : 'Starting Backtest...')
                      : (mode === 'pdf' ? '🚀 Extract Idea & Run Backtest' : '🚀 Run Backtest')}
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
            {/* Run Preview */}
            <GlassCard className="p-6">
              <h3 className="text-xl font-semibold text-white mb-4">📋 Run Preview</h3>
              <div className="space-y-3 text-sm">
                {mode === 'pdf' ? (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Paper:</span>
                    <span className="text-white font-medium truncate max-w-[60%]">
                      {pdfFile ? pdfFile.name : '—'}
                    </span>
                  </div>
                ) : (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Strategy:</span>
                    <span className="text-white font-medium truncate max-w-[60%]">{formData.name}</span>
                  </div>
                )}
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
                {mode === 'manual' && (
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
                )}
              </div>
            </GlassCard>

            {/* How it works */}
            <GlassCard className="p-6">
              <h3 className="text-xl font-semibold text-white mb-4">🤖 How It Works</h3>
              {mode === 'pdf' ? (
                <ol className="space-y-2 text-sm text-gray-300 list-decimal list-inside">
                  <li>PDF is parsed and the trading idea is extracted by an AI agent</li>
                  <li>The idea is converted into executable Backtrader strategy code</li>
                  <li>Historical market data is fetched via AgentCore Gateway</li>
                  <li>Backtest runs in a sandbox and results are summarized</li>
                </ol>
              ) : (
                <ol className="space-y-2 text-sm text-gray-300 list-decimal list-inside">
                  <li>Your buy/sell conditions are converted into executable Backtrader code</li>
                  <li>Historical market data is fetched via AgentCore Gateway</li>
                  <li>Backtest runs in a sandbox and results are summarized</li>
                </ol>
              )}
            </GlassCard>

            {/* Validation Status */}
            <GlassCard className={`p-6 ${validation.isValid ? 'border-accent-green/30' : 'border-red-400/30'}`}>
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${validation.isValid ? 'bg-accent-green' : 'bg-red-400'}`} />
                <span className={`font-medium ${validation.isValid ? 'text-accent-green' : 'text-red-400'}`}>
                  {validation.isValid ? 'Ready to Backtest' : 'Please Fix Errors'}
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
      <div className="mt-8 text-center text-xs text-gray-500">
        Frontend: {FRONTEND_VERSION}
      </div>
    </div>
  );
}
