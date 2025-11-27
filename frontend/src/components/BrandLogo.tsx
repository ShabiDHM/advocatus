// FILE: src/components/BrandLogo.tsx
// PHOENIX PROTOCOL - BRANDING INTEGRITY
// 1. COMPONENT: A new, reusable component for the official "Juristi AI" brand logo.
// 2. SVG: Contains the vector data for the "scales of justice" icon.
// 3. USAGE: To be used in Sidebar.tsx and MainLayout.tsx to enforce brand consistency.

import React from 'react';

const BrandLogo: React.FC = () => {
  return (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 bg-background-light border border-glass-edge rounded-lg flex items-center justify-center shadow-lg">
        {/* SVG Icon: Scales of Justice */}
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
      <span className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
        Juristi AI
      </span>
    </div>
  );
};

export default BrandLogo;