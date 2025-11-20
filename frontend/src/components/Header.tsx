// FILE: src/components/Header.tsx
// PHOENIX PROTOCOL - UX IMPROVEMENT
// 1. ADDED: Click-outside handler (useRef + useEffect) to auto-close the profile menu.
// 2. REFACTOR: Attached reference to the profile container.

import React, { useState, useMemo, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Scale, User, LogOut, Menu, X } from 'lucide-react'; 
import { motion, AnimatePresence } from 'framer-motion'; 

const MotionLink = motion(Link);

const Header: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false); 
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false); 
  
  // Ref for the dropdown container
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProfileMenuOpen(false);
      }
    };

    if (isProfileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isProfileMenuOpen]);

  const navItems = useMemo(() => {
    const items = [
      { name: t('general.dashboard'), path: '/dashboard' },
      { name: t('general.drafting'), path: '/drafting' },
    ];
    if (user) {
      items.push({ name: t('general.calendar'), path: '/calendar' });
    }
    if (user?.role === 'ADMIN') {
      items.push({ name: t('general.admin'), path: '/admin' });
    }
    return items;
  }, [t, user]);

  const handleLanguageChange = (lng: string) => { i18n.changeLanguage(lng); setIsProfileMenuOpen(false); };
  const isActive = (path: string) => location.pathname.startsWith(path);
  
  const handleLogout = () => { 
      setIsProfileMenuOpen(false); 
      logout(); 
      navigate('/auth'); 
  };

  const NavLink = ({ item, isMobile = false }: { item: { name: string, path: string }, isMobile?: boolean }) => (
    <MotionLink
      key={item.path}
      to={item.path}
      onClick={() => isMobile && setIsMobileNavOpen(false)}
      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 w-full text-left ${
        isActive(item.path)
          ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg glow-primary'
          : 'text-text-secondary hover:text-text-primary hover:bg-background-light/30'
      } ${isMobile ? 'block' : ''}`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
    >
      {item.name}
    </MotionLink>
  );

  return (
    <header className="bg-background-light/50 backdrop-blur-md border-b border-glass-edge shadow-md glow-secondary/10 sticky top-0 z-30">
      <div className="container mx-auto px-3 sm:px-6 lg:px-8 py-3 flex justify-between items-center">
        <Link to="/dashboard" className="flex items-center space-x-2 sm:space-x-3 flex-shrink-0">
          <Scale className="h-6 w-6 sm:h-7 sm:w-7 text-text-primary" /> 
          <span className="text-lg sm:text-xl font-bold text-text-primary whitespace-nowrap">Advocatus AI</span>
        </Link>

        <nav className="hidden md:flex items-center space-x-1">
          {navItems.map((item) => <NavLink key={item.path} item={item} />)}
        </nav>

        <div className="flex items-center space-x-2 sm:space-x-4">
          <div className="hidden sm:flex items-center space-x-1 text-sm font-medium p-1 rounded-xl bg-background-dark/50 border border-glass-edge/50">
            <motion.button onClick={() => handleLanguageChange('en')} className={`px-2 py-1 rounded-lg transition-colors ${i18n.language === 'en' ? 'bg-primary-start text-white shadow-md' : 'text-text-secondary hover:text-text-primary'}`} whileHover={{ scale: 1.05 }}>EN</motion.button>
            <motion.button onClick={() => handleLanguageChange('al')} className={`px-2 py-1 rounded-lg transition-colors ${i18n.language === 'al' ? 'bg-primary-start text-white shadow-md' : 'text-text-secondary hover:text-text-primary'}`} whileHover={{ scale: 1.05 }}>AL</motion.button>
          </div>

          {/* Dropdown Container with Ref */}
          <div className="relative z-40" ref={dropdownRef}>
            <button onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)} className="flex items-center justify-center h-9 w-9 sm:h-10 sm:w-10 rounded-full bg-gradient-to-r from-primary-start to-primary-end text-white font-semibold focus:outline-none glow-primary shadow-xl">
              {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
            </button>
            <AnimatePresence>
              {isProfileMenuOpen && (
                <motion.div className="absolute right-0 mt-2 w-48 bg-background-light/85 backdrop-blur-md border border-glass-edge rounded-xl shadow-2xl py-1 z-50" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                  <div className="block px-4 py-2 text-sm text-text-primary border-b border-glass-edge/50">{user?.username || t('general.userProfile')}</div>
                  
                  <div className="sm:hidden px-4 py-2 border-b border-glass-edge/50 flex justify-between">
                     <span className="text-sm text-text-secondary">Language</span>
                     <div className="flex space-x-2">
                        <button onClick={() => handleLanguageChange('en')} className={`font-bold ${i18n.language === 'en' ? 'text-primary-start' : 'text-gray-500'}`}>EN</button>
                        <button onClick={() => handleLanguageChange('al')} className={`font-bold ${i18n.language === 'al' ? 'text-primary-start' : 'text-gray-500'}`}>AL</button>
                     </div>
                  </div>

                  <MotionLink to="/account" onClick={() => setIsProfileMenuOpen(false)} className="flex items-center w-full px-4 py-2 text-sm text-text-secondary hover:bg-background-dark/50 hover:text-text-primary transition-colors"><User className="h-4 w-4 mr-3" />{t('accountPage.pageTitle')}</MotionLink>
                  <div className="border-t border-glass-edge/50 py-1"><button onClick={handleLogout} className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-700/80 hover:text-white flex items-center transition-colors"><LogOut className="h-4 w-4 mr-3" />{t('general.logout')}</button></div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <button className="md:hidden text-text-primary p-1" onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}>{isMobileNavOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}</button>
        </div>
      </div>
      
      <AnimatePresence>
        {isMobileNavOpen && (
          <motion.div className="md:hidden px-4 pb-4 space-y-2 bg-background-light/85 backdrop-blur-md border-t border-glass-edge/50" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.2 }}>
            {navItems.map((item) => <NavLink key={item.path} item={item} isMobile={true} />)}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

export default Header;