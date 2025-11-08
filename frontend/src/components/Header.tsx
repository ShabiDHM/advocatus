// FILE: /home/user/advocatus-frontend/src/components/Header.tsx
// DEFINITIVE VERSION 12.9 (UI CONSISTENCY):
// 1. Integrated the 'Admin' link into the primary navItems array for consistent styling.
// 2. Updated the 'Admin' link to use a simpler translation key ('general.admin').

import React, { useState, useMemo } from 'react';
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

  const navItems = useMemo(() => {
    const items = [
      { name: t('general.dashboard'), path: '/dashboard' },
      { name: t('general.drafting'), path: '/drafting' },
    ];
    if (user) {
      items.push({ name: t('general.calendar'), path: '/calendar' });
    }
    // PHOENIX PROTOCOL FIX: Conditionally add Admin link to the main array
    if (user?.role === 'ADMIN') {
      items.push({ name: t('general.admin'), path: '/admin' });
    }
    return items;
  }, [t, user]);

  const handleLanguageChange = (lng: string) => { i18n.changeLanguage(lng); setIsProfileMenuOpen(false); };
  const isActive = (path: string) => location.pathname.startsWith(path);
  const handleLogout = () => { logout(); navigate('/auth'); };

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
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-between items-center">
        <Link to="/dashboard" className="flex items-center space-x-3">
          <Scale className="h-7 w-7 text-text-primary" /> 
          <span className="text-xl font-bold text-text-primary hidden sm:block">Advocatus AI</span>
        </Link>

        {/* PHOENIX PROTOCOL FIX: Simplified nav rendering */}
        <nav className="hidden md:flex items-center space-x-1">
          {navItems.map((item) => <NavLink key={item.path} item={item} />)}
        </nav>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1 text-sm font-medium p-1 rounded-xl bg-background-dark/50 border border-glass-edge/50">
            <motion.button onClick={() => handleLanguageChange('en')} className={`px-2 py-1 rounded-lg transition-colors ${i18n.language === 'en' ? 'bg-primary-start text-white shadow-md' : 'text-text-secondary hover:text-text-primary'}`} whileHover={{ scale: 1.05 }}>EN</motion.button>
            <motion.button onClick={() => handleLanguageChange('al')} className={`px-2 py-1 rounded-lg transition-colors ${i18n.language === 'al' ? 'bg-primary-start text-white shadow-md' : 'text-text-secondary hover:text-text-primary'}`} whileHover={{ scale: 1.05 }}>AL</motion.button>
          </div>

          <div className="relative z-40">
            <button onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)} className="flex items-center justify-center h-10 w-10 rounded-full bg-gradient-to-r from-primary-start to-primary-end text-white font-semibold focus:outline-none glow-primary shadow-xl">
              {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
            </button>
            <AnimatePresence>
              {isProfileMenuOpen && (
                <motion.div className="absolute right-0 mt-2 w-48 bg-background-light/85 backdrop-blur-md border border-glass-edge rounded-xl shadow-2xl py-1 z-50" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                  <div className="block px-4 py-2 text-sm text-text-primary border-b border-glass-edge/50">{user?.username || t('general.userProfile')}</div>
                  <MotionLink to="/account" onClick={() => setIsProfileMenuOpen(false)} className="flex items-center w-full px-4 py-2 text-sm text-text-secondary hover:bg-background-dark/50 hover:text-text-primary transition-colors"><User className="h-4 w-4 mr-3" />{t('accountPage.pageTitle')}</MotionLink>
                  <div className="border-t border-glass-edge/50 py-1"><button onClick={handleLogout} className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-700/80 hover:text-white flex items-center transition-colors"><LogOut className="h-4 w-4 mr-3" />{t('general.logout')}</button></div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <button className="md:hidden text-text-primary" onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}>{isMobileNavOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}</button>
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