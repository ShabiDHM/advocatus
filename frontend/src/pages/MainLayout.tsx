// FILE: src/pages/MainLayout.tsx
// PHOENIX PROTOCOL - LAYOUT UPDATE (PAGES FOLDER)
// 1. LOCATION: Correctly targeted for 'src/pages/'.
// 2. IMPORTS: Points to '../components/' for Header and Footer.
// 3. INTEGRATION: Includes the new Global Footer.

import React, { Suspense } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

// PHOENIX FIX: Correct paths for components from 'pages' directory
import Header from '../components/Header'; 
import Footer from '../components/Footer'; 

const MainLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="min-h-screen bg-background-dark"></div>; 
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return (
    <div className="flex flex-col min-h-screen bg-background-dark 
                    bg-gradient-to-br from-background-dark via-background-light to-background-dark 
                    bg-[length:200%_200%] animate-gradient-shift relative">
      
      <div className="absolute inset-0 z-0 opacity-50 pointer-events-none [mask-image:radial-gradient(transparent_0%,_white_100%)]">
      </div>

      <div className="z-20 relative flex-shrink-0"> 
        <Header />
      </div>
      
      <main className="flex-grow px-3 py-4 md:p-6 container mx-auto z-10 max-w-full md:max-w-7xl flex flex-col">
        <Suspense fallback={<div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>}>
            <motion.div 
                key={location.pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="flex-grow"
            >
              <Outlet />
            </motion.div>
        </Suspense>
      </main>

      {/* PHOENIX FIX: Global Footer */}
      <div className="z-20 relative mt-auto">
        <Footer />
      </div>
    </div>
  );
};

export default MainLayout;