// FILE: src/components/BrandLogo.tsx
// PHOENIX PROTOCOL - PLATFORM IDENTITY
// 1. PURPOSE: Represents the SaaS Platform ("Juristi AI"). 
// 2. USAGE: Use ONLY in Sidebar, Navbar, and Auth screens. NEVER in user-generated content.
// 3. OPTIMIZATION: Added 'className' for flexible layout.

import React from 'react';

interface BrandLogoProps {
  className?: string;
  showText?: boolean;
}

const BrandLogo: React.FC<BrandLogoProps> = ({ className = "", showText = true }) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Platform Icon - Scales of Justice */}
      <div className="w-8 h-8 flex-shrink-0 bg-white/5 border border-white/10 rounded-lg flex items-center justify-center shadow-lg backdrop-blur-md">
        <svg 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          className="text-white"
        >
          <path d="M16 16l3-8 3 8c-2 1-4 1-6 0z"></path>
          <path d="M2 16l3-8 3 8c-2 1-4 1-6 0z"></path>
          <path d="M12 2v20"></path>
          <path d="M6 6h12"></path>
          <path d="M6 16H2"></path>
          <path d="M18 16h4"></path>
        </svg>
      </div>
      
      {/* Platform Name */}
      {showText && (
        <span className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent whitespace-nowrap">
          Juristi AI
        </span>
      )}
    </div>
  );
};

export default BrandLogo;