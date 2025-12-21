// FILE: src/components/Sidebar.tsx
// PHOENIX PROTOCOL - SIDEBAR V1.3 (MOBILE OPTIMIZATION)
// 1. FIX: Optimized mobile layout to prevent vertical overcrowding on small screens.
// 2. UI: Added distinct background and compact styling to the mobile user footer.
// 3. LOGIC: Enforced flex constraints to ensure navigation scrolls properly.

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
    Calendar, FileText, MessageSquare, 
    Building2, Shield, LogOut, User as UserIcon, Scale 
} from 'lucide-react';
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
        label: t('sidebar.business', 'Zyra Ime'), 
        path: '/business' 
      },
      { 
        icon: Scale, 
        label: t('sidebar.juristi_ai', 'Juristi AI'), 
        path: '/dashboard' 
      },
      { 
        icon: Calendar, 
        label: t('sidebar.calendar', 'Kalendari'), 
        path: '/calendar' 
      }, 
      { 
        icon: FileText, 
        label: t('sidebar.drafting', 'Hartimi'), 
        path: '/drafting' 
      },
      { 
        icon: MessageSquare, 
        label: t('sidebar.support', 'Ndihma'), 
        path: '/support' 
      },
    ];

    if (user?.role === 'ADMIN') {
      baseItems.splice(1, 0, {
        icon: Shield,
        label: t('sidebar.admin', 'Admin Panel'),
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
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/80 z-40 lg:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside className={`
        fixed top-0 left-0 z-50 h-full w-64 bg-background-dark border-r border-glass-edge shadow-2xl
        transform transition-transform duration-300 ease-in-out lg:translate-x-0 flex flex-col
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
          
          {/* Header */}
          <div className="h-16 flex items-center px-6 border-b border-glass-edge bg-background-light/10 flex-shrink-0">
            <BrandLogo />
          </div>

          {/* Navigation - PHOENIX FIX: Added min-h-0 to force scrolling */}
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
                      ? 'bg-secondary-start/10 text-secondary-start shadow-lg shadow-secondary-start/5' 
                      : 'text-text-secondary hover:text-white hover:bg-white/5'}
                  `}
                >
                  <div className="flex items-center">
                      {isActive && (
                          <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary-start rounded-r-full" />
                      )}
                      <Icon className={`h-5 w-5 mr-3 transition-colors ${isActive ? 'text-secondary-start' : 'group-hover:text-white'}`} />
                      <span className="font-medium text-sm">{item.label}</span>
                  </div>
                </NavLink>
              );
            })}
          </nav>

          {/* Mobile-Only Profile Footer - PHOENIX FIX: Compact Design */}
          <div className="p-3 border-t border-glass-edge bg-[#0a0a0a] lg:hidden mt-auto flex-shrink-0 pb-safe">
            <div className="flex items-center gap-3 mb-3 px-1">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-secondary-start to-secondary-end flex items-center justify-center text-white font-bold shadow-md shrink-0">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="overflow-hidden min-w-0">
                <p className="text-sm font-bold text-white truncate">{user?.username}</p>
                <p className="text-[10px] text-gray-500 truncate uppercase tracking-wider">{user?.role}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
                <NavLink 
                    to="/account"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center justify-center px-2 py-2 rounded-lg bg-white/5 text-gray-300 hover:bg-white/10 hover:text-white transition-colors text-xs font-bold border border-white/5"
                >
                    <UserIcon className="h-3.5 w-3.5 mr-2" />
                    {t('sidebar.account', 'Profili')}
                </NavLink>
                <button 
                    onClick={handleLogout}
                    className="flex items-center justify-center px-2 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors text-xs font-bold border border-red-500/20"
                >
                    <LogOut className="h-3.5 w-3.5 mr-2" />
                    {t('header.logout', 'Dilni')}
                </button>
            </div>
          </div>
          
      </aside>
    </>
  );
};

export default Sidebar;