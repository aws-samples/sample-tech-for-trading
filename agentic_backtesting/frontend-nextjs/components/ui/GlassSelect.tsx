'use client';

import React, { useState } from 'react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

interface Option {
  value: string;
  label: string;
  description?: string;
}

interface GlassSelectProps {
  options: Option[];
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  className?: string;
}

const GlassSelect: React.FC<GlassSelectProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  label,
  error,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(option => option.value === value);

  const selectClasses = clsx(
    'glass-input cursor-pointer flex items-center justify-between',
    {
      'border-red-400': error,
    },
    className
  );

  return (
    <div className="relative space-y-2">
      {label && (
        <label className="block text-sm font-medium text-gray-200 text-left">
          {label}
        </label>
      )}
      
      <div
        className={selectClasses}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className={selectedOption ? 'text-white' : 'text-gray-400'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <motion.svg
          className="w-5 h-5 text-gray-400"
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </motion.svg>
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="absolute top-full left-0 right-0 z-50 mt-1 glass-card max-h-60 overflow-auto"
          >
            {options.map((option) => (
              <motion.div
                key={option.value}
                className="p-3 cursor-pointer hover:bg-white/10 transition-colors duration-200 first:rounded-t-2xl last:rounded-b-2xl"
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
                whileHover={{ x: 4 }}
              >
                <div className="text-white font-medium">{option.label}</div>
                {option.description && (
                  <div className="text-gray-400 text-sm mt-1">{option.description}</div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <p className="text-sm text-red-400 animate-fade-in">
          {error}
        </p>
      )}

      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default GlassSelect;
