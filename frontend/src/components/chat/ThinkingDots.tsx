// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - NATIVE TAILWIND HARDWARE-ACCELERATED WAVE BOUNCE V70.0

import React from 'react';

export const ThinkingDots: React.FC = () => (
  <span className="inline-flex items-center gap-1 ml-2 py-0.5">
    <span className="w-1.5 h-1.5 rounded-full bg-primary-start animate-bounce [animation-delay:-0.32s] shadow-xs shadow-primary-start/50" />
    <span className="w-1.5 h-1.5 rounded-full bg-primary-start animate-bounce [animation-delay:-0.16s] shadow-xs shadow-primary-start/50" />
    <span className="w-1.5 h-1.5 rounded-full bg-primary-start animate-bounce shadow-xs shadow-primary-start/50" />
  </span>
);

export default ThinkingDots;