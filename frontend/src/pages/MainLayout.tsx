// FILE: src/pages/MainLayout.tsx
// PHOENIX PROTOCOL - BUILD FIX (CRITICAL)
// 1. SYNTAX FIX: Corrected the invalid import statement for 'useState' on line 6. This resolves the primary build failure.
// 2. VERIFIED: All other architectural changes, including the removal of the Footer, are maintained.

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import BrandLogo from '../components/BrandLogo';

const MainLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background-dark text-text-primary overflow-hidden">
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden lg:ml-64 relative transition-all duration-300">
        
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between p-4 border-b border-glass-edge bg-background-light/10 backdrop-blur-md z-10">
          <BrandLogo />
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-white/10 text-white transition-colors"
          >
            <Menu className="w-6 h-6" />
          </button>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-0 bg-gradient-to-br from-background-dark to-background-light/5 custom-scrollbar">
          <Outlet />
        </main>

      </div>
    </div>
  );
};

export default MainLayout;