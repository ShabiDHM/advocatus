// FILE: src/layouts/MainLayout.tsx
// PHOENIX PROTOCOL - LAYOUT V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, text-text-primary, border-main.
// 2. Ambient glows use semantic color variables (primary-start, secondary-start).
// 3. Removed sidebar references; full‑width content.
// 4. Header remains sticky; page scrolls normally.

import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header';

const MainLayout: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen w-full bg-canvas text-text-primary relative selection:bg-primary-start/30">
      
      {/* --- AMBIENT BACKGROUND GLOWS (semantic) --- */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-[20%] -right-[10%] w-[800px] h-[800px] bg-primary-start/20 rounded-full blur-[120px] opacity-40 animate-pulse-slow"></div>
        <div className="absolute -bottom-[20%] -left-[10%] w-[600px] h-[600px] bg-secondary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-surface/40 rounded-full blur-[150px] opacity-20"></div>
      </div>

      {/* --- HEADER (fixed navigation) --- */}
      <header className="sticky top-0 shrink-0 relative z-40">
        <Header />
      </header>

      {/* --- MAIN CONTENT AREA (full width) --- */}
      <div className="flex-1 flex flex-col relative w-full">
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