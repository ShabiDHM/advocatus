// FILE: src/components/Sidebar.tsx
// PHOENIX PROTOCOL - SIDEBAR V3.0 (SAFE ALERTS)
// 1. FEATURE: Added Notification Badge for Calendar Alerts.
// 2. SECURITY: Fetches alerts ONLY when 'user' is authenticated (Prevents 401 Race Condition).
// 3. UI: Added count badge to the Calendar navigation item.

import React, { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
    LayoutDashboard, Calendar, FileText, MessageSquare, 
    Building2, Shield, LogOut, User as UserIcon 
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api'; // Import API
import BrandLogo from './BrandLogo';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen }) => {
  const { t } = useTranslation();
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const [alertCount, setAlertCount] = useState(0);

  // PHOENIX FIX: Safe Fetch Logic
  // Prevents 401 errors by waiting for Authentication before requesting data.
  useEffect(() => {
    let mounted = true;

    const fetchAlerts = async () => {
        if (!isAuthenticated || !user) return; // The Guard Clause
        
        try {
            const data = await apiService.getAlertsCount();
            if (mounted) setAlertCount(data.count);
        } catch (error) {
            console.error("Failed to fetch sidebar alerts", error);
        }
    };

    fetchAlerts();

    // Optional: Refresh alerts every minute if sidebar is open/visible
    const interval = setInterval(fetchAlerts, 60000);
    return () => { 
        mounted = false; 
        clearInterval(interval); 
    };
  }, [isAuthenticated, user]); // Re-run when auth state changes

  const getNavItems = () => {
    const baseItems = [
      { icon: LayoutDashboard, label: t('sidebar.dashboard'), path: '/dashboard' },
      { icon: Calendar, label: t('sidebar.calendar'), path: '/calendar', badge: alertCount }, // Attach Badge
      { icon: FileText, label: t('sidebar.drafting'), path: '/drafting' },
      { icon: Building2, label: t('sidebar.business'), path: '/business' },
      { icon: MessageSquare, label: t('sidebar.support'), path: '/support' },
    ];

    if (user?.role === 'ADMIN') {
      baseItems.splice(1, 0, {
        icon: Shield,
        label: t('sidebar.admin'),
        path: '/admin',
      });
    }

    return baseItems;
  };

  const navItems = getNavItems();

  const handleLogout = () => {
    logout();
    setIsOpen(false);
  };

  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 lg:hidden backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside className={`
        fixed top-0 left-0 z-30 h-full w-64 bg-background-dark border-r border-glass-edge shadow-2xl
        transform transition-transform duration-300 ease-in-out lg:translate-x-0 flex flex-col
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
          
          <div className="h-16 flex items-center px-6 border-b border-glass-edge bg-background-light/10 flex-shrink-0">
            <BrandLogo />
          </div>

          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto custom-scrollbar">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  className={`
                    flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden
                    ${isActive 
                      ? 'bg-secondary-start/10 text-secondary-start shadow-lg shadow-secondary-start/5' 
                      : 'text-text-secondary hover:text-white hover:bg-white/5'}
                  `}
                >
                  <div className="flex items-center">
                      {isActive && (
                          <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-start rounded-r-full" />
                      )}
                      <Icon className={`h-5 w-5 mr-3 transition-colors ${isActive ? 'text-secondary-start' : 'group-hover:text-white'}`} />
                      <span className="font-medium">{item.label}</span>
                  </div>
                  
                  {/* BADGE RENDERER */}
                  {item.badge && item.badge > 0 ? (
                      <span className="bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md shadow-red-500/20">
                          {item.badge}
                      </span>
                  ) : null}
                </NavLink>
              );
            })}
          </nav>

          {/* Mobile-Only Profile Footer */}
          <div className="p-4 border-t border-glass-edge bg-background-light/5 lg:hidden mt-auto flex-shrink-0">
            <div className="flex items-center gap-3 mb-4 px-2">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-secondary-start to-secondary-end flex items-center justify-center text-white font-bold shadow-lg">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-medium text-white truncate">{user?.username}</p>
                <p className="text-xs text-text-secondary truncate uppercase tracking-wider">{user?.role}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
                <NavLink 
                    to="/account"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center justify-center px-3 py-2.5 rounded-xl bg-white/5 text-text-secondary hover:bg-white/10 hover:text-white transition-colors text-sm font-medium border border-white/5"
                >
                    <UserIcon className="h-4 w-4 mr-2" />
                    {t('sidebar.account', 'Profili')}
                </NavLink>
                <button 
                    onClick={handleLogout}
                    className="flex items-center justify-center px-3 py-2.5 rounded-xl bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors text-sm font-medium border border-red-500/20"
                >
                    <LogOut className="h-4 w-4 mr-2" />
                    {t('header.logout', 'Shkyçu')}
                </button>
            </div>
          </div>
          
      </aside>
    </>
  );
};

export default Sidebar;