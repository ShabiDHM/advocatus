// FILE: src/components/BrandLogo.tsx
// PHOENIX PROTOCOL - PLATFORM IDENTITY V7.0 (JURISTI VIRTUAL & SUBTITLE INTEGRATION)

import React from 'react';
import { Scale } from 'lucide-react';

interface BrandLogoProps {
  className?: string;
  showText?: boolean;
}

const BrandLogo: React.FC<BrandLogoProps> = ({ className = "", showText = true }) => {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Platform Icon - Scales of Justice */}
      <div className="w-9 h-9 flex-shrink-0 bg-primary-start/10 border border-primary-start/20 rounded-xl flex items-center justify-center shadow-md backdrop-blur-md">
        <Scale className="w-5 h-5 text-primary-start" />
      </div>
      
      {/* Platform Title & Subtitle */}
      {showText && (
        <div className="flex flex-col text-left justify-center min-w-0">
          <span className="text-base sm:text-lg font-black bg-gradient-to-r from-primary-start to-primary-end bg-clip-text text-transparent whitespace-nowrap leading-tight tracking-tight">
            Juristi Virtual
          </span>
          <span className="text-[9.5px] sm:text-[10px] font-medium text-text-muted whitespace-nowrap leading-none tracking-tight mt-0.5">
            Menaxhim dhe ndihmë ligjore
          </span>
        </div>
      )}
    </div>
  );
};

export default BrandLogo;