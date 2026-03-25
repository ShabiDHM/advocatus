// src/layouts/MainLayout.tsx
import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header';

const MainLayout: React.FC = () => {
  return (
    <>
      <Header />
      <main className="pt-16 min-h-screen bg-canvas">
        <Outlet />
      </main>
    </>
  );
};

export default MainLayout;