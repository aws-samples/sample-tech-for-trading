'use client';

import React from 'react';
import clsx from 'clsx';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  blur?: 'light' | 'medium' | 'heavy';
  opacity?: number;
  border?: boolean;
  glow?: 'blue' | 'purple' | 'green' | 'none';
  onClick?: () => void;
  animate?: boolean;
}

const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  blur = 'medium',
  opacity,
  border = true,
  glow = 'none',
  onClick,
  animate = true
}) => {
  const blurClasses = {
    light: 'glass-light',
    medium: 'glass-medium',
    heavy: 'glass-heavy'
  };

  const glowClasses = {
    blue: 'glow-blue',
    purple: 'glow-purple',
    green: 'glow-green',
    none: ''
  };

  const cardClasses = clsx(
    'glass-card',
    blurClasses[blur],
    glowClasses[glow],
    {
      'animate-glass-in': animate,
      'cursor-pointer hover:scale-105 transition-transform duration-300': onClick,
      'border-0': !border
    },
    className
  );

  const style = opacity ? { background: `rgba(255, 255, 255, ${opacity})` } : {};

  return (
    <div className={cardClasses} style={style} onClick={onClick}>
      {children}
    </div>
  );
};

export default GlassCard;
