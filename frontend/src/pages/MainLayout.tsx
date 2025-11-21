// FILE: src/pages/MainLayout.tsx
// PHOENIX PROTOCOL - UI OPTIMIZATION
// 1. LOGIC CHANGE: Footer now ONLY appears on the Dashboard.
// 2. REASONING: Maximizes screen real estate for document viewing, drafting, and analysis tools.
// 3. LAYOUT: Keeps the main content scrollable and the header static.

import React, { Suspense } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

// Correct paths for components
import Header from '../components/Header'; 
import Footer from '../components/Footer'; 

// --- Custom Scrollbar Styles ---
const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
`;

const MainLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="min-h-screen bg-background-dark"></div>; 
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  // PHOENIX FIX: Only show footer on the main Dashboard route
  const showFooter = location.pathname === '/dashboard' || location.pathname === '/dashboard/';

  return (
    <div className="flex flex-col h-screen bg-background-dark 
                    bg-gradient-to-br from-background-dark via-background-light to-background-dark 
                    bg-[length:200%_200%] animate-gradient-shift relative overflow-hidden">
      
      <style>{scrollbarStyles}</style>

      <div className="absolute inset-0 z-0 opacity-50 pointer-events-none [mask-image:radial-gradient(transparent_0%,_white_100%)]">
      </div>

      {/* Static Header */}
      <div className="z-20 relative flex-shrink-0"> 
        <Header />
      </div>
      
      {/* Scrollable Main Content Area */}
      <main className="flex-grow px-3 py-4 md:p-6 container mx-auto z-10 max-w-full md:max-w-7xl flex flex-col overflow-y-auto custom-scrollbar">
        <Suspense fallback={<div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>}>
            <motion.div 
                key={location.pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="flex-grow flex flex-col"
            >
              <Outlet />
            </motion.div>
        </Suspense>
      </main>

      {/* PHOENIX FIX: Conditionally Render Footer */}
      {showFooter && (
        <div className="z-20 relative flex-shrink-0">
          <Footer />
        </div>
      )}
    </div>
  );
};

export default MainLayout;