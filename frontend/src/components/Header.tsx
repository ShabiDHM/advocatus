// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - HEADER V8.0 (MOBILE NAVIGATION ALIGNMENT)
// STATUS: CLEAN - VERIFIED - FULL FILE REPLACEMENT

import React, { useState, useEffect, useRef } from 'react';
import { Bell, Search, LogOut, User as UserIcon, MessageSquare, Shield, Scale, FileText, Building2, Menu, X, BookOpen, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { apiService } from '../services/api';
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

  const navItems = [
    { icon: Building2, label: t('sidebar.myOffice', 'Zyra'), path: '/business' },
    { icon: Scale, label: t('sidebar.juristiAi', 'Rastet'), path: '/dashboard' },
    { icon: FileText, label: t('sidebar.drafting', 'Hartimi'), path: '/drafting' },
    { icon: BookOpen, label: t('sidebar.lawLibrary', 'Biblioteka Ligjore'), path: '/laws/search' },
  ];
  
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
      <header className="glass-panel sticky top-0 z-40 h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 transition-all duration-300">
        
        {/* Left section: logo and search */}
        <div className="flex items-center h-full gap-4 lg:gap-8 min-w-0">
          <div className="flex-shrink-0">
            <BrandLogo />
          </div>
          
          <div className="relative hidden sm:block w-64 lg:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted h-4 w-4" />
            <input 
              type="text" 
              placeholder={t('general.search', 'Kërko...')} 
              className="glass-input w-full pl-10 pr-3 py-2 rounded-xl focus:ring-1 focus:ring-primary-start/40 transition-all"
            />
          </div>
        </div>

        {/* Desktop Nav */}
        <nav className="hidden lg:flex items-center h-full space-x-2">
          {navItems.map((item) => {
            const isCurrentActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 h-full text-sm font-medium transition-all duration-200 relative ${
                  isCurrentActive 
                    ? 'text-primary border-b-2 border-primary' 
                    : 'text-secondary hover:text-primary hover:bg-hover'
                }`}
              >
                <item.icon className="h-4 w-4 mr-2" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Right section: Utilities and Mobile Toggle */}
        <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
          
          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-secondary hover:text-primary hover:bg-hover transition-colors"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          <Link to="/calendar" className="p-2 text-secondary hover:text-primary hover:bg-hover rounded-lg transition-colors relative" title="Kalendari">
            <Bell size={20} />
            {alertCount > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-danger rounded-full animate-pulse"></span>
            )}
          </Link>
          
          <div className="h-6 w-px bg-border-main mx-1"></div>

          {/* Profile Dropdown */}
          <div className="relative">
            <button 
              ref={buttonRef}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className={`flex items-center gap-2 p-1 rounded-xl transition-all border ${
                isProfileOpen ? 'bg-hover border-border-main' : 'border-transparent hover:bg-hover hover:border-border-main'
              }`}
            >
              <div className="text-right hidden sm:block px-1">
                <p className="text-sm font-medium text-primary leading-none mb-1">{user?.username || 'User'}</p>
                <p className="text-[10px] text-secondary uppercase tracking-wider leading-none">{user?.role || 'LAWYER'}</p>
              </div>
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-primary-hover flex items-center justify-center text-white font-bold text-sm shadow-sm">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
            </button>

            {isProfileOpen && (
              <div 
                ref={dropdownRef}
                className="absolute right-0 mt-2 w-60 bg-glass backdrop-blur-xl border border-border-main rounded-xl shadow-lg py-2 z-50 animate-in fade-in slide-in-from-top-2"
              >
                <div className="px-4 py-3 border-b border-border-main mb-1 bg-hover/5">
                  <p className="text-sm text-primary font-medium truncate">{user?.username}</p>
                  <p className="text-xs text-secondary truncate">{user?.email}</p>
                </div>
                <Link to="/account" className="flex items-center px-4 py-2.5 text-sm text-secondary hover:text-primary hover:bg-hover transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <UserIcon size={16} className="mr-3 text-primary" />
                  {t('sidebar.account', 'Llogaria Ime')}
                </Link>
                <Link to="/support" className="flex items-center px-4 py-2.5 text-sm text-secondary hover:text-primary hover:bg-hover transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <MessageSquare size={16} className="mr-3 text-primary" />
                  {t('sidebar.support', 'Mbështetja')}
                </Link>
                <div className="h-px bg-border-main my-1"></div>
                <button onClick={() => { setIsProfileOpen(false); logout(); }} className="w-full flex items-center px-4 py-2.5 text-sm text-danger hover:bg-danger/10 transition-colors">
                  <LogOut size={16} className="mr-3" />
                  {t('general.logout', 'Dilni')}
                </button>
              </div>
            )}
          </div>

          {/* Mobile Menu Button - Moved to Far Right */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden p-2 text-secondary hover:text-primary hover:bg-hover rounded-lg transition-colors border border-transparent hover:border-border-main"
            aria-label="Toggle navigation menu"
          >
            <Menu size={24} />
          </button>
        </div>
      </header>

      {/* Mobile Sidebar Overlay */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-0 bg-glass backdrop-blur-xl z-50 animate-in fade-in">
          <div className="flex items-center justify-between h-16 px-4 border-b border-border-main">
            <BrandLogo />
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="p-2 text-secondary hover:text-primary transition-colors"
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
                  className={`flex items-center px-4 py-3 text-base font-medium rounded-lg transition-all duration-200 ${
                    isCurrentActive ? 'text-primary bg-hover' : 'text-secondary hover:text-primary hover:bg-hover'
                  }`}
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