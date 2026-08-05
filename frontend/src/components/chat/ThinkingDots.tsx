// FILE: src/components/chat/ThinkingDots.tsx
import React from 'react';
import { motion } from 'framer-motion';

export const ThinkingDots: React.FC = () => (
  <span className="inline-flex items-center ml-2">
    <motion.span
      animate={{ opacity: [0.3, 1, 0.3] }}
      transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1] }}
      className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5"
    />
    <motion.span
      animate={{ opacity: [0.3, 1, 0.3] }}
      transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.2 }}
      className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5"
    />
    <motion.span
      animate={{ opacity: [0.3, 1, 0.3] }}
      transition={{ duration: 1.2, repeat: Infinity, times: [0, 0.5, 1], delay: 0.4 }}
      className="w-1.5 h-1.5 bg-primary-start rounded-full mx-0.5"
    />
  </span>
);