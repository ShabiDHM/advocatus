// FILE: src/App.tsx
// PHOENIX PROTOCOL - ROUTING V2.7 (FINAL PATH CORRECTION)
// 1. FIX: Corrected import path for MainLayout to './pages/MainLayout' based on verified project structure.
// 2. STATUS: This resolves the final "Cannot find module" error.

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
// PHOENIX FIX: Final, corrected import path.
import MainLayout from './pages/MainLayout'; 

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AcceptInvitePage from './pages/AcceptInvitePage';
import DashboardPage from './pages/DashboardPage';
import CaseViewPage from './pages/CaseViewPage';
import CalendarPage from './pages/CalendarPage';
import DraftingPage from './pages/DraftingPage';
import SupportPage from './pages/SupportPage';
import LandingPage from './pages/LandingPage';
import BusinessPage from './pages/BusinessPage';
import AccountPage from './pages/AccountPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import FinanceWizardPage from './pages/FinanceWizardPage';
import ClientPortalPage from './pages/ClientPortalPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <div className="flex items-center justify-center h-screen bg-background-dark"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  return <>{children}</>;
};

const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  if (isLoading) {
    return <div className="flex items-center justify-center h-screen bg-background-dark"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  if (user?.role !== 'ADMIN') {
    return <Navigate to="/dashboard" />;
  }
  return <>{children}</>;
};

const AppRoutes: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" /> : <LandingPage />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterPage />} />
      
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      <Route path="/portal/:caseId" element={<ClientPortalPage />} />
      <Route path="/finance/wizard" element={<ProtectedRoute><FinanceWizardPage /></ProtectedRoute>} />

      <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/cases/:caseId" element={<CaseViewPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/drafting" element={<DraftingPage />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/business" element={<BusinessPage />} />
        <Route path="/account" element={<AccountPage />} />
      </Route>

      <Route element={<AdminRoute><MainLayout /></AdminRoute>}>
        <Route path="/admin" element={<AdminDashboardPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
};

export default App;