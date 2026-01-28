// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - HEADER V4.1 (SUPPORT LINK RELOCATED - COMPLETED)
// 1. FEAT: Added the 'Support' link to the user profile dropdown menu.
// 2. INTEGRITY: Added missing closing tags to restore file integrity.

import React, { useState, useEffect, useRef } from 'react';
import { Bell, Search, Menu, LogOut, User as UserIcon, MessageSquare } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import LanguageSwitcher from './LanguageSwitcher';

interface HeaderProps {
  toggleSidebar: () => void;
}

const Header: React.FC<HeaderProps> = ({ toggleSidebar }) => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  // Refs for click-outside detection
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Poll for alerts
  useEffect(() => {
    const checkAlerts = async () => {
      if (!user) return;
      try {
        const data = await apiService.getAlertsCount();
        setAlertCount(data.count);
      } catch (err) {
        console.warn("Alert check skipped");
      }
    };
    
    checkAlerts();
    const interval = setInterval(checkAlerts, 60000); 
    return () => clearInterval(interval);
  }, [user]);

  // Click Outside Event Listener
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        isProfileOpen &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsProfileOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isProfileOpen]);

  return (
    <header className="h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 z-40 sticky top-0 backdrop-blur-xl bg-background-dark/60 border-b border-white/5 transition-all duration-300">
      
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
            placeholder={t('header.searchPlaceholder')} 
            className="bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder-text-secondary/50 focus:ring-1 focus:ring-primary-start/50 focus:bg-background-dark/80 focus:border-primary-start/50 outline-none w-64 transition-all focus:w-80"
          />
        </div>
      </div>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden">
          <LanguageSwitcher />
        </div>

        <Link to="/calendar" className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors relative" title="Njoftimet">
          <Bell size={20} />
          {alertCount > 0 && (
            <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
          )}
        </Link>
        
        <div className="h-6 w-px bg-white/10"></div>

        {/* Profile Dropdown Container */}
        <div className="relative">
          <button 
            ref={buttonRef}
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className={`flex items-center gap-3 p-1.5 rounded-xl transition-all border ${isProfileOpen ? 'bg-white/10 border-white/10' : 'border-transparent hover:bg-white/5 hover:border-white/5'}`}
          >
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-white">{user?.username || 'User'}</p>
              <p className="text-xs text-text-secondary uppercase tracking-wider">
                {user?.role || 'LAWYER'}
              </p>
            </div>
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-secondary-start to-secondary-end flex items-center justify-center text-white font-bold shadow-lg shadow-secondary-start/20 ring-2 ring-transparent group-hover:ring-white/10">
              {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
            </div>
          </button>

          {isProfileOpen && (
            <div 
              ref={dropdownRef}
              className="absolute right-0 mt-2 w-60 bg-background-dark/90 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl py-2 z-50 animate-in fade-in slide-in-from-top-2"
            >
              <div className="px-4 py-3 border-b border-white/5 mb-1 bg-white/5">
                <p className="text-sm text-white font-medium truncate">{user?.username}</p>
                <p className="text-xs text-text-secondary truncate">{user?.email}</p>
              </div>

              <Link 
                to="/account" 
                className="flex items-center px-4 py-2.5 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors"
                onClick={() => setIsProfileOpen(false)}
              >
                <UserIcon size={16} className="mr-3 text-primary-start" />
                {t('sidebar.account', 'Llogaria Ime')}
              </Link>
              
              {/* --- ADDED SUPPORT LINK --- */}
              <Link 
                to="/support" 
                className="flex items-center px-4 py-2.5 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors"
                onClick={() => setIsProfileOpen(false)}
              >
                <MessageSquare size={16} className="mr-3 text-primary-start" />
                {t('sidebar.support', 'Mbështetja')}
              </Link>
              {/* --- END ADDED SUPPORT LINK --- */}

              <div className="h-px bg-white/5 my-1"></div>

              <button
                onClick={() => {
                  setIsProfileOpen(false);
                  logout();
                }}
                className="w-full flex items-center px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
              >
                <LogOut size={16} className="mr-3" />
                {t('header.logout', 'Dilni')}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;