// FILE: src/components/BrandLogo.tsx
// PHOENIX PROTOCOL - PLATFORM IDENTITY V2.0 (ICON ALIGNMENT)
// 1. REFINED: Replaced custom SVG with 'Scale' icon from lucide-react for consistency.
// 2. PURPOSE: Represents the SaaS Platform ("Juristi AI"). 
// 3. USAGE: Use ONLY in Sidebar, Navbar, and Auth screens. NEVER in user-generated content.
// 4. OPTIMIZATION: Added 'className' for flexible layout.

import React from 'react';
import { Scale } from 'lucide-react'; // PHOENIX: Import the Scale icon

interface BrandLogoProps {
  className?: string;
  showText?: boolean;
}

const BrandLogo: React.FC<BrandLogoProps> = ({ className = "", showText = true }) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Platform Icon - Scales of Justice */}
      <div className="w-8 h-8 flex-shrink-0 bg-white/5 border border-white/10 rounded-lg flex items-center justify-center shadow-lg backdrop-blur-md">
        {/* PHOENIX: Replaced SVG with Lucide Icon */}
        <Scale className="w-5 h-5 text-white" />
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