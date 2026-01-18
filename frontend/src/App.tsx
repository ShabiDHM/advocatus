// FILE: src/App.tsx
// PHOENIX PROTOCOL - ROUTING V2.3 (JOIN ROUTE ENABLED)
// 1. FEATURE: Added public route '/join'.
// 2. LOGIC: Handles "Magic Links" for team invitations.

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import MainLayout from './pages/MainLayout';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import JoinPage from './pages/JoinPage'; // PHOENIX: Imported Join Page
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
      {/* Public Routes (No Auth Required) */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" /> : <LandingPage />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterPage />} />
      
      {/* PHOENIX: Join Route (Invitation Magic Link) */}
      <Route path="/join" element={<JoinPage />} />

      {/* Client Portal Route (Public Access via Link) */}
      <Route path="/portal/:caseId" element={<ClientPortalPage />} />

      {/* Standalone Protected Routes (No Sidebar) */}
      <Route path="/finance/wizard" element={<ProtectedRoute><FinanceWizardPage /></ProtectedRoute>} />

      {/* Standard Protected Routes (With Sidebar) */}
      <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/cases/:caseId" element={<CaseViewPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/drafting" element={<DraftingPage />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/business" element={<BusinessPage />} />
        <Route path="/account" element={<AccountPage />} />
      </Route>

      {/* Admin Protected Route */}
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