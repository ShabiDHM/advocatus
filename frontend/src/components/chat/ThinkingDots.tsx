// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - 100% PURE FLUID WAVE BOUNCING THINKING DOTS V60.0

import React from 'react';

export const ThinkingDots: React.FC = () => (
  <span className="inline-flex items-center gap-1.5 ml-2 py-1">
    <style>{`
      @keyframes waveBounce {
        0%, 80%, 100% {
          transform: translateY(0) scale(0.85);
          opacity: 0.35;
        }
        40% {
          transform: translateY(-6px) scale(1.35);
          opacity: 1;
        }
      }
      .dot-wave-1 { animation: waveBounce 1.1s infinite ease-in-out; animation-delay: 0s; }
      .dot-wave-2 { animation: waveBounce 1.1s infinite ease-in-out; animation-delay: 0.18s; }
      .dot-wave-3 { animation: waveBounce 1.1s infinite ease-in-out; animation-delay: 0.36s; }
    `}</style>
    <span className="dot-wave-1 w-2 h-2 rounded-full bg-primary-start inline-block shadow-sm shadow-primary-start/50" />
    <span className="dot-wave-2 w-2 h-2 rounded-full bg-primary-start inline-block shadow-sm shadow-primary-start/50" />
    <span className="dot-wave-3 w-2 h-2 rounded-full bg-primary-start inline-block shadow-sm shadow-primary-start/50" />
  </span>
);

export default ThinkingDots;