// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - HARDWARE-ACCELERATED FRAMER WAVE BOUNCE V80.0

import React from 'react';
import { motion, type Transition } from 'framer-motion';

const dotTransition: Transition = {
  duration: 0.6,
  repeat: Infinity,
  repeatType: 'reverse',
  ease: 'easeInOut'
};

export const ThinkingDots: React.FC = () => {
  return (
    <span className="inline-flex items-center gap-1.5 ml-1.5 py-0.5">
      <motion.span
        animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
        transition={{ ...dotTransition, delay: 0 }}
        className="w-1.5 h-1.5 rounded-full bg-primary-start shadow-xs shadow-primary-start/50 inline-block"
      />
      <motion.span
        animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
        transition={{ ...dotTransition, delay: 0.2 }}
        className="w-1.5 h-1.5 rounded-full bg-primary-start shadow-xs shadow-primary-start/50 inline-block"
      />
      <motion.span
        animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
        transition={{ ...dotTransition, delay: 0.4 }}
        className="w-1.5 h-1.5 rounded-full bg-primary-start shadow-xs shadow-primary-start/50 inline-block"
      />
    </span>
  );
};

export default ThinkingDots;