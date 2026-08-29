// FILE: src/components/BrandLogo.tsx
// PHOENIX PROTOCOL - PLATFORM IDENTITY V9.0 (NDIHMË JURIDIKE - DATA & HUMAN MANAGEMENT)

import React from 'react';
import { Scale } from 'lucide-react';

interface BrandLogoProps {
  className?: string;
  showText?: boolean;
}

const BrandLogo: React.FC<BrandLogoProps> = ({ className = "", showText = true }) => {
  return (
    <div className={`flex items-center gap-2.5 sm:gap-3 ${className}`}>
      {/* Platform Icon - Scales of Justice with glowing glass container */}
      <div className="w-9 h-9 sm:w-10 sm:h-10 flex-shrink-0 bg-primary-start/10 border border-primary-start/25 dark:border-primary-start/40 rounded-xl flex items-center justify-center shadow-sm backdrop-blur-md transition-transform duration-200 group-hover:scale-105">
        <Scale className="w-5 h-5 text-primary-start" />
      </div>
      
      {/* Platform Title & Subtitle */}
      {showText && (
        <div className="flex flex-col text-left justify-center min-w-0">
          <span className="text-base sm:text-lg font-black tracking-tight leading-tight bg-gradient-to-r from-primary-start via-primary-start to-indigo-500 bg-clip-text text-transparent whitespace-nowrap select-none">
            Ndihmë Juridike
          </span>
          <span className="text-[9px] sm:text-[9.5px] font-bold uppercase tracking-[0.14em] text-text-muted dark:text-text-secondary whitespace-nowrap leading-none mt-0.5 select-none">
            Data and Human Management
          </span>
        </div>
      )}
    </div>
  );
};

export default BrandLogo;