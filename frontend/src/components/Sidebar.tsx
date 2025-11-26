// FILE: src/components/Sidebar.tsx
// PHOENIX PROTOCOL - SIDEBAR NAVIGATION
// Includes: 'Zyra Ime' (Business) Link.

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Calendar, FileText, LogOut, MessageSquare, Building2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen }) => {
  const { t } = useTranslation();
  const { logout, user } = useAuth();
  const location = useLocation();

  const navItems = [
    { icon: LayoutDashboard, label: t('sidebar.dashboard', 'Paneli'), path: '/dashboard' },
    { icon: Calendar, label: t('sidebar.calendar', 'Kalendari'), path: '/calendar' },
    { icon: FileText, label: t('sidebar.drafting', 'Draftimi'), path: '/drafting' },
    { icon: Building2, label: t('sidebar.business', 'Zyra Ime'), path: '/business' },
    { icon: MessageSquare, label: t('sidebar.support', 'Ndihma'), path: '/support' },
  ];

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 lg:hidden backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside className={`
        fixed top-0 left-0 z-30 h-full w-64 bg-background-dark border-r border-glass-edge shadow-2xl
        transform transition-transform duration-300 ease-in-out lg:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          
          {/* Logo Area */}
          <div className="h-16 flex items-center px-6 border-b border-glass-edge bg-background-light/10">
            <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-secondary-start to-secondary-end rounded-lg flex items-center justify-center shadow-lg shadow-secondary-start/20">
                    <span className="text-white font-bold text-lg">J</span>
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                    Juristi AI
                </span>
            </div>
          </div>

          {/* Navigation Links */}
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

          {/* User Profile & Logout */}
          <div className="p-4 border-t border-glass-edge bg-background-light/5">
            <div className="flex items-center mb-4 px-2">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-primary-start to-primary-end flex items-center justify-center text-white font-bold shadow-md">
                    {user?.full_name?.charAt(0) || 'U'}
                </div>
                <div className="ml-3 overflow-hidden">
                    <p className="text-sm font-medium text-white truncate">{user?.full_name || 'User'}</p>
                    <p className="text-xs text-text-secondary truncate">{user?.email}</p>
                </div>
            </div>
            
            <button
              onClick={logout}
              className="w-full flex items-center justify-center px-4 py-2 rounded-xl border border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all duration-200"
            >
              <LogOut className="h-4 w-4 mr-2" />
              {t('sidebar.logout', 'Dilni')}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;