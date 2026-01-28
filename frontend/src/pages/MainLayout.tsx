// FILE: src/layouts/MainLayout.tsx
// PHOENIX PROTOCOL - LAYOUT V6.0 (FULL HEADER NAVIGATION CONVERSION)
// 1. STRUCTURAL: Removed the entire <Sidebar /> component.
// 2. STRUCTURAL: Removed the 'isSidebarOpen' state and 'toggleSidebar' function.
// 3. CSS: Removed the 'lg:ml-64' rule to allow content to span the full width.
// 4. HEADER: Consolidated all header logic into the single <Header /> component.

import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header';

const MainLayout: React.FC = () => {

  return (
    // Removed lg:flex-row and lg:h-screen as we are now scrollable vertically (header fixed, content scrolls)
    <div className="flex flex-col min-h-screen w-full bg-background-dark text-text-primary relative selection:bg-primary-start/30">
      
      {/* --- AMBIENT BACKGROUND GLOWS --- */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-[20%] -right-[10%] w-[800px] h-[800px] bg-primary-start/20 rounded-full blur-[120px] opacity-40 animate-pulse-slow"></div>
        <div className="absolute -bottom-[20%] -left-[10%] w-[600px] h-[600px] bg-secondary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-background-light/40 rounded-full blur-[150px] opacity-20"></div>
      </div>

      {/* --- HEADER (Now the single point of navigation) --- */}
      {/* It must be fixed or sticky to remain visible */}
      <header className="sticky top-0 shrink-0 relative z-40">
        <Header />
      </header>

      {/* --- MAIN CONTENT AREA --- */}
      {/* Removed lg:ml-64 to take full width */}
      <div className="flex-1 flex flex-col relative w-full">
        
        {/* Content Area */}
        {/* Removed lg:overflow-y-auto as the whole body will now scroll */}
        <main className="flex-1 scroll-smooth">
          <div className="relative min-h-full pb-20 lg:pb-0">
             <Outlet />
          </div>
        </main>

      </div>
    </div>
  );
};

export default MainLayout;