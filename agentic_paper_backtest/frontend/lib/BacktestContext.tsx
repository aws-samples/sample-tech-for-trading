'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import { AgentOutput } from '@/types/strategy';

interface BacktestContextType {
  result: AgentOutput | null;
  setResult: (result: AgentOutput | null) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

const BacktestContext = createContext<BacktestContextType | undefined>(undefined);

export function BacktestProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<AgentOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <BacktestContext.Provider value={{ result, setResult, error, setError }}>
      {children}
    </BacktestContext.Provider>
  );
}

export function useBacktest() {
  const context = useContext(BacktestContext);
  if (context === undefined) {
    throw new Error('useBacktest must be used within a BacktestProvider');
  }
  return context;
}
