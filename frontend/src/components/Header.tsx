// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - HEADER V7.0 (SEMANTIC DESIGN SYSTEM)
// 1. UPDATED: Uses new semantic color classes: canvas, surface, text-primary, border-main, etc.
// 2. RETAINED: Theme toggle, alerts, profile dropdown.

import React, { useState, useEffect, useRef } from 'react';
import { Bell, Search, LogOut, User as UserIcon, MessageSquare, Shield, Scale, FileText, Building2, Menu, X, BookOpen, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { apiService } from '../services/api';
import LanguageSwitcher from './LanguageSwitcher';
import BrandLogo from './BrandLogo';

const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t } = useTranslation();
  const location = useLocation();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // BASE NAVIGATION (Visible to all authenticated users)
  const navItems = [
    { icon: Building2, label: t('sidebar.myOffice', 'Zyra'), path: '/business' },
    { icon: Scale, label: t('sidebar.juristiAi', 'Rastet'), path: '/dashboard' },
    { icon: FileText, label: t('sidebar.drafting', 'Hartimi'), path: '/drafting' },
    { icon: BookOpen, label: t('sidebar.lawLibrary', 'Biblioteka Ligjore'), path: '/laws/search' },
  ];
  
  // ADMIN-ONLY: Insert Admin Panel link at index 1 (after Zyra)
  if (user?.role === 'ADMIN') {
      navItems.splice(1, 0, {
          icon: Shield,
          label: t('sidebar.adminPanel', 'Admin'),
          path: '/admin',
      });
  }

  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isMobileMenuOpen]);

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

  const handleMobileLinkClick = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      <header className="h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 z-40 top-0 backdrop-blur-xl bg-surface/60 border-b border-main transition-all duration-300">
        
        <div className="flex items-center h-full gap-4 lg:gap-8">
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden p-2 text-text-secondary hover:text-text-primary transition-colors"
            aria-label="Toggle navigation menu"
          >
            <Menu size={24} />
          </button>
          
          <BrandLogo />
          
          <div className="relative hidden sm:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-4 w-4" />
            <input 
              type="text" 
              placeholder={t('general.search', 'Kërko...')} 
              className="glass-input w-64 focus:w-80"
            />
          </div>
        </div>

        <nav className="hidden lg:flex items-center h-full space-x-2">
          {navItems.map((item) => {
            const isCurrentActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 h-full text-sm font-medium transition-all duration-200 relative ${isCurrentActive ? 'text-text-primary border-b-2 border-primary-start' : 'text-text-secondary hover:text-text-primary hover:bg-surface/10'}`}
              >
                <item.icon className="h-4 w-4 mr-2" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface/10 rounded-lg transition-colors"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          <div className="hidden">
            <LanguageSwitcher />
          </div>

          <Link to="/calendar" className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface/10 rounded-lg transition-colors relative" title="Kalendari">
            <Bell size={20} />
            {alertCount > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-danger-start rounded-full animate-pulse"></span>
            )}
          </Link>
          
          <div className="h-6 w-px bg-main"></div>

          <div className="relative">
            <button 
              ref={buttonRef}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className={`flex items-center gap-3 p-1.5 rounded-xl transition-all border ${isProfileOpen ? 'bg-surface/10 border-main' : 'border-transparent hover:bg-surface/10 hover:border-main'}`}
            >
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-text-primary">{user?.username || 'User'}</p>
                <p className="text-xs text-text-secondary uppercase tracking-wider">{user?.role || 'LAWYER'}</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-white font-bold shadow-accent-glow">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
            </button>

            {isProfileOpen && (
              <div 
                ref={dropdownRef}
                className="absolute right-0 mt-2 w-60 bg-surface/90 backdrop-blur-xl border border-main rounded-xl shadow-xl py-2 z-50 animate-in fade-in slide-in-from-top-2"
              >
                <div className="px-4 py-3 border-b border-main mb-1 bg-surface/5">
                  <p className="text-sm text-text-primary font-medium truncate">{user?.username}</p>
                  <p className="text-xs text-text-secondary truncate">{user?.email}</p>
                </div>
                <Link to="/account" className="flex items-center px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-surface/10 transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <UserIcon size={16} className="mr-3 text-primary-start" />
                  {t('sidebar.account', 'Llogaria Ime')}
                </Link>
                <Link to="/support" className="flex items-center px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-surface/10 transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <MessageSquare size={16} className="mr-3 text-primary-start" />
                  {t('sidebar.support', 'Mbështetja')}
                </Link>
                <div className="h-px bg-main my-1"></div>
                <button onClick={() => { setIsProfileOpen(false); logout(); }} className="w-full flex items-center px-4 py-2.5 text-sm text-danger-start hover:bg-danger-start/10 hover:text-danger-start transition-colors">
                  <LogOut size={16} className="mr-3" />
                  {t('general.logout', 'Dilni')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-0 bg-surface/95 backdrop-blur-xl z-50 animate-in fade-in">
          <div className="flex items-center justify-between h-16 px-4 border-b border-main">
            <BrandLogo />
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="p-2 text-text-secondary hover:text-text-primary transition-colors"
              aria-label="Close navigation menu"
            >
              <X size={24} />
            </button>
          </div>
          <nav className="flex flex-col p-4 space-y-2 mt-4">
            {navItems.map((item) => {
              const isCurrentActive = location.pathname.startsWith(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={handleMobileLinkClick}
                  className={`flex items-center px-4 py-3 text-base font-medium rounded-lg transition-all duration-200 ${isCurrentActive ? 'text-text-primary bg-surface/10' : 'text-text-secondary hover:text-text-primary hover:bg-surface/10'}`}
                >
                  <item.icon className="h-5 w-5 mr-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </div>
      )}
    </>
  );
};

export default Header;