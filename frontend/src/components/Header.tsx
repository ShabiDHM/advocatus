// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL – 100% SOLID OPAQUE HEADER V16.0 (STRICT ADMIN-ONLY DRAFTING & NAVIGATION)

import React, { useState, useEffect, useRef } from 'react';
import { 
    Bell, LogOut, User as UserIcon, MessageSquare, Shield, Scale, FileText, Building2, Menu, X, BookOpen, Sun, Moon 
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import BrandLogo from './BrandLogo';

const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  const isAdmin = user?.role === 'ADMIN';

  // 1. LISTA BAZË E NAVIGIMIT PËR TË GJITHË PËRDORUESIT (PA HARTIM)
  const navItems = [
    { icon: Building2, label: t('sidebar.myOffice', 'Zyra'), path: '/business' },
    { icon: Scale, label: t('sidebar.juristiAi', 'Rastet'), path: '/dashboard' },
    { icon: BookOpen, label: t('sidebar.lawLibrary', 'Biblioteka Ligjore'), path: '/laws/search' },
  ];
  
  // 2. VETËM NËSE PËRDORUESI ËSHTË SUPER ADMIN SHTOHEN ADMIN & HARTIMI
  if (isAdmin) {
    navItems.splice(1, 0, {
      icon: Shield,
      label: t('sidebar.adminPanel', 'Admin'),
      path: '/admin',
    });
    navItems.push({
      icon: FileText,
      label: t('sidebar.drafting', 'Hartimi'),
      path: '/drafting',
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
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsMobileMenuOpen(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        isMobileMenuOpen &&
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(event.target as Node) &&
        !(event.target as HTMLElement).closest('.mobile-menu-button')
      ) {
        setIsMobileMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
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
    const handleClickOutsideProfile = (event: MouseEvent) => {
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
    document.addEventListener('mousedown', handleClickOutsideProfile);
    return () => document.removeEventListener('mousedown', handleClickOutsideProfile);
  }, [isProfileOpen]);

  const isActive = (path: string) => {
    if (path === '/business') {
      return location.pathname.startsWith('/business');
    }
    return location.pathname === path;
  };

  return (
    <>
      {/* 100% OPAQUE SOLID HEADER */}
      <header 
        className="fixed top-0 left-0 right-0 z-[60] flex items-center justify-between px-3 sm:px-6 md:px-8 py-2.5 sm:py-3 border-b border-main shadow-sm transition-colors duration-200"
        style={{
          backgroundColor: theme === 'dark' ? '#020617' : '#F4F6F9',
          opacity: 1
        }}
      >
        {/* Left: Brand */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <button 
            onClick={() => setIsMobileMenuOpen(true)} 
            className="mobile-menu-button p-2 text-text-primary lg:hidden hover:bg-hover rounded-xl transition-colors focus:outline-none cursor-pointer"
            aria-label={t('header.menu', 'Menu')}
          >
            <Menu size={22} />
          </button>
          <Link to="/business" className="flex items-center">
            <BrandLogo />
          </Link>
        </div>

        {/* Center: Segmented Navigation Bar (Desktop Only) */}
        <div 
          className="hidden lg:flex items-center p-1.5 rounded-2xl border border-main gap-1 shadow-xs"
          style={{ backgroundColor: theme === 'dark' ? '#0f172a' : '#FFFFFF' }}
        >
          {navItems.map((item) => {
            const active = isActive(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all duration-200
                  ${active 
                    ? 'bg-primary-start text-white shadow-md shadow-primary-start/20' 
                    : 'text-text-muted hover:text-text-primary hover:bg-hover border border-transparent'
                  }
                `}
              >
                <item.icon size={16} />
                <span className="hidden xl:inline">{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          <button 
            onClick={toggleTheme} 
            className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none cursor-pointer"
            aria-label={theme === 'dark' ? t('theme.light', 'Dritë') : t('theme.dark', 'Errët')}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <Link 
            to="/calendar" 
            className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl relative transition-colors focus:outline-none"
          >
            <Bell size={18} />
            {alertCount > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full animate-pulse"></span>
            )}
          </Link>

          {/* User profile */}
          <div className="relative hidden sm:block">
            <button
              ref={buttonRef}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="flex items-center gap-2 p-1 rounded-full border border-main hover:border-primary-start/40 transition-all shadow-xs focus:outline-none cursor-pointer"
              style={{ backgroundColor: theme === 'dark' ? '#0f172a' : '#FFFFFF' }}
            >
              <div className="h-8 w-8 rounded-full bg-primary-start text-white flex items-center justify-center text-xs font-black">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
            </button>

            {isProfileOpen && (
              <div 
                ref={dropdownRef} 
                className="absolute right-0 mt-2 w-56 border border-main rounded-2xl shadow-2xl py-2 z-[70] text-text-primary"
                style={{ backgroundColor: theme === 'dark' ? '#0f172a' : '#FFFFFF' }}
              >
                <div className="px-4 py-2.5 border-b border-main mb-1">
                  <p className="text-sm font-bold text-text-primary truncate">{user?.username}</p>
                  <p className="text-xs text-text-muted truncate">{user?.email}</p>
                </div>

                <button 
                  onClick={() => { setIsProfileOpen(false); navigate('/account'); }} 
                  className="w-full text-left flex items-center px-4 py-2.5 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-hover transition-colors cursor-pointer"
                >
                  <UserIcon size={16} className="mr-3 text-primary-start" />{t('sidebar.account', 'Llogaria')}
                </button>
                <button 
                  onClick={() => { setIsProfileOpen(false); navigate('/support'); }} 
                  className="w-full text-left flex items-center px-4 py-2.5 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-hover transition-colors cursor-pointer"
                >
                  <MessageSquare size={16} className="mr-3 text-primary-start" />{t('sidebar.support', 'Ndihma')}
                </button>
                <div className="h-px bg-border-main my-1"></div>
                <button 
                  onClick={() => { setIsProfileOpen(false); logout(); }} 
                  className="w-full flex items-center px-4 py-2.5 text-sm font-bold text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                >
                  <LogOut size={16} className="mr-3" />{t('general.logout', 'Dilni')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      <div
        className={`fixed inset-0 z-[70] transition-all duration-300 ease-in-out ${
          isMobileMenuOpen ? 'pointer-events-auto' : 'pointer-events-none'
        }`}
      >
        <div
          className={`absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
            isMobileMenuOpen ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={() => setIsMobileMenuOpen(false)}
        />
        
        <div
          ref={mobileMenuRef}
          className={`absolute top-0 left-0 bottom-0 w-72 max-w-[85vw] rounded-r-3xl border-y border-r border-main shadow-2xl transition-transform duration-300 ease-in-out ${
            isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
          } flex flex-col`}
          style={{ backgroundColor: theme === 'dark' ? '#0f172a' : '#FFFFFF' }}
        >
          <div className="flex justify-between items-center p-4 border-b border-main">
            <BrandLogo />
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors focus:outline-none cursor-pointer"
              aria-label={t('general.close', 'Mbyll')}
            >
              <X size={22} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-6 px-4 space-y-2">
            {navItems.map((item) => {
              const active = isActive(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`
                    flex items-center gap-4 px-4 py-3 rounded-2xl text-sm font-black uppercase tracking-widest transition-all duration-200
                    ${active 
                      ? 'bg-primary-start text-white shadow-md shadow-primary-start/20' 
                      : 'text-text-muted hover:text-text-primary hover:bg-hover'
                    }
                  `}
                >
                  <item.icon size={20} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>

          <div className="p-4 border-t border-main">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-10 w-10 rounded-full bg-primary-start text-white flex items-center justify-center text-sm font-black">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-text-primary truncate">{user?.username || t('header.guest', 'Mysafir')}</p>
                <p className="text-xs text-text-muted truncate">{user?.email || ''}</p>
              </div>
            </div>
            <button
              onClick={() => { setIsMobileMenuOpen(false); logout(); }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition-colors text-xs font-black uppercase tracking-widest cursor-pointer"
            >
              <LogOut size={16} />
              {t('general.logout', 'Dilni')}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Header;