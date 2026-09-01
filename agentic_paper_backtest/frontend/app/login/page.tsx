'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import GlassCard from '@/components/ui/GlassCard';
import GlassInput from '@/components/ui/GlassInput';
import AnimatedButton from '@/components/ui/AnimatedButton';

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!username || !password) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${BASE_PATH}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        router.push('/');
        router.refresh();
      } else {
        const data = await response.json().catch(() => ({}));
        setError(data.error || 'Login failed');
        setIsSubmitting(false);
      }
    } catch {
      setError('Network error. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-tertiary flex items-center justify-center px-6">
      <motion.div
        className="w-full max-w-md"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent mb-2">
            📄 Paper Backtester
          </h1>
          <p className="text-gray-400">Sign in to continue</p>
        </div>

        <GlassCard className="p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <GlassInput
              label="👤 Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
            />
            <GlassInput
              label="🔒 Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
            />

            {error && (
              <p className="text-red-400 text-sm">• {error}</p>
            )}

            <AnimatedButton
              onClick={handleSubmit}
              variant="accent"
              size="lg"
              disabled={!username || !password || isSubmitting}
              loading={isSubmitting}
              glow={!!username && !!password}
              className="w-full py-3"
            >
              {isSubmitting ? 'Signing in...' : 'Sign In'}
            </AnimatedButton>
          </form>
        </GlassCard>
      </motion.div>
    </div>
  );
}
