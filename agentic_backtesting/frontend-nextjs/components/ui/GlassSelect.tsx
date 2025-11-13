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
    <div className="relative space-y-2" style={{ zIndex: isOpen ? 1000 : 'auto' }}>
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
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-[999]"
              onClick={() => setIsOpen(false)}
            />
            
            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full left-0 right-0 z-[1000] mt-2 max-h-60 overflow-auto shadow-2xl border border-white/20 rounded-2xl"
              style={{
                backdropFilter: 'blur(20px)',
                background: 'rgba(26, 26, 26, 0.95)'
              }}
            >
              {options.map((option, index) => (
                <motion.div
                  key={option.value}
                  className={`p-4 cursor-pointer hover:bg-white/10 transition-all duration-200 border-b border-white/5 last:border-b-0 ${
                    index === 0 ? 'rounded-t-2xl' : ''
                  } ${
                    index === options.length - 1 ? 'rounded-b-2xl' : ''
                  }`}
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  whileHover={{ x: 2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="text-white font-medium">{option.label}</div>
                  {option.description && (
                    <div className="text-gray-400 text-sm mt-1">{option.description}</div>
                  )}
                </motion.div>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {error && (
        <p className="text-sm text-red-400 animate-fade-in mt-2">
          {error}
        </p>
      )}
    </div>
  );
};

export default GlassSelect;
