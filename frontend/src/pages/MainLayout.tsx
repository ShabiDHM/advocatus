// /home/user/advocatus-frontend/src/pages/MainLayout.tsx
// DEFINITIVE VERSION 2.1 - DESIGN TRANSPLANT: Applied Global Animated Background and Structure
// FIX APPLIED 18.10: Increased Header container z-index to resolve click interception by the main content area.

import React from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header'; 
import { motion } from 'framer-motion'; // NEW: For page-wide motion

const MainLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation(); // Import and use useLocation for the key

  // If loading, render a simple dark placeholder
  if (isLoading) {
    // DESIGN: Render a simple dark background while loading
    return <div className="min-h-screen bg-background-dark"></div>; 
  }

  // If not authenticated, redirect to the login page
  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  // Render the authenticated layout
  return (
    // DESIGN: Apply global animated gradient background
    <div className="flex flex-col min-h-screen bg-background-dark 
                    bg-gradient-to-br from-background-dark via-background-light to-background-dark 
                    bg-[length:200%_200%] animate-gradient-shift relative">
      
      {/* DESIGN: Placeholder for Floating Particles - Can be implemented as a separate component */}
      <div className="absolute inset-0 z-0 opacity-50 pointer-events-none [mask-image:radial-gradient(transparent_0%,_white_100%)]">
        {/* Animated particle div/SVG would go here */}
      </div>

      {/* FIX: Header is Z-20 to ensure it and its dropdowns are definitively above the Z-10 main content */}
      <div className="z-20 relative"> 
        <Header />
      </div>
      
      {/* Main Content Area */}
      <main className="flex-grow p-4 md:p-6 container mx-auto z-10">
        {/* Use Framer Motion on the Outlet for full-page transitions */}
        <motion.div 
            key={location.pathname} // Forces re-mount and animation on route change
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
        >
          <Outlet />
        </motion.div>
      </main>
      {/* Footer can be added here */}
    </div>
  );
};

export default MainLayout;