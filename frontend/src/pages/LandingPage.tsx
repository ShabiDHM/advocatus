// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING PAGE V3.0 (GLASS & SYSTEM ALIGNMENT)
// 1. VISUALS: Full Glassmorphism adoption with 'glass-panel' and 'ambient glows'.
// 2. COLORS: Replaced hardcoded blues with 'primary-start' system variables.
// 3. RESPONSIVE: Fine-tuned mobile typography and padding.

import React from 'react';
import { motion } from 'framer-motion';
import { 
    Zap, 
    FileText, 
    Database, 
    Lock, 
    ChevronRight, 
    TrendingUp, 
    MessageSquare,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import ProductShowcase from '../components/landing/ProductShowcase';

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-background-dark text-white overflow-hidden font-sans selection:bg-primary-start/30 selection:text-white relative">
      
      {/* BACKGROUND EFFECTS */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[300px] md:w-[600px] h-[300px] md:h-[600px] bg-primary-start/20 rounded-full blur-[80px] md:blur-[120px] animate-pulse-slow" />
        <div className="absolute bottom-[10%] right-[-5%] w-[250px] md:w-[500px] h-[250px] md:h-[500px] bg-secondary-start/20 rounded-full blur-[80px] md:blur-[100px] animate-pulse-slow delay-1000" />
      </div>

      <div className="relative z-10">
        
        {/* --- HERO SECTION --- */}
        <section className="pt-24 md:pt-32 pb-16 md:pb-24 text-center max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.6 }}
          >
            <span className="inline-block py-1.5 px-4 rounded-full bg-primary-start/10 border border-primary-start/20 text-primary-300 text-[10px] md:text-xs font-bold tracking-wider mb-6 uppercase shadow-lg shadow-primary-start/5">
              Platforma Nr. 1 për Juristët në Kosovë
            </span>
            
            <h1 className="text-4xl md:text-5xl lg:text-7xl font-bold mb-6 leading-tight tracking-tight">
              Më i zgjuar. Më i shpejtë.<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-start to-secondary-end">
                Juristi.tech
              </span>
            </h1>
            <p className="text-lg md:text-xl text-text-secondary mb-10 max-w-2xl mx-auto leading-relaxed px-2 font-medium">
              Transformoni zyrën tuaj ligjore me fuqinë e Inteligjencës Artificiale.
              <br className="hidden md:block"/>
              <span className="text-white font-bold block mt-2">
                Analizë Rastesh • Asistent Sokratik • Menaxhim Biznesi
              </span>
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center px-4">
              <Link to="/register" className="w-full sm:w-auto group relative px-8 py-4 bg-gradient-to-r from-primary-start to-primary-end rounded-xl font-bold text-lg text-white shadow-lg shadow-primary-start/30 hover:shadow-primary-start/50 transition-all flex items-center justify-center gap-2 hover:-translate-y-1">
                Provo Falas
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link to="/login" className="w-full sm:w-auto px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-xl font-bold text-lg text-white transition-all backdrop-blur-sm text-center hover:-translate-y-1">
                Hyni në Platformë
              </Link>
            </div>
          </motion.div>
        </section>

        {/* --- STATS --- */}
        <section className="py-12 border-y border-white/5 bg-background-dark/50 backdrop-blur-md">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
                <div className="p-4 md:p-6">
                    <h3 className="text-4xl font-bold text-primary-start mb-2 drop-shadow-lg">60%</h3>
                    <p className="text-text-secondary font-medium">Kursim në kohë administrative.</p>
                </div>
                <div className="p-4 md:p-6 border-y md:border-y-0 md:border-x border-white/5">
                    <h3 className="text-4xl font-bold text-accent-start mb-2 drop-shadow-lg">Zero</h3>
                    <p className="text-text-secondary font-medium">Humbje të afateve ligjore.</p>
                </div>
                <div className="p-4 md:p-6">
                    <h3 className="text-4xl font-bold text-success-start mb-2 drop-shadow-lg">24/7</h3>
                    <p className="text-text-secondary font-medium">Asistenti juaj ligjor është gjithmonë gati.</p>
                </div>
            </div>
        </section>

        {/* --- SHOWCASE --- */}
        <ProductShowcase />

        {/* --- FEATURES --- */}
        <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 md:mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4 text-white">Nga Kaosi në Strategji</h2>
            <p className="text-text-secondary text-lg">Një platformë e vetme për të gjitha nevojat e zyrës suaj.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-auto md:auto-rows-[300px]">
            
            <div className="md:col-span-2 row-span-1 glass-panel p-6 md:p-8 relative overflow-hidden group min-h-[250px] transition-all hover:border-primary-start/30">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500">
                    <MessageSquare className="w-32 h-32 md:w-48 md:h-48 text-primary-start" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-10 h-10 md:w-12 md:h-12 bg-primary-start/20 rounded-xl flex items-center justify-center mb-4 text-primary-300 border border-primary-start/20">
                        <Zap className="w-5 h-5 md:w-6 md:h-6" />
                    </div>
                    <h3 className="text-xl md:text-2xl font-bold mb-2 text-white">Asistenti Sokratik AI</h3>
                    <p className="text-text-secondary text-sm md:text-base leading-relaxed">
                        Bisedoni me dokumentet tuaja. Bëni pyetje komplekse juridike dhe merrni përgjigje të menjëhershme.
                    </p>
                </div>
            </div>

            <div className="md:col-span-1 row-span-1 glass-panel p-6 md:p-8 relative group min-h-[200px] transition-all hover:border-success-start/30">
                 <div className="w-10 h-10 md:w-12 md:h-12 bg-success-start/20 rounded-xl flex items-center justify-center mb-4 text-success-300 border border-success-start/20">
                    <Lock className="w-5 h-5 md:w-6 md:h-6" />
                </div>
                <h3 className="text-lg md:text-xl font-bold mb-2 text-white">Siguri e Plotë</h3>
                <p className="text-text-secondary text-sm">
                    Të dhënat tuaja janë të enkriptuara dhe të mbrojtura me standardet më të larta.
                </p>
            </div>

            <div className="md:col-span-1 row-span-1 glass-panel p-6 md:p-8 relative min-h-[200px] transition-all hover:border-accent-start/30">
                <div className="w-10 h-10 md:w-12 md:h-12 bg-accent-start/20 rounded-xl flex items-center justify-center mb-4 text-accent-300 border border-accent-start/20">
                    <TrendingUp className="w-5 h-5 md:w-6 md:h-6" />
                </div>
                <h3 className="text-lg md:text-xl font-bold mb-2 text-white">Qendra e Biznesit</h3>
                <p className="text-text-secondary text-sm">
                    Gjeneroni fatura, menaxhoni klientët dhe gjurmoni financat e zyrës.
                </p>
            </div>

            <div className="md:col-span-2 row-span-1 glass-panel p-6 md:p-8 relative overflow-hidden min-h-[250px] transition-all hover:border-secondary-start/30">
                 <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Database className="w-32 h-32 md:w-48 md:h-48 text-secondary-start" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-10 h-10 md:w-12 md:h-12 bg-secondary-start/20 rounded-xl flex items-center justify-center mb-4 text-secondary-300 border border-secondary-start/20">
                        <FileText className="w-5 h-5 md:w-6 md:h-6" />
                    </div>
                    <h3 className="text-xl md:text-2xl font-bold mb-2 text-white">Arkiva Inteligjente</h3>
                    <p className="text-text-secondary text-sm md:text-base leading-relaxed">
                        Skanoni, ruani dhe kërkoni në sekonda brenda mijëra faqeve PDF me fuqinë e OCR.
                    </p>
                </div>
            </div>

          </div>
        </section>

        {/* --- CTA --- */}
        <section className="py-16 md:py-24 text-center max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="glass-high border border-white/10 rounded-3xl p-8 md:p-12 relative overflow-hidden">
                <div className="relative z-10">
                    <h2 className="text-2xl md:text-4xl font-bold mb-4 md:mb-6 text-white">Gati për të modernizuar zyrën tuaj?</h2>
                    <p className="text-lg md:text-xl text-text-secondary mb-6 md:mb-8 max-w-2xl mx-auto">
                        Regjistrohuni sot në Juristi.tech dhe përjetoni të ardhmen e drejtësisë.
                    </p>
                    <Link to="/register" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-gray-900 hover:bg-gray-100 rounded-xl font-bold text-lg transition-colors w-full sm:w-auto justify-center shadow-lg hover:shadow-xl hover:-translate-y-1">
                        Fillo Tani
                        <ChevronRight className="w-5 h-5" />
                    </Link>
                </div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] md:w-[500px] h-[300px] md:h-[500px] bg-primary-start/20 rounded-full blur-[100px] pointer-events-none" />
            </div>
        </section>

        {/* --- FOOTER --- */}
        <footer className="py-8 border-t border-white/5 text-center text-text-secondary text-sm bg-background-dark/50 backdrop-blur-sm">
            <p>&copy; {new Date().getFullYear()} Data And Human Management. Të gjitha të drejtat e rezervuara.</p>
        </footer>

      </div>
    </div>
  );
};

export default LandingPage;