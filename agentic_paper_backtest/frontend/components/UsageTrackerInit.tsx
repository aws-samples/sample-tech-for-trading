'use client';

import { useEffect } from 'react';

declare global {
  interface Window {
    UsageTrackerAuto?: new (options?: Record<string, unknown>) => unknown;
    __usageTracker?: unknown;
  }
}

export default function UsageTrackerInit() {
  useEffect(() => {
    if (window.__usageTracker) return;

    let attempts = 0;
    const maxAttempts = 50; // ~5s total

    const tryInit = () => {
      if (typeof window.UsageTrackerAuto === 'function') {
        try {
          window.__usageTracker = new window.UsageTrackerAuto();
        } catch (err) {
          console.error('[UsageTracker] init failed:', err);
        }
        return;
      }
      if (++attempts < maxAttempts) {
        setTimeout(tryInit, 100);
      } else {
        console.warn('[UsageTracker] script did not load within 5s');
      }
    };

    tryInit();
  }, []);

  return null;
}
