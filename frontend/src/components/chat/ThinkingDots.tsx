// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - GPU HARDWARE-ACCELERATED WAVE BOUNCE V90.0 (UNFREEZABLE)

import React from 'react';

export const ThinkingDots: React.FC = () => {
  return (
    <>
      <style>{`
        @keyframes phoenixWaveBounce {
          0%, 100% {
            transform: translateY(0);
            opacity: 0.3;
          }
          50% {
            transform: translateY(-5px);
            opacity: 1;
          }
        }
        .phoenix-wave-dot-1 {
          animation: phoenixWaveBounce 0.75s ease-in-out infinite;
          animation-delay: 0s;
        }
        .phoenix-wave-dot-2 {
          animation: phoenixWaveBounce 0.75s ease-in-out infinite;
          animation-delay: 0.18s;
        }
        .phoenix-wave-dot-3 {
          animation: phoenixWaveBounce 0.75s ease-in-out infinite;
          animation-delay: 0.36s;
        }
      `}</style>

      <span className="inline-flex items-center gap-1.5 ml-2 py-0.5 align-middle">
        <span className="w-1.5 h-1.5 rounded-full bg-primary-start shadow-xs shadow-primary-start/50 inline-block phoenix-wave-dot-1" />
        <span className="w-1.5 h-1.5 rounded-full bg-primary-start shadow-xs shadow-primary-start/50 inline-block phoenix-wave-dot-2" />
        <span className="w-1.5 h-1.5 rounded-full bg-primary-start shadow-xs shadow-primary-start/50 inline-block phoenix-wave-dot-3" />
      </span>
    </>
  );
};

export default ThinkingDots;