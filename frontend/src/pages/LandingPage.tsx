// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING PAGE (TRANSLATED & RESPONSIVE)
import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, FileText, Cpu, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const LandingPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-background-dark text-white overflow-hidden">
      {/* Hero Section */}
      <div className="relative pt-24 pb-16 sm:pt-32 sm:pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6">
            <span className="block bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
              {t('landing.heroTitle', 'Inteligjenca Artificiale')}
            </span>
            <span className="block text-primary-start mt-2">
              {t('landing.heroHighlight', 'për Profesionistët Ligjorë')}
            </span>
          </h1>
          <p className="mt-4 text-xl text-text-secondary max-w-2xl mx-auto">
            {t('landing.heroSubtitle', 'Analizoni kontrata, menaxhoni raste dhe gjeneroni dokumente në sekonda me fuqinë e AI.')}
          </p>
          <div className="mt-10 flex flex-col sm:flex-row justify-center gap-4">
            <Link to="/register" className="px-8 py-3 rounded-xl bg-gradient-to-r from-primary-start to-primary-end text-white font-bold shadow-lg glow-primary hover:scale-105 transition-transform flex items-center justify-center">
              {t('landing.getStarted', 'Fillo Falas')} <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link to="/login" className="px-8 py-3 rounded-xl bg-white/10 text-white font-semibold hover:bg-white/20 border border-white/10 backdrop-blur-sm transition-all flex items-center justify-center">
              {t('auth.loginButton', 'Hyni')}
            </Link>
          </div>
        </div>
        
        {/* Background Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] sm:w-[500px] h-[300px] sm:h-[500px] bg-primary-start/20 rounded-full blur-[120px] -z-10"></div>
      </div>

      {/* Features Grid */}
      <div className="py-24 bg-background-light/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<ShieldCheck className="h-8 w-8 text-secondary-start" />}
              title={t('landing.feature1Title', 'Analizë e Sigurt')}
              desc={t('landing.feature1Desc', 'Skanoni dokumente për rreziqe ligjore dhe shkelje të kodit.')}
            />
            <FeatureCard 
              icon={<Cpu className="h-8 w-8 text-primary-start" />}
              title={t('landing.feature2Title', 'AI Sokratike')}
              desc={t('landing.feature2Desc', 'Bisedoni me dokumentet tuaja. Bëni pyetje dhe merrni përgjigje.')}
            />
            <FeatureCard 
              icon={<FileText className="h-8 w-8 text-accent-start" />}
              title={t('landing.feature3Title', 'Draftim Inteligjent')}
              desc={t('landing.feature3Desc', 'Krijoni kontrata dhe padi të personalizuara bazuar në shabllone.')}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

const FeatureCard = ({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) => (
  <div className="p-6 bg-background-dark border border-glass-edge rounded-2xl hover:border-primary-start/50 transition-colors">
    <div className="mb-4 p-3 bg-white/5 rounded-xl w-fit">{icon}</div>
    <h3 className="text-xl font-bold mb-2 text-white">{title}</h3>
    <p className="text-text-secondary">{desc}</p>
  </div>
);

export default LandingPage;