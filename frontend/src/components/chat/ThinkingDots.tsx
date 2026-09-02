// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - FLUID BOUNCING WAVE THINKING DOTS V50.0

import React from 'react';
import { motion } from 'framer-motion';

export const ThinkingDots: React.FC = () => (
  <span className="inline-flex items-center gap-1 ml-2">
    <motion.span
      animate={{ y: [0, -5, 0], scale: [1, 1.3, 1], opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0 }}
      className="w-1.5 h-1.5 bg-primary-start rounded-full inline-block shadow-xs shadow-primary-start/40"
    />
    <motion.span
      animate={{ y: [0, -5, 0], scale: [1, 1.3, 1], opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0.18 }}
      className="w-1.5 h-1.5 bg-primary-start rounded-full inline-block shadow-xs shadow-primary-start/40"
    />
    <motion.span
      animate={{ y: [0, -5, 0], scale: [1, 1.3, 1], opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut", delay: 0.36 }}
      className="w-1.5 h-1.5 bg-primary-start rounded-full inline-block shadow-xs shadow-primary-start/40"
    />
  </span>
);

export default ThinkingDots;