// FILE: src/components/MainLayout.tsx
// PHOENIX PROTOCOL - LAYOUT V5.0 (MOBILE NATIVE FEEL)
// 1. MOBILE FIX: Removed 'h-screen' and 'overflow-hidden' on mobile.
//    - This restores "Pull-to-Refresh".
//    - This restores "Hide Address Bar on Scroll".
// 2. DESKTOP: Kept 'lg:h-screen' and 'lg:overflow-hidden' for the dashboard feel.
// 3. Z-INDEX: Ensured Sidebar stays above the natural scroll flow on mobile.

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import BrandLogo from '../components/BrandLogo';

const MainLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    // PHOENIX CHANGE: 'h-screen' and 'overflow-hidden' are now DESKTOP ONLY (lg:)
    // On mobile, we use 'min-h-screen' to allow natural browser scrolling (Pull-to-Refresh).
    <div className="flex flex-col lg:flex-row min-h-screen lg:h-screen w-full bg-background-dark text-text-primary relative selection:bg-primary-start/30">
      
      {/* --- AMBIENT BACKGROUND GLOWS (FIXED) --- */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-[20%] -right-[10%] w-[800px] h-[800px] bg-primary-start/20 rounded-full blur-[120px] opacity-40 animate-pulse-slow"></div>
        <div className="absolute -bottom-[20%] -left-[10%] w-[600px] h-[600px] bg-secondary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-background-light/40 rounded-full blur-[150px] opacity-20"></div>
      </div>

      {/* --- SIDEBAR (Fixed on Desktop, Overlay on Mobile) --- */}
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />

      {/* --- CONTENT WRAPPER --- */}
      {/* Mobile: Standard Block. Desktop: Flex Column with hidden overflow */}
      <div className="flex-1 flex flex-col lg:ml-64 relative z-10 transition-all duration-300 lg:h-full lg:overflow-hidden">
        
        {/* Desktop Header */}
        <div className="hidden lg:block shrink-0">
          <Header toggleSidebar={toggleSidebar} />
        </div>
        
        {/* Mobile Header (Sticky) */}
        <header className="lg:hidden sticky top-0 flex items-center justify-between p-4 border-b border-white/10 bg-background-dark/80 backdrop-blur-xl z-30">
          <BrandLogo />
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-white/10 text-white transition-colors"
          >
            <Menu className="w-6 h-6" />
          </button>
        </header>

        {/* Content Area */}
        {/* Mobile: Natural Height. Desktop: Scrollable Area */}
        <main className="flex-1 p-0 lg:overflow-y-auto lg:custom-scrollbar scroll-smooth">
          {/* Outlet Wrapper */}
          <div className="relative min-h-full pb-20 lg:pb-0">
             <Outlet />
          </div>
        </main>

      </div>
    </div>
  );
};

export default MainLayout;