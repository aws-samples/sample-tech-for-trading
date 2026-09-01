'use client';

import React, { forwardRef } from 'react';
import clsx from 'clsx';

interface GlassInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
  glow?: boolean;
}

const GlassInput = forwardRef<HTMLInputElement, GlassInputProps>(
  ({ label, error, icon, glow = false, className = '', ...props }, ref) => {
    const inputClasses = clsx(
      'glass-input w-full',
      {
        'border-red-400 glow-red': error,
        'animate-glow-pulse': glow,
        'pl-12': icon
      },
      className
    );

    return (
      <div className="space-y-2">
        {label && (
          <label className="block text-sm font-medium text-gray-200 text-left">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            className={inputClasses}
            {...props}
          />
        </div>
        {error && (
          <p className="text-sm text-red-400 animate-fade-in">
            {error}
          </p>
        )}
      </div>
    );
  }
);

GlassInput.displayName = 'GlassInput';

export default GlassInput;
