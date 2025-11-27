// FILE: src/components/Sidebar.tsx
// PHOENIX PROTOCOL - STATE CONFIRMED (FINAL)
// 1. ARCHITECTURE: This version is validated to be correct, with the redundant 'My Account' link properly removed.
// 2. VERIFIED: All other navigation links, including the conditional Admin route, are preserved.

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Calendar, FileText, LogOut, MessageSquare, Building2, Shield } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import BrandLogo from './BrandLogo';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen }) => {
  const { t } = useTranslation();
  const { logout, user } = useAuth();
  const location = useLocation();

  const getNavItems = () => {
    const baseItems = [
      { icon: LayoutDashboard, label: t('sidebar.dashboard'), path: '/dashboard' },
      { icon: Calendar, label: t('sidebar.calendar'), path: '/calendar' },
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
        transform transition-transform duration-300 ease-in-out lg:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          
          <div className="h-16 flex items-center px-6 border-b border-glass-edge bg-background-light/10">
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
                    flex items-center px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden
                    ${isActive 
                      ? 'bg-secondary-start/10 text-secondary-start shadow-lg shadow-secondary-start/5' 
                      : 'text-text-secondary hover:text-white hover:bg-white/5'}
                  `}
                >
                  {isActive && (
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-start rounded-r-full" />
                  )}
                  <Icon className={`h-5 w-5 mr-3 transition-colors ${isActive ? 'text-secondary-start' : 'group-hover:text-white'}`} />
                  <span className="font-medium">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          <div className="p-4 border-t border-glass-edge bg-background-light/5">
            <div className="flex items-center mb-4 px-2">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-primary-start to-primary-end flex items-center justify-center text-white font-bold shadow-md">
                    {user?.username?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="ml-3 overflow-hidden">
                    <p className="text-sm font-medium text-white truncate">{user?.username || 'User'}</p>
                    <p className="text-xs text-text-secondary truncate">{user?.email}</p>
                </div>
            </div>
            
            <button
              onClick={logout}
              className="w-full flex items-center justify-center px-4 py-2 rounded-xl border border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all duration-200"
            >
              <LogOut className="h-4 w-4 mr-2" />
              {t('sidebar.logout')}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;