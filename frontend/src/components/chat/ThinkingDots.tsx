// FILE: src/components/chat/ThinkingDots.tsx
// PHOENIX PROTOCOL - NATIVE SVG COMPOSITOR WAVE V110.0 (IMPOSSIBLE TO FREEZE)

import React from 'react';

export const ThinkingDots: React.FC = () => {
  return (
    <span className="inline-flex items-center ml-2 py-0.5 align-middle">
      <svg className="w-9 h-3 text-primary-start inline-block" viewBox="0 0 120 30" fill="currentColor">
        <circle cx="15" cy="15" r="12">
          <animate
            attributeName="cy"
            from="15"
            to="15"
            values="15;4;15"
            dur="0.75s"
            begin="0s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from="0.3"
            to="0.3"
            values="0.3;1;0.3"
            dur="0.75s"
            begin="0s"
            repeatCount="indefinite"
          />
        </circle>
        <circle cx="60" cy="15" r="12">
          <animate
            attributeName="cy"
            from="15"
            to="15"
            values="15;4;15"
            dur="0.75s"
            begin="0.18s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from="0.3"
            to="0.3"
            values="0.3;1;0.3"
            dur="0.75s"
            begin="0.18s"
            repeatCount="indefinite"
          />
        </circle>
        <circle cx="105" cy="15" r="12">
          <animate
            attributeName="cy"
            from="15"
            to="15"
            values="15;4;15"
            dur="0.75s"
            begin="0.36s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from="0.3"
            to="0.3"
            values="0.3;1;0.3"
            dur="0.75s"
            begin="0.36s"
            repeatCount="indefinite"
          />
        </circle>
      </svg>
    </span>
  );
};

export default ThinkingDots;