// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - HEADER V7.0 (DEFINITIVE FULL VERSION)
// 1. REPLACED: Generic glassmorphism with solid "Lawyer-Grade" surface architecture.
// 2. RETAINED: 100% of original logic, auth checks, admin routing, and alert intervals.
// 3. ENHANCED: Professional spacing, typography hierarchy, and theme-toggle animation.

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

  // BASE NAVIGATION (Exactly as original)
  const navItems = [
    { icon: Building2, label: t('sidebar.myOffice', 'Zyra'), path: '/business' },
    { icon: Scale, label: t('sidebar.juristiAi', 'Rastet'), path: '/dashboard' },
    { icon: FileText, label: t('sidebar.drafting', 'Hartimi'), path: '/drafting' },
    { icon: BookOpen, label: t('sidebar.lawLibrary', 'Biblioteka Ligjore'), path: '/laws/search' },
  ];
  
  // ADMIN-ONLY: Insert Admin Panel link (Exactly as original)
  if (user?.role === 'ADMIN') {
      navItems.splice(1, 0, {
          icon: Shield,
          label: t('sidebar.adminPanel', 'Admin'),
          path: '/admin',
      });
  }

  // Effect: Body Overflow (Exactly as original)
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

  // Effect: Alerts Count (Exactly as original)
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

  // Effect: Outside Click (Exactly as original)
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
      {/* Container: Fixed position to allow full page scroll while maintaining accessibility */}
      <header className="fixed top-0 left-0 right-0 h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 z-50 bg-surface border-b border-surface-border shadow-lawyer-light transition-all duration-300">
        
        <div className="flex items-center h-full gap-4 lg:gap-10">
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden p-2 text-text-secondary hover:text-text-primary hover:bg-canvas rounded-lg transition-colors"
            aria-label="Toggle navigation menu"
          >
            <Menu size={24} />
          </button>
          
          <BrandLogo />
          
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary h-4 w-4" />
            <input 
              type="text" 
              placeholder={t('general.search', 'Kërko...')} 
              className="glass-input w-64 pl-10 pr-4 py-2 text-sm focus:w-80 border-surface-border bg-canvas/40 font-medium transition-all"
            />
          </div>
        </div>

        <nav className="hidden lg:flex items-center h-full space-x-1">
          {navItems.map((item) => {
            const isCurrentActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 h-full text-sm font-bold transition-all duration-200 relative group ${
                  isCurrentActive 
                    ? 'text-text-primary' 
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <item.icon className={`h-4 w-4 mr-2.5 transition-colors ${isCurrentActive ? 'text-primary-start' : 'group-hover:text-primary-start'}`} />
                {item.label}
                {isCurrentActive && (
                  <span className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-start rounded-t-full shadow-[0_-2px_4px_rgba(var(--color-primary-start-rgb),0.3)]" />
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 sm:gap-4">
          {/* Theme Toggle Button - Animated and Polished */}
          <button
            onClick={toggleTheme}
            className="p-2.5 text-text-secondary hover:text-primary-start border border-surface-border bg-canvas/30 hover:bg-canvas rounded-xl transition-all shadow-lawyer-light"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? (
              <Sun size={19} className="animate-in spin-in-90 duration-300" />
            ) : (
              <Moon size={19} className="animate-in spin-in-45 duration-300" />
            )}
          </button>

          {/* Preserving hidden div exactly as original */}
          <div className="hidden">
            <LanguageSwitcher />
          </div>

          <Link 
            to="/calendar" 
            className="p-2.5 text-text-secondary hover:text-primary-start border border-surface-border bg-canvas/30 hover:bg-canvas rounded-xl transition-all relative shadow-lawyer-light" 
            title="Kalendari"
          >
            <Bell size={19} />
            {alertCount > 0 && (
              <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-surface animate-pulse"></span>
            )}
          </Link>
          
          <div className="h-8 w-px bg-surface-border mx-1"></div>

          <div className="relative">
            <button 
              ref={buttonRef}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className={`flex items-center gap-3 p-1 rounded-full transition-all border ${
                isProfileOpen 
                ? 'bg-canvas border-primary-start/30 ring-4 ring-primary-start/5' 
                : 'border-surface-border hover:border-primary-start/20 hover:bg-canvas/50'
              }`}
            >
              <div className="text-right hidden lg:block pl-3">
                <p className="text-sm font-bold text-text-primary leading-tight">{user?.username || 'User'}</p>
                <p className="text-[10px] text-text-secondary font-bold uppercase tracking-widest">{user?.role || 'LAWYER'}</p>
              </div>
              <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-white font-black text-sm shadow-md ring-2 ring-surface">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
            </button>

            {isProfileOpen && (
              <div 
                ref={dropdownRef}
                className="absolute right-0 mt-3 w-64 bg-surface border border-surface-border rounded-2xl shadow-lawyer-dark py-2 z-[60] animate-in fade-in slide-in-from-top-3 duration-200"
              >
                <div className="px-5 py-4 border-b border-surface-border mb-2 bg-canvas/30">
                  <p className="text-sm text-text-primary font-bold truncate leading-tight">{user?.username}</p>
                  <p className="text-xs text-text-secondary truncate mt-0.5">{user?.email}</p>
                </div>
                
                <Link to="/account" className="flex items-center px-5 py-3 text-sm text-text-secondary font-medium hover:text-text-primary hover:bg-canvas transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <UserIcon size={16} className="mr-3.5 text-primary-start" />
                  {t('sidebar.account', 'Llogaria Ime')}
                </Link>
                
                <Link to="/support" className="flex items-center px-5 py-3 text-sm text-text-secondary font-medium hover:text-text-primary hover:bg-canvas transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <MessageSquare size={16} className="mr-3.5 text-primary-start" />
                  {t('sidebar.support', 'Mbështetja')}
                </Link>
                
                <div className="h-px bg-surface-border my-2 mx-4"></div>
                
                <button 
                  onClick={() => { setIsProfileOpen(false); logout(); }} 
                  className="w-full flex items-center px-5 py-3 text-sm font-bold text-red-500 hover:bg-red-50 transition-colors"
                >
                  <LogOut size={16} className="mr-3.5" />
                  {t('general.logout', 'Dilni')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* MOBILE MENU: Preserved 100% logic with upgraded visuals */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 bg-canvas z-[70] animate-in fade-in duration-300">
          <div className="flex items-center justify-between h-16 px-6 border-b border-surface-border bg-surface">
            <BrandLogo />
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="p-2 text-text-secondary hover:text-text-primary bg-canvas rounded-lg transition-colors"
              aria-label="Close navigation menu"
            >
              <X size={28} />
            </button>
          </div>
          <nav className="flex flex-col p-6 space-y-3 mt-6">
            {navItems.map((item) => {
              const isCurrentActive = location.pathname.startsWith(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={handleMobileLinkClick}
                  className={`flex items-center px-5 py-4 text-lg font-bold rounded-2xl transition-all ${
                    isCurrentActive 
                      ? 'text-primary-start bg-primary-start/10 shadow-sm' 
                      : 'text-text-secondary hover:text-text-primary hover:bg-canvas'
                  }`}
                >
                  <item.icon className={`h-6 w-6 mr-5 ${isCurrentActive ? 'text-primary-start' : 'text-text-secondary'}`} />
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