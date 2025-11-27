// FILE: src/pages/MainLayout.tsx
// PHOENIX PROTOCOL - MAIN LAYOUT
// 1. BRANDING FIX: Replaced the static text logo in the mobile header with the new reusable BrandLogo component.
// 2. INTEGRITY: Ensures consistent branding between mobile and desktop views.

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';
import BrandLogo from '../components/BrandLogo'; // PHOENIX: Import the new component

const MainLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background-dark text-text-primary overflow-hidden">
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />

      <div className="flex-1 flex flex-col overflow-hidden lg:ml-64 relative transition-all duration-300">
        
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between p-4 border-b border-glass-edge bg-background-light/10 backdrop-blur-md z-10">
          {/* PHOENIX FIX: Using the BrandLogo component */}
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

        <Footer />
      </div>
    </div>
  );
};

export default MainLayout;