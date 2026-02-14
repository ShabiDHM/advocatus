// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING V8.0 (CLEAN HERO)
// 1. MODIFIED: Removed the version badge pill (BrainCircuit + landing.versionBadge).
// 2. CLEANUP: Removed unused BrainCircuit import from lucide-react.
// 3. STATUS: Visual Alignment Complete.

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
    ArrowRight, Lock, Globe, ChevronRight, 
    MessageSquare, Zap, TrendingUp, Database, FileText 
} from 'lucide-react';
import { motion } from 'framer-motion';
import BrandLogo from '../components/BrandLogo';
import ProductShowcase from '../components/landing/ProductShowcase';

const LandingPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-[#0B0F19] text-white overflow-hidden relative selection:bg-primary-start/30 font-sans">
      
      {/* Background Gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[800px] h-[800px] bg-primary-start/10 rounded-full blur-[120px] opacity-30 animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-secondary-start/10 rounded-full blur-[100px] opacity-20" />
      </div>

      {/* Navbar */}
      <nav className="relative z-50 px-6 py-6 max-w-7xl mx-auto flex justify-between items-center">
        <BrandLogo />
        <div className="flex gap-4">
            <Link to="/login" className="px-6 py-2.5 text-sm font-bold text-white hover:text-primary-300 transition-colors">
                {t('landing.login')}
            </Link>
            <Link to="/register" className="hidden sm:flex px-6 py-2.5 bg-white text-black text-sm font-bold rounded-xl hover:bg-gray-200 transition-all shadow-lg shadow-white/10 items-center gap-2">
                {t('landing.getStarted')} <ArrowRight size={16} />
            </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 pt-20 pb-16 px-6">
        <div className="max-w-5xl mx-auto text-center mb-24">
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
            >
                {/* Version Badge Removed */}
                
                <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 leading-tight">
                    {t('landing.heroTitle')} <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-start to-primary-end">
                        {t('landing.heroHighlight')}
                    </span>
                </h1>
                
                <p className="text-lg md:text-xl text-gray-400 max-w-3xl mx-auto mb-12 leading-relaxed">
                    {t('landing.heroSubtitle')}
                </p>
                
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Link to="/register" className="px-8 py-4 bg-gradient-to-r from-primary-start to-primary-end rounded-2xl text-lg font-bold shadow-xl shadow-primary-start/20 hover:scale-105 transition-transform flex items-center justify-center gap-3">
                        {t('landing.getStarted')} <ChevronRight />
                    </Link>
                </div>
            </motion.div>
        </div>

        {/* --- PREMIUM SHOWCASE SECTION --- */}
        <ProductShowcase />
        {/* ------------------------------- */}

        {/* Feature Grid (Secondary Highlights) */}
        <section className="py-24 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[300px]">
            <div className="md:col-span-2 row-span-1 glass-panel p-8 relative overflow-hidden group hover:border-primary-start/30 transition-colors">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500">
                    <MessageSquare className="w-48 h-48 text-primary-start" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-primary-start/20 rounded-xl flex items-center justify-center mb-4 text-primary-300 border border-primary-start/20">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2 text-white">{t('landing.socraticAssistantTitle')}</h3>
                    <p className="text-text-secondary leading-relaxed">
                        {t('landing.socraticAssistantDescription')}
                    </p>
                </div>
            </div>

            <div className="md:col-span-1 row-span-1 glass-panel p-8 relative group hover:border-success-start/30 transition-colors">
                 <div className="w-12 h-12 bg-success-start/20 rounded-xl flex items-center justify-center mb-4 text-success-300 border border-success-start/20">
                    <Lock className="w-6 h-6" />
                </div>
                <h3 className="xl font-bold mb-2 text-white">{t('landing.fullSecurityTitle')}</h3>
                <p className="text-text-secondary text-sm">
                    {t('landing.fullSecurityDescription')}
                </p>
            </div>

            <div className="md:col-span-1 row-span-1 glass-panel p-8 relative hover:border-accent-start/30 transition-colors">
                <div className="w-12 h-12 bg-accent-start/20 rounded-xl flex items-center justify-center mb-4 text-accent-300 border border-accent-start/20">
                    <TrendingUp className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold mb-2 text-white">{t('landing.businessCenterTitle')}</h3>
                <p className="text-text-secondary text-sm">
                    {t('landing.businessCenterDescription')}
                </p>
            </div>

            <div className="md:col-span-2 row-span-1 glass-panel p-8 relative overflow-hidden hover:border-secondary-start/30 transition-colors">
                 <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Database className="w-48 h-48 text-secondary-start" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-secondary-start/20 rounded-xl flex items-center justify-center mb-4 text-secondary-300 border border-secondary-start/20">
                        <FileText className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2 text-white">{t('landing.intelligentArchiveTitle')}</h3>
                    <p className="text-text-secondary leading-relaxed">
                        {t('landing.intelligentArchiveDescription')}
                    </p>
                </div>
            </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 text-center text-gray-600 text-sm relative z-10 bg-black/20">
        <p>{t('footer.copyright', { year: new Date().getFullYear() })}</p>
        <div className="flex justify-center gap-6 mt-4">
            <span className="flex items-center gap-1"><Lock size={12}/> {t('footer.encryption')}</span>
            <span className="flex items-center gap-1"><Globe size={12}/> {t('footer.jurisdiction')}</span>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;