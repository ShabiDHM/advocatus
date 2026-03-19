// src/drafting/components/ThinkingDots.tsx
import React from 'react';
import { motion } from 'framer-motion';

export const ThinkingDots: React.FC = () => (
  <span className="inline-flex items-center ml-1 text-primary-start">
    {[0, 0.2, 0.4].map((delay, i) => (
      <motion.span
        key={i}
        animate={{ opacity: [0.3, 1, 0.3] }}
        transition={{ duration: 1.2, repeat: Infinity, delay }}
        className="w-1 h-1 bg-current rounded-full mx-0.5"
      />
    ))}
  </span>
);