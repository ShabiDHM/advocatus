// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - HEADER V6.3 (LAW LIBRARY FOR ALL USERS)
// 1. MODIFIED: Law Library link is now visible to all authenticated users.
// 2. RETAINED: Admin Panel link remains restricted to admin role.
// 3. STATUS: All users can access legal database.

import React, { useState, useEffect, useRef } from 'react';
import { Bell, Search, LogOut, User as UserIcon, MessageSquare, Shield, Scale, FileText, Building2, Menu, X, BookOpen } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { apiService } from '../services/api';
import LanguageSwitcher from './LanguageSwitcher';
import BrandLogo from './BrandLogo';

const Header: React.FC = () => {
  const { user, logout } = useAuth();
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
    // Law Library – now visible to everyone
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
      <header className="h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8 z-40 top-0 backdrop-blur-xl bg-background-dark/60 border-b border-white/5 transition-all duration-300">
        
        <div className="flex items-center h-full gap-4 lg:gap-8">
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden p-2 text-text-secondary hover:text-white transition-colors"
            aria-label="Toggle navigation menu"
          >
            <Menu size={24} />
          </button>
          
          <BrandLogo />
          
          <div className="relative hidden sm:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary h-4 w-4" />
            <input 
              type="text" 
              placeholder={t('general.search', 'Kërko...')} 
              className="bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder-text-secondary/50 focus:ring-1 focus:ring-primary-start/50 focus:bg-background-dark/80 focus:border-primary-start/50 outline-none w-64 transition-all focus:w-80"
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
                className={`flex items-center px-4 h-full text-sm font-medium transition-all duration-200 relative ${isCurrentActive ? 'text-white border-b-2 border-primary-start' : 'text-text-secondary hover:text-white hover:bg-white/5'}`}
              >
                <item.icon className="h-4 w-4 mr-2" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <div className="hidden">
            <LanguageSwitcher />
          </div>

          <Link to="/calendar" className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-lg transition-colors relative" title="Kalendari">
            <Bell size={20} />
            {alertCount > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            )}
          </Link>
          
          <div className="h-6 w-px bg-white/10"></div>

          <div className="relative">
            <button 
              ref={buttonRef}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className={`flex items-center gap-3 p-1.5 rounded-xl transition-all border ${isProfileOpen ? 'bg-white/10 border-white/10' : 'border-transparent hover:bg-white/5 hover:border-white/5'}`}
            >
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-white">{user?.username || 'User'}</p>
                <p className="text-xs text-text-secondary uppercase tracking-wider">{user?.role || 'LAWYER'}</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-secondary-start to-secondary-end flex items-center justify-center text-white font-bold shadow-lg shadow-secondary-start/20">
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
                <Link to="/account" className="flex items-center px-4 py-2.5 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <UserIcon size={16} className="mr-3 text-primary-start" />
                  {t('sidebar.account', 'Llogaria Ime')}
                </Link>
                <Link to="/support" className="flex items-center px-4 py-2.5 text-sm text-text-secondary hover:text-white hover:bg-white/5 transition-colors" onClick={() => setIsProfileOpen(false)}>
                  <MessageSquare size={16} className="mr-3 text-primary-start" />
                  {t('sidebar.support', 'Mbështetja')}
                </Link>
                <div className="h-px bg-white/5 my-1"></div>
                <button onClick={() => { setIsProfileOpen(false); logout(); }} className="w-full flex items-center px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors">
                  <LogOut size={16} className="mr-3" />
                  {t('general.logout', 'Dilni')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-0 bg-background-dark/95 backdrop-blur-xl z-50 animate-in fade-in">
          <div className="flex items-center justify-between h-16 px-4 border-b border-white/10">
            <BrandLogo />
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="p-2 text-text-secondary hover:text-white transition-colors"
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
                  className={`flex items-center px-4 py-3 text-base font-medium rounded-lg transition-all duration-200 ${isCurrentActive ? 'text-white bg-white/10' : 'text-text-secondary hover:text-white hover:bg-white/5'}`}
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