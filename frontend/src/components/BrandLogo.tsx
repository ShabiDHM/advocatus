// FILE: src/components/BrandLogo.tsx
// PHOENIX PROTOCOL - PLATFORM IDENTITY V2.1 (SEMANTIC COLORS)
// 1. UPDATED: Hardcoded white colors replaced with semantic variables.
// 2. ICON: Uses primary-start for consistent brand accent.
// 3. TEXT: Uses gradient from primary-start to primary-end for modern look.

import React from 'react';
import { Scale } from 'lucide-react';

interface BrandLogoProps {
  className?: string;
  showText?: boolean;
}

const BrandLogo: React.FC<BrandLogoProps> = ({ className = "", showText = true }) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Platform Icon - Scales of Justice */}
      <div className="w-8 h-8 flex-shrink-0 bg-surface/10 border border-main rounded-lg flex items-center justify-center shadow-lg backdrop-blur-md">
        <Scale className="w-5 h-5 text-primary-start" />
      </div>
      
      {/* Platform Name */}
      {showText && (
        <span className="text-xl font-bold bg-gradient-to-r from-primary-start to-primary-end bg-clip-text text-transparent whitespace-nowrap">
          Juristi AI
        </span>
      )}
    </div>
  );
};

export default BrandLogo;