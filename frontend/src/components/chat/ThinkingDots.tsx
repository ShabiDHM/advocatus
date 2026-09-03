// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - NATIVE TAILWIND BOUNCE WAVE V100.0 (100% UNFREEZABLE)

import React from 'react';

export const ThinkingDots: React.FC = () => {
  return (
    <span className="inline-flex items-center gap-1.5 ml-2 py-1 align-middle">
      <span className="w-2 h-2 rounded-full bg-primary-start animate-bounce [animation-delay:-0.3s] shadow-sm shadow-primary-start/50 inline-block" />
      <span className="w-2 h-2 rounded-full bg-primary-start animate-bounce [animation-delay:-0.15s] shadow-sm shadow-primary-start/50 inline-block" />
      <span className="w-2 h-2 rounded-full bg-primary-start animate-bounce shadow-sm shadow-primary-start/50 inline-block" />
    </span>
  );
};

export default ThinkingDots;