// FILE: src/pages/MainLayout.tsx
// PHOENIX PROTOCOL - VISUAL UPGRADE 4.0 (GLASSMORPHISM)
// 1. BACKGROUND: Added animated ambient glows (primary & secondary blobs).
// 2. LAYOUT: Preserved existing structural logic (Sidebar/Header) while wrapping content in relative z-containers.

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
    <div className="flex h-screen w-full overflow-hidden bg-background-dark text-text-primary relative selection:bg-primary-start/30">
      
      {/* --- AMBIENT BACKGROUND GLOWS (FIXED LAYER) --- */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Top Right - Primary Glow */}
        <div className="absolute -top-[20%] -right-[10%] w-[800px] h-[800px] bg-primary-start/20 rounded-full blur-[120px] opacity-40 animate-pulse-slow"></div>
        {/* Bottom Left - Secondary Glow */}
        <div className="absolute -bottom-[20%] -left-[10%] w-[600px] h-[600px] bg-secondary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
        {/* Center - Accent Tint */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-background-light/40 rounded-full blur-[150px] opacity-20"></div>
      </div>

      {/* --- SIDEBAR (Z-INDEX 50) --- */}
      {/* Sidebar handles its own z-index and positioning */}
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />

      {/* --- MAIN CONTENT WRAPPER (Z-INDEX 10) --- */}
      <div className="flex-1 flex flex-col overflow-hidden lg:ml-64 relative z-10 transition-all duration-300">
        
        {/* Desktop Header */}
        <div className="hidden lg:block">
          <Header toggleSidebar={toggleSidebar} />
        </div>
        
        {/* Mobile Header (Frosted) */}
        <header className="lg:hidden flex items-center justify-between p-4 border-b border-white/10 bg-background-dark/60 backdrop-blur-xl z-20">
          <BrandLogo />
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-white/10 text-white transition-colors"
          >
            <Menu className="w-6 h-6" />
          </button>
        </header>

        {/* Scrollable Page Content */}
        <main className="flex-1 overflow-y-auto p-0 scroll-smooth custom-scrollbar">
          {/* Outlet Wrapper ensures content sits above background blobs */}
          <div className="relative min-h-full">
            <Outlet />
          </div>
        </main>

      </div>
    </div>
  );
};

export default MainLayout;