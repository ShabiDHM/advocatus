// FILE: src/App.tsx
// PHOENIX PROTOCOL - ROUTING V10.0 (SUBSCRIPTION GUARD)
// V10.0: SUBSCRIPTION GUARD —
//        - `ProtectedRoute` me prop `requireSubscription` (default true).
//        - Admin/Superadmin → bypass kontroll abonimi.
//        - User INACTIVE ose i skaduar → redirect /pending-approval.
//        - Whitelist routes (`/account`, `/support`, `/laws/*`) nuk kërkojnë abonim.
//        - Route i ri: `/pending-approval` (standalone, pa MainLayout).
// V9.0: Hequr route /mobile-upload/:token + import MobileConnect.

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import MainLayout from './pages/MainLayout';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AcceptInvitePage from './pages/AcceptInvitePage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import DashboardPage from './pages/DashboardPage';
import CaseViewPage from './pages/CaseViewPage';
import CalendarPage from './pages/CalendarPage';
import SupportPage from './pages/SupportPage';
import LandingPage from './pages/LandingPage';
import BusinessPage from './pages/BusinessPage';
import AccountPage from './pages/AccountPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import AdminSupportPage from './pages/AdminSupportPage';
import FinanceWizardPage from './pages/FinanceWizardPage';
import ClientPortalPage from './pages/ClientPortalPage';
import LawViewerPage from './pages/LawViewerPage';
import LawSearchPage from './pages/LawSearchPage';
import LawArticlePage from './pages/LawArticlePage';
import LawOverviewPage from './pages/LawOverviewPage';
import ChatPage from './pages/ChatPage';
import PendingApprovalPage from './pages/PendingApprovalPage';

// ═══════════════════════════════════════════════════════════════════════════
// GUARDS
// ═══════════════════════════════════════════════════════════════════════════

const _isAdmin = (role?: string): boolean => {
  const r = (role || '').toUpperCase();
  return r === 'ADMIN' || r === 'SUPERADMIN';
};

const _hasActiveSubscription = (user: any): boolean => {
  if (!user) return false;
  const status = String(user.subscription_status || '').toUpperCase();
  if (status !== 'ACTIVE') return false;

  if (user.subscription_expiry) {
    try {
      const expiry = new Date(user.subscription_expiry);
      if (expiry < new Date()) return false;
    } catch {
      // Pa datë valide → lejo
    }
  }
  return true;
};

/**
 * V10.0: Guard me dy nivele.
 * - requireSubscription=true (default): kërkon auth + abonim aktiv. Admin bypass.
 * - requireSubscription=false: vetëm auth (whitelist: /account, /support, /laws, /pending-approval).
 */
const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  requireSubscription?: boolean;
}> = ({ children, requireSubscription = true }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-canvas">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Admin bypass — gjithmonë kalon
  if (_isAdmin(user?.role)) {
    return <>{children}</>;
  }

  // Kontroll abonimi (vetëm nëse kërkohet)
  if (requireSubscription && !_hasActiveSubscription(user)) {
    return <Navigate to="/pending-approval" replace />;
  }

  return <>{children}</>;
};

const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-canvas">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!_isAdmin(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
};

// ═══════════════════════════════════════════════════════════════════════════
// ROUTES
// ═══════════════════════════════════════════════════════════════════════════

const AppRoutes: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* ─── Publike ─── */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />
      <Route path="/portal/:caseId" element={<ClientPortalPage />} />

      {/* ─── Pending Approval (standalone, auth required, NO subscription required) ─── */}
      <Route
        path="/pending-approval"
        element={
          <ProtectedRoute requireSubscription={false}>
            <PendingApprovalPage />
          </ProtectedRoute>
        }
      />

      {/* ─── Whitelist: auth required, NO subscription required (MainLayout) ─── */}
      <Route
        element={
          <ProtectedRoute requireSubscription={false}>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/account" element={<AccountPage />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/laws/search" element={<LawSearchPage />} />
        <Route path="/laws/overview" element={<LawOverviewPage />} />
        <Route path="/laws/article" element={<LawArticlePage />} />
        <Route path="/laws/:chunkId" element={<LawViewerPage />} />
      </Route>

      {/* ─── Biznes: auth + subscription required (MainLayout) ─── */}
      <Route
        element={
          <ProtectedRoute requireSubscription={true}>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/cases/:caseId" element={<CaseViewPage />} />
        <Route path="/cases/:caseId/chat" element={<ChatPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/business" element={<BusinessPage />} />
        <Route path="/finance/wizard" element={<FinanceWizardPage />} />
      </Route>

      {/* ─── Admin ─── */}
      <Route
        element={
          <AdminRoute>
            <MainLayout />
          </AdminRoute>
        }
      >
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/admin/support" element={<AdminSupportPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <Router>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </Router>
    </ThemeProvider>
  );
};

export default App;