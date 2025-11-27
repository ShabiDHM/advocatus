// FILE: src/components/Sidebar.tsx
// PHOENIX PROTOCOL - ARCHITECTURAL CONSOLIDATION (FINAL)
// 1. UI CLEANUP: Removed the entire redundant user profile and logout section from the bottom of the sidebar.
// 2. SINGLE SOURCE OF TRUTH: The Header component is now the single, authoritative location for user session controls.
// 3. VERIFIED: All primary navigation functionality is preserved.

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Calendar, FileText, MessageSquare, Building2, Shield } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import BrandLogo from './BrandLogo';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen }) => {
  const { t } = useTranslation();
  const { user } = useAuth(); // Note: 'logout' is no longer needed here.
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

          {/* PHOENIX FIX: The redundant user profile and logout section has been removed. */}
          
        </div>
      </aside>
    </>
  );
};

export default Sidebar;