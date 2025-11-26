// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - HEADER FIX
// 1. TYPES: Replaced 'username' with 'email' to match AuthUser type.
// 2. UI: Displays Full Name and Role correctly.

import React, { useState } from 'react';
import { Bell, Search, Menu, LogOut, User as UserIcon, Settings, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

interface HeaderProps {
  toggleSidebar: () => void;
}

const Header: React.FC<HeaderProps> = ({ toggleSidebar }) => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  return (
    <header className="h-16 bg-background-dark border-b border-glass-edge flex items-center justify-between px-4 sm:px-6 lg:px-8 z-20 sticky top-0 backdrop-blur-md bg-opacity-90">
      
      {/* Left: Mobile Menu & Search */}
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="lg:hidden p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors"
        >
          <Menu size={24} />
        </button>

        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary h-4 w-4" />
          <input 
            type="text" 
            placeholder={t('header.searchPlaceholder', 'Kërko...')} 
            className="bg-background-light/10 border border-glass-edge rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:ring-1 focus:ring-primary-start outline-none w-64 transition-all focus:w-80"
          />
        </div>
      </div>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-3 sm:gap-4">
        <button className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors relative">
          <Bell size={20} />
          <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        <div className="relative">
          <button 
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center gap-3 hover:bg-white/5 p-1.5 rounded-xl transition-colors border border-transparent hover:border-glass-edge"
          >
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-white">{user?.full_name || 'User'}</p>
              <p className="text-[10px] text-text-secondary uppercase tracking-wider">
                {/* PHOENIX FIX: Replaced user.username check with user.email */}
                {user?.role || 'LAWYER'}
              </p>
            </div>
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-secondary-start to-secondary-end flex items-center justify-center text-white font-bold shadow-lg shadow-secondary-start/20">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
          </button>

          {/* Dropdown Menu */}
          {isProfileOpen && (
            <>
              <div 
                className="fixed inset-0 z-10" 
                onClick={() => setIsProfileOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-56 bg-background-dark border border-glass-edge rounded-xl shadow-2xl py-2 z-20 animate-in fade-in slide-in-from-top-2">
                <div className="px-4 py-3 border-b border-glass-edge mb-1">
                  <p className="text-sm text-white font-medium truncate">{user?.full_name}</p>
                  {/* PHOENIX FIX: Correct property is user.email */}
                  <p className="text-xs text-text-secondary truncate">{user?.email}</p>
                </div>

                {user?.role === 'ADMIN' && (
                  <Link 
                    to="/dashboard" 
                    className="flex items-center px-4 py-2 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors"
                    onClick={() => setIsProfileOpen(false)}
                  >
                    <Shield size={16} className="mr-3 text-purple-400" />
                    {t('sidebar.admin', 'Admin Panel')}
                  </Link>
                )}

                <Link 
                  to="/business" 
                  className="flex items-center px-4 py-2 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors"
                  onClick={() => setIsProfileOpen(false)}
                >
                  <UserIcon size={16} className="mr-3 text-blue-400" />
                  {t('header.profile', 'Profili')}
                </Link>

                <Link 
                  to="/settings" 
                  className="flex items-center px-4 py-2 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors"
                  onClick={() => setIsProfileOpen(false)}
                >
                  <Settings size={16} className="mr-3 text-gray-400" />
                  {t('header.settings', 'Cilësimet')}
                </Link>

                <div className="h-px bg-glass-edge my-1"></div>

                <button
                  onClick={logout}
                  className="w-full flex items-center px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  <LogOut size={16} className="mr-3" />
                  {t('header.logout', 'Dilni')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;