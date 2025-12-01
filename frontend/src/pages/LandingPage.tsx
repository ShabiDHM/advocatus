// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - TEXT UPDATE
// 1. CONTENT: Changed 'Avokatët' to 'Juristët' in the hero badge.
// 2. STATUS: Production-ready.

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
    Briefcase
} from 'lucide-react';
import { Link } from 'react-router-dom';

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0B1120] text-white overflow-hidden font-sans selection:bg-primary-start selection:text-white">
      
      {/* BACKGROUND EFFECTS */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary-start/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[10%] right-[-5%] w-[400px] h-[400px] bg-secondary-start/20 rounded-full blur-[100px]" />
        <div className="absolute top-[40%] left-[20%] w-[300px] h-[300px] bg-blue-600/10 rounded-full blur-[80px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* --- HERO SECTION --- */}
        <section className="pt-32 pb-24 text-center">
          <motion.div 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.6 }}
          >
            <span className="inline-block py-1 px-3 rounded-full bg-blue-900/30 border border-blue-500/30 text-blue-400 text-xs font-semibold tracking-wider mb-6 uppercase">
              Platforma Nr. 1 për Juristët në Kosovë
            </span>
            <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
              Më i zgjuar. Më i shpejtë.<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-start to-secondary-end">
                Juristi.tech
              </span>
            </h1>
            <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
              Transformoni zyrën tuaj ligjore me fuqinë e Inteligjencës Artificiale.
              <br/>
              <span className="text-white font-medium block mt-2">
                Analizë Rastesh • Asistent Sokratik • Menaxhim Biznesi
              </span>
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link to="/register" className="group relative px-8 py-4 bg-primary-start hover:bg-primary-end rounded-xl font-bold text-lg shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:shadow-[0_0_30px_rgba(59,130,246,0.7)] transition-all flex items-center gap-2">
                Provo Falas
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link to="/login" className="px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl font-medium text-lg transition-all backdrop-blur-sm">
                Hyni në Platformë
              </Link>
            </div>
          </motion.div>
        </section>

        {/* --- STATS / PAIN POINTS --- */}
        <section className="py-12 border-y border-white/5 bg-white/5 backdrop-blur-sm">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
                <div className="p-6">
                    <h3 className="text-4xl font-bold text-primary-start mb-2">60%</h3>
                    <p className="text-gray-400">Kursim në kohë administrative.</p>
                </div>
                <div className="p-6 border-y md:border-y-0 md:border-x border-white/5">
                    <h3 className="text-4xl font-bold text-yellow-400 mb-2">Zero</h3>
                    <p className="text-gray-400">Humbje të afateve ligjore.</p>
                </div>
                <div className="p-6">
                    <h3 className="text-4xl font-bold text-green-400 mb-2">24/7</h3>
                    <p className="text-gray-400">Asistenti juaj ligjor është gjithmonë gati.</p>
                </div>
            </div>
        </section>

        {/* --- FEATURES (BENTO GRID) --- */}
        <section className="py-24">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Nga Kaosi në Strategji</h2>
            <p className="text-gray-400">Një platformë e vetme për të gjitha nevojat e zyrës suaj.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[300px]">
            
            {/* Card 1: Socratic Assistant */}
            <div className="md:col-span-2 row-span-1 rounded-3xl p-8 border border-white/10 bg-gradient-to-br from-gray-900 to-gray-800 hover:border-primary-start/50 transition-colors relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                    <MessageSquare className="w-48 h-48" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center mb-4 text-blue-400">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2">Asistenti Sokratik AI</h3>
                    <p className="text-gray-400">
                        Bisedoni me dokumentet tuaja. Bëni pyetje komplekse juridike dhe merrni përgjigje të menjëhershme të bazuara në ligjet e Kosovës dhe dosjen tuaj.
                    </p>
                </div>
            </div>

            {/* Card 2: Security */}
            <div className="md:col-span-1 row-span-1 rounded-3xl p-8 border border-white/10 bg-gray-900 hover:bg-gray-800 transition-colors relative group">
                 <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mb-4 text-green-400">
                    <Lock className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold mb-2">Siguri e Plotë</h3>
                <p className="text-gray-400 text-sm">
                    Të dhënat tuaja janë të enkriptuara. Ne nuk trajnojmë modelet tona me dokumentet e klientëve tuaj.
                </p>
            </div>

            {/* Card 3: Business Center */}
            <div className="md:col-span-1 row-span-1 rounded-3xl p-8 border border-white/10 bg-gray-900 hover:bg-gray-800 transition-colors">
                <div className="w-12 h-12 bg-yellow-500/20 rounded-xl flex items-center justify-center mb-4 text-yellow-400">
                    <TrendingUp className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold mb-2">Qendra e Biznesit</h3>
                <p className="text-gray-400 text-sm">
                    Gjeneroni fatura, menaxhoni klientët dhe ndiqni financat e zyrës me një klikim. Agjenti "Kontabilisti AI" së shpejti.
                </p>
            </div>

            {/* Card 4: Document Archive */}
            <div className="md:col-span-2 row-span-1 rounded-3xl p-8 border border-white/10 bg-gradient-to-br from-gray-800 to-gray-900 hover:border-secondary-start/50 transition-colors relative overflow-hidden">
                 <div className="absolute top-0 right-0 p-8 opacity-10">
                    <Database className="w-48 h-48" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-4 text-purple-400">
                        <FileText className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2">Arkiva Inteligjente</h3>
                    <p className="text-gray-400">
                        Skanoni, ruani dhe kërkoni në sekonda brenda mijëra faqeve PDF. OCR automatik për çdo dokument të ngarkuar.
                    </p>
                </div>
            </div>

          </div>
        </section>

        {/* --- TESTIMONIALS --- */}
        <section className="py-20">
             <div className="text-center mb-12">
                <h2 className="text-3xl font-bold">Besuar nga profesionistët</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <TestimonialCard 
                    quote="Juristi.tech ma ka thjeshtësuar jashtëzakonisht shumë menaxhimin e lëndëve penale. Kërkimi në dokumente është i menjëhershëm."
                    role="Avokat, Prishtinë"
                />
                <TestimonialCard 
                    quote="Moduli i faturimit dhe Qendra e Biznesit më kursen orë të tëra çdo fundmuaj. Është fiks çfarë i duhet një zyreje moderne."
                    role="Juriste, Prizren"
                />
                 <TestimonialCard 
                    quote="Asistenti Sokratik më ndihmon të përgatis strategjinë e mbrojtjes shumë më shpejt duke analizuar dëshmitë në sekonda."
                    role="Partner i Zyrës Ligjore"
                />
            </div>
        </section>

        {/* --- CTA --- */}
        <section className="py-24 text-center">
            <div className="bg-gradient-to-r from-blue-900/40 to-purple-900/40 border border-white/10 rounded-3xl p-12 relative overflow-hidden">
                <div className="relative z-10">
                    <h2 className="text-4xl font-bold mb-6">Gati për të modernizuar zyrën tuaj?</h2>
                    <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
                        Regjistrohuni sot në Juristi.tech dhe përjetoni ndryshimin në praktikën tuaj ligjore.
                    </p>
                    <Link to="/register" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-gray-900 hover:bg-gray-100 rounded-xl font-bold text-lg transition-colors">
                        Fillo Tani
                        <ChevronRight className="w-5 h-5" />
                    </Link>
                </div>
                {/* Glow effect */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/20 rounded-full blur-[100px] pointer-events-none" />
            </div>
        </section>

        {/* --- FOOTER --- */}
        <footer className="py-8 border-t border-white/10 text-center text-gray-500 text-sm">
            <p>&copy; {new Date().getFullYear()} Juristi.tech. Të gjitha të drejtat e rezervuara.</p>
        </footer>

      </div>
    </div>
  );
};

const TestimonialCard = ({ quote, role }: { quote: string, role: string }) => (
    <div className="p-6 bg-[#111827] border border-white/5 rounded-2xl relative">
        <div className="absolute top-4 left-4 text-blue-500 opacity-50">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor"><path d="M14.017 21L14.017 18C14.017 16.054 15.391 14.508 17.067 13.911C16.326 13.911 15.659 13.565 15.115 12.984C14.542 12.373 14.254 11.536 14.254 10.518C14.254 8.243 15.86 6.353 18.232 6.353C20.669 6.353 22.25 8.243 22.25 10.662C22.25 15.205 19.38 21 14.017 21ZM5 21L5 18C5 16.054 6.374 14.508 8.05 13.911C7.309 13.911 6.642 13.565 6.098 12.984C5.525 12.373 5.237 11.536 5.237 10.518C5.237 8.243 6.843 6.353 9.215 6.353C11.652 6.353 13.233 8.243 13.233 10.662C13.233 15.205 10.363 21 5 21Z" /></svg>
        </div>
        <p className="text-gray-300 italic mb-4 relative z-10 pt-8">"{quote}"</p>
        <div className="flex items-center gap-3 border-t border-white/5 pt-4">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-gray-700 to-gray-600 flex items-center justify-center">
                <Briefcase className="w-4 h-4 text-gray-300" />
            </div>
            <p className="text-sm font-semibold text-blue-400">{role}</p>
        </div>
    </div>
);

export default LandingPage;