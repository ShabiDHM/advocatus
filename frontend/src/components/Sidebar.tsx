// FILE: src/components/Sidebar.tsx
// PHOENIX PROTOCOL - SIDEBAR V3.0 (NAVIGATION STREAMLINING)
// 1. UX: Removed the static 'Calendar' link from the main navigation array.
// 2. WORKFLOW: This change reinforces the 'Kujdestari' briefing as the primary entry point for calendar-related tasks.

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
    FileText, MessageSquare, 
    Building2, Shield, LogOut, User as UserIcon, Scale 
} from 'lucide-react'; // REMOVED: Calendar icon
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import BrandLogo from './BrandLogo';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen }) => {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();

  const getNavItems = () => {
    const baseItems = [
      { 
        icon: Building2, 
        label: t('sidebar.myOffice', 'Zyra'), 
        path: '/business' 
      },
      { 
        icon: Scale, 
        label: t('sidebar.juristiAi', 'Rastet'), 
        path: '/dashboard' 
      },
      // --- ITEM REMOVED ---
      // { 
      //   icon: Calendar, 
      //   label: t('sidebar.calendar', 'Kalendari'), 
      //   path: '/calendar' 
      // }, 
      // --- END REMOVAL ---
      { 
        icon: FileText, 
        label: t('sidebar.drafting', 'Hartimi'), 
        path: '/drafting' 
      },
      { 
        icon: MessageSquare, 
        label: t('sidebar.support', 'Mbështetja'), 
        path: '/support' 
      },
    ];

    if (user?.role === 'ADMIN') {
      // Insert Admin Panel after "Zyra"
      baseItems.splice(1, 0, {
        icon: Shield,
        label: t('sidebar.adminPanel', 'Admin'),
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
      {/* Mobile Backdrop */}
      <div 
        className={`fixed inset-0 bg-background-dark/80 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setIsOpen(false)}
      />

      <aside className={`
        fixed top-0 left-0 z-50 h-full w-64 
        bg-background-dark/70 backdrop-blur-xl border-r border-white/5 shadow-2xl
        transform transition-transform duration-300 cubic-bezier(0.4, 0, 0.2, 1) lg:translate-x-0 flex flex-col
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
          
          {/* Header */}
          <div className="h-16 flex items-center px-6 border-b border-white/5 flex-shrink-0">
            <BrandLogo />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto custom-scrollbar min-h-0">
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
                      ? 'bg-primary-start/10 text-primary-start shadow-[0_0_20px_rgba(37,99,235,0.15)] border border-primary-start/10' 
                      : 'text-text-secondary hover:text-white hover:bg-white/5 border border-transparent'}
                  `}
                >
                  <div className="flex items-center relative z-10">
                      <Icon className={`h-5 w-5 mr-3 transition-colors ${isActive ? 'text-primary-start' : 'group-hover:text-white'}`} />
                      <span className="font-medium text-sm">{item.label}</span>
                  </div>
                  
                  {/* Active Indicator */}
                  {isActive && (
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary-start rounded-l-full shadow-[0_0_10px_#2563eb]" />
                  )}
                </NavLink>
              );
            })}
          </nav>

          {/* Mobile Profile Footer */}
          <div className="p-2 border-t border-white/5 bg-background-dark/40 lg:hidden mt-auto flex-shrink-0 pb-safe backdrop-blur-md">
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className="h-8 w-8 rounded-md bg-gradient-to-br from-secondary-start to-secondary-end flex items-center justify-center text-white font-bold shadow-lg shadow-secondary-start/20 shrink-0 text-sm">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="overflow-hidden min-w-0">
                <p className="text-sm font-bold text-white truncate">{user?.username}</p>
                <p className="text-xs text-text-secondary truncate uppercase tracking-wider">{user?.role}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
                <NavLink 
                    to="/account"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center justify-center px-2 py-2 rounded-lg bg-white/5 text-text-secondary hover:bg-white/10 hover:text-white transition-colors text-xs font-bold border border-white/5"
                >
                    <UserIcon className="h-3.5 w-3.5 mr-1.5" />
                    {t('sidebar.account', 'Profili')}
                </NavLink>
                <button 
                    onClick={handleLogout}
                    className="flex items-center justify-center px-2 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors text-xs font-bold border border-red-500/20"
                >
                    <LogOut className="h-3.5 w-3.5 mr-1.5" />
                    {t('general.logout', 'Dalja')}
                </button>
            </div>
          </div>
          
      </aside>
    </>
  );
};

export default Sidebar;