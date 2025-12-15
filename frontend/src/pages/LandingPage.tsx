// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING PAGE V2.2 (MOBILE FONTS)
// 1. STYLE: Hero text reduced to 4xl on mobile (was 5xl).
// 2. LAYOUT: Padding adjusted for better mobile breathing room.
// 3. STATUS: Mobile Optimized.

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
    <div className="min-h-screen bg-[#0B1120] text-white overflow-hidden font-sans selection:bg-primary-start selection:text-white">
      
      {/* BACKGROUND EFFECTS */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[300px] md:w-[500px] h-[300px] md:h-[500px] bg-primary-start/20 rounded-full blur-[80px] md:blur-[120px]" />
        <div className="absolute bottom-[10%] right-[-5%] w-[250px] md:w-[400px] h-[250px] md:h-[400px] bg-secondary-start/20 rounded-full blur-[80px] md:blur-[100px]" />
      </div>

      <div className="relative z-10">
        
        {/* --- HERO SECTION --- */}
        <section className="pt-24 md:pt-32 pb-16 md:pb-24 text-center max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.6 }}
          >
            <span className="inline-block py-1 px-3 rounded-full bg-blue-900/30 border border-blue-500/30 text-blue-400 text-[10px] md:text-xs font-semibold tracking-wider mb-6 uppercase">
              Platforma Nr. 1 për Juristët në Kosovë
            </span>
            {/* PHOENIX FIX: Responsive Font Sizes */}
            <h1 className="text-4xl md:text-5xl lg:text-7xl font-bold mb-6 leading-tight">
              Më i zgjuar. Më i shpejtë.<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-start to-secondary-end">
                Juristi.tech
              </span>
            </h1>
            <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed px-2">
              Transformoni zyrën tuaj ligjore me fuqinë e Inteligjencës Artificiale.
              <br className="hidden md:block"/>
              <span className="text-white font-medium block mt-2">
                Analizë Rastesh • Asistent Sokratik • Menaxhim Biznesi
              </span>
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center px-4">
              <Link to="/register" className="w-full sm:w-auto group relative px-8 py-4 bg-primary-start hover:bg-primary-end rounded-xl font-bold text-lg shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:shadow-[0_0_30px_rgba(59,130,246,0.7)] transition-all flex items-center justify-center gap-2">
                Provo Falas
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link to="/login" className="w-full sm:w-auto px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl font-medium text-lg transition-all backdrop-blur-sm text-center">
                Hyni në Platformë
              </Link>
            </div>
          </motion.div>
        </section>

        {/* --- STATS --- */}
        <section className="py-12 border-y border-white/5 bg-white/5 backdrop-blur-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
                <div className="p-4 md:p-6">
                    <h3 className="text-4xl font-bold text-primary-start mb-2">60%</h3>
                    <p className="text-gray-400">Kursim në kohë administrative.</p>
                </div>
                <div className="p-4 md:p-6 border-y md:border-y-0 md:border-x border-white/5">
                    <h3 className="text-4xl font-bold text-yellow-400 mb-2">Zero</h3>
                    <p className="text-gray-400">Humbje të afateve ligjore.</p>
                </div>
                <div className="p-4 md:p-6">
                    <h3 className="text-4xl font-bold text-green-400 mb-2">24/7</h3>
                    <p className="text-gray-400">Asistenti juaj ligjor është gjithmonë gati.</p>
                </div>
            </div>
        </section>

        {/* --- SHOWCASE --- */}
        <ProductShowcase />

        {/* --- FEATURES --- */}
        <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 md:mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Nga Kaosi në Strategji</h2>
            <p className="text-gray-400">Një platformë e vetme për të gjitha nevojat e zyrës suaj.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-auto md:auto-rows-[300px]">
            
            <div className="md:col-span-2 row-span-1 rounded-3xl p-6 md:p-8 border border-white/10 bg-gradient-to-br from-gray-900 to-gray-800 relative overflow-hidden group min-h-[250px]">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                    <MessageSquare className="w-32 h-32 md:w-48 md:h-48" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-10 h-10 md:w-12 md:h-12 bg-blue-500/20 rounded-xl flex items-center justify-center mb-4 text-blue-400">
                        <Zap className="w-5 h-5 md:w-6 md:h-6" />
                    </div>
                    <h3 className="text-xl md:text-2xl font-bold mb-2">Asistenti Sokratik AI</h3>
                    <p className="text-gray-400 text-sm md:text-base">
                        Bisedoni me dokumentet tuaja. Bëni pyetje komplekse juridike dhe merrni përgjigje të menjëhershme.
                    </p>
                </div>
            </div>

            <div className="md:col-span-1 row-span-1 rounded-3xl p-6 md:p-8 border border-white/10 bg-gray-900 relative group min-h-[200px]">
                 <div className="w-10 h-10 md:w-12 md:h-12 bg-green-500/20 rounded-xl flex items-center justify-center mb-4 text-green-400">
                    <Lock className="w-5 h-5 md:w-6 md:h-6" />
                </div>
                <h3 className="text-lg md:text-xl font-bold mb-2">Siguri e Plotë</h3>
                <p className="text-gray-400 text-sm">
                    Të dhënat tuaja janë të enkriptuara.
                </p>
            </div>

            <div className="md:col-span-1 row-span-1 rounded-3xl p-6 md:p-8 border border-white/10 bg-gray-900 relative min-h-[200px]">
                <div className="w-10 h-10 md:w-12 md:h-12 bg-yellow-500/20 rounded-xl flex items-center justify-center mb-4 text-yellow-400">
                    <TrendingUp className="w-5 h-5 md:w-6 md:h-6" />
                </div>
                <h3 className="text-lg md:text-xl font-bold mb-2">Qendra e Biznesit</h3>
                <p className="text-gray-400 text-sm">
                    Gjeneroni fatura dhe menaxhoni klientët.
                </p>
            </div>

            <div className="md:col-span-2 row-span-1 rounded-3xl p-6 md:p-8 border border-white/10 bg-gradient-to-br from-gray-800 to-gray-900 relative overflow-hidden min-h-[250px]">
                 <div className="absolute top-0 right-0 p-8 opacity-10">
                    <Database className="w-32 h-32 md:w-48 md:h-48" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-10 h-10 md:w-12 md:h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-4 text-purple-400">
                        <FileText className="w-5 h-5 md:w-6 md:h-6" />
                    </div>
                    <h3 className="text-xl md:text-2xl font-bold mb-2">Arkiva Inteligjente</h3>
                    <p className="text-gray-400 text-sm md:text-base">
                        Skanoni, ruani dhe kërkoni në sekonda brenda mijëra faqeve PDF.
                    </p>
                </div>
            </div>

          </div>
        </section>

        {/* --- CTA --- */}
        <section className="py-16 md:py-24 text-center max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-gradient-to-r from-blue-900/40 to-purple-900/40 border border-white/10 rounded-3xl p-8 md:p-12 relative overflow-hidden">
                <div className="relative z-10">
                    <h2 className="text-2xl md:text-4xl font-bold mb-4 md:mb-6">Gati për të modernizuar zyrën tuaj?</h2>
                    <p className="text-lg md:text-xl text-gray-300 mb-6 md:mb-8 max-w-2xl mx-auto">
                        Regjistrohuni sot në Juristi.tech.
                    </p>
                    <Link to="/register" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-gray-900 hover:bg-gray-100 rounded-xl font-bold text-lg transition-colors w-full sm:w-auto justify-center">
                        Fillo Tani
                        <ChevronRight className="w-5 h-5" />
                    </Link>
                </div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] md:w-[500px] h-[300px] md:h-[500px] bg-blue-500/20 rounded-full blur-[100px] pointer-events-none" />
            </div>
        </section>

        {/* --- FOOTER --- */}
        <footer className="py-8 border-t border-white/10 text-center text-gray-500 text-sm">
            <p>&copy; {new Date().getFullYear()} Data And Human Management. Të gjitha të drejtat e rezervuara.</p>
        </footer>

      </div>
    </div>
  );
};

export default LandingPage;