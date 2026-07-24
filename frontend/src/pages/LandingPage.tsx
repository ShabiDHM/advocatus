// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING V7.0 (ONTOLOGY EVIDENCE GRAPH CAPABILITY INTEGRATED)

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
    ArrowRight, Lock, Globe, ChevronRight, 
    Database, FileText, Swords, ShieldCheck, BarChart2, Network
} from 'lucide-react';
import { motion } from 'framer-motion';
import BrandLogo from '../components/BrandLogo';
import ProductShowcase from '../components/landing/ProductShowcase';

const LandingPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-canvas text-text-primary overflow-x-hidden relative selection:bg-primary-start/30 font-sans">
      
      {/* Background Gradients - semantic colors */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[800px] h-[800px] bg-primary-start/10 rounded-full blur-[120px] opacity-30 animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-secondary-start/10 rounded-full blur-[100px] opacity-20" />
      </div>

      {/* Navbar */}
      <nav className="relative z-50 px-6 py-6 max-w-7xl mx-auto flex justify-between items-center h-16 shrink-0">
        <BrandLogo />
        <div className="flex gap-4 h-11 items-center">
            <Link to="/login" className="flex items-center justify-center px-6 h-11 text-sm font-bold text-text-secondary hover:text-text-primary transition-colors focus:outline-none">
                {t('landing.login')}
            </Link>
            <Link to="/register" className="hidden sm:flex px-6 h-11 btn-primary text-sm font-bold rounded-xl items-center gap-2 focus:outline-none">
                {t('landing.getStarted')} <ArrowRight size={16} />
            </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 pt-16 pb-16 px-6">
        <div className="max-w-5xl mx-auto text-center mb-20">
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
            >
                <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 leading-tight text-text-primary select-none">
                    {t('landing.heroTitle')} <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-start to-primary-end">
                        {t('landing.heroHighlight')}
                    </span>
                </h1>
                
                <p className="text-lg md:text-xl text-text-secondary max-w-3xl mx-auto mb-12 leading-relaxed">
                    {t('landing.heroSubtitle')}
                </p>
                
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Link to="/register" className="btn-primary px-8 py-4 rounded-2xl text-lg font-bold shadow-xl shadow-primary-start/25 hover:scale-105 transition-transform flex items-center justify-center gap-3 focus:outline-none">
                        {t('landing.getStarted')} <ChevronRight />
                    </Link>
                </div>
            </motion.div>
        </div>

        {/* --- PREMIUM SHOWCASE SECTION --- */}
        <ProductShowcase />
        {/* ------------------------------- */}

        {/* --- ACTUAL PLATFORM CAPABILITIES SECTION --- */}
        <section className="py-24 max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-4 max-w-3xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-text-primary">
                  Sistemi i Inteligjencës Ligjore me Performancë të Lartë
              </h2>
              <p className="text-text-secondary text-sm md:text-base leading-relaxed">
                  Zbuloni mjetet dhe algoritmet e thella që kemi integruar për të shndërruar dokumentet e lëndës në strategji të pakontestueshme procedurale.
              </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[300px]">
            
            {/* Box 1: Socratic RAG Chat & War Room */}
            <div className="md:col-span-2 row-span-1 glass-panel p-8 relative overflow-hidden group hover:border-primary-start/30 transition-colors border border-main bg-surface/30 rounded-3xl shadow-sm">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none">
                    <Swords className="w-48 h-48 text-primary-start" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-primary-start/20 rounded-xl flex items-center justify-center mb-4 text-primary-start border border-primary-start/20 shadow-inner">
                        <Swords className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2 text-text-primary tracking-tight">Asistenti Sokratik & Dhoma e Luftës</h3>
                    <p className="text-text-secondary leading-relaxed text-sm">
                        Bëni pyetje të rregulluara me RAG mbi dokumentet tuaja dhe hyni në &quot;Dhomën e Luftës&quot; për të simuluar strategjinë e palës kundërshtare, nxjerrë kronologjinë e saktë dhe detektuar kontradiktat factual në seancë.
                    </p>
                </div>
            </div>

            {/* Box 2: Forensic Accounting Analyst */}
            <div className="md:col-span-1 row-span-1 glass-panel p-8 relative group hover:border-status-success/30 transition-colors border border-main bg-surface/30 rounded-3xl shadow-sm">
                 <div className="w-12 h-12 bg-status-success/15 rounded-xl flex items-center justify-center mb-4 text-status-success border border-status-success/20 shadow-inner">
                    <BarChart2 className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold mb-2 text-text-primary tracking-tight">Analizë Financiare Forenzike</h3>
                <p className="text-text-secondary text-sm leading-relaxed">
                    Skanoni deklarata bankare, vlerësoni mospërputhjet financiare përmes Ligjit të Benfordit, zbuloni transaksione të dyshimta në vikend apo dublifikime faturash, dhe bisedoni direkt me ditarin tuaj të shpenzimeve.
                </p>
            </div>

            {/* Box 3: Ontologjia e Provave (Palantir-Style Legal Graph) */}
            <div className="md:col-span-2 row-span-1 glass-panel p-8 relative overflow-hidden group hover:border-purple-500/40 transition-colors border border-main bg-surface/30 rounded-3xl shadow-sm">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none">
                    <Network className="w-48 h-48 text-purple-500" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-4 text-purple-500 border border-purple-500/30 shadow-inner">
                        <Network className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2 text-text-primary tracking-tight">Ontologjia e Provave & Radar i Kontradiktave</h3>
                    <p className="text-text-secondary leading-relaxed text-sm">
                        Ndërtoni hartën vizuale të të gjitha entiteteve (Personave, Kompanive, Llogarive Bankare dhe Lokacioneve). AI detekton automatikisht kontradiktat factual mes dëshmive dhe gjurmon rrjedhën e parave në Euro (€).
                    </p>
                </div>
            </div>

            {/* Box 4: Context-Aware Drafting */}
            <div className="md:col-span-1 row-span-1 glass-panel p-8 relative hover:border-accent-start/30 transition-colors border border-main bg-surface/30 rounded-3xl shadow-sm">
                <div className="w-12 h-12 bg-accent-start/20 rounded-xl flex items-center justify-center mb-4 text-accent-start border border-accent-start/20 shadow-inner">
                    <FileText className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold mb-2 text-text-primary tracking-tight">Hartimi i Dokumenteve</h3>
                <p className="text-text-secondary text-sm leading-relaxed">
                    Gjeneroni shkresa ligjore, Kundërpadi, padi apo kontrata të ndryshme direkt nga faqja e Hartimit. AI është plotësisht i vetëdijshëm për të dhënat, emrat dhe numrat zyrtar të nxjerrë nga dosja e rastit tuaj.
                </p>
            </div>

          </div>
        </section>

        {/* --- HIGH-TRUST SECURITY & GDPR COMPLIANCE SECTION --- */}
        <section className="py-20 border-t border-b border-main/60 bg-surface/10 backdrop-blur-md relative z-20">
          <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              
              {/* Left Column: Title & Text */}
              <div className="space-y-6">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-success-start/10 text-success-start border border-success-start/20 rounded-full text-xs font-black tracking-widest uppercase">
                      <ShieldCheck size={14} /> GDPR & SIGURIA E TË DHËNAVE
                  </div>
                  <h2 className="text-3xl md:text-5xl font-black text-text-primary tracking-tight">
                      Privatësia dhe Sovraniteti i të Dhënave tuaja
                  </h2>
                  <p className="text-text-secondary leading-relaxed text-sm md:text-base">
                      Ne i trajtojmë shkresat gjyqësore dhe të dhënat tuaja financiare me diskrecionin më të lartë bankar. Çdo linjë kodi në platformën tonë është zhvilluar në përputhje të plotë me rregulloret e GDPR dhe Ligjin për Mbrojtjen e të Dhënave Personale të Republikës së Kosovës.
                  </p>
              </div>

              {/* Right Column: Security Feature Points */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  
                  {/* Point 1: Zero Retention */}
                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <Lock size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-sm uppercase tracking-wide">Zero Retention AI</h4>
                      <p className="text-text-secondary text-xs leading-relaxed">
                          Dokumentet tuaja analizohen në kujtesën e përkohshme (RAM) dhe nuk përdoren asnjëherë nga modelet e jashtme AI për trajnim.
                      </p>
                  </div>

                  {/* Point 2: AES-256 Encryption */}
                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <ShieldCheck size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-sm uppercase tracking-wide">Enkriptimi AES-256</h4>
                      <p className="text-text-secondary text-xs leading-relaxed">
                          Të gjitha dosjet e lëndëve tuaja ligjore dhe dëshmitë e ngarkuara enkriptohen me çelësa bankar para se të ruhen në Cloud.
                      </p>
                  </div>

                  {/* Point 3: Cascade Deletion */}
                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <Database size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-sm uppercase tracking-wide">Fshirja Kaskadë</h4>
                      <p className="text-text-secondary text-xs leading-relaxed">
                          Kur fshini një dokument apo lëndë, sistemi ynë spastron menjëherë të gjithë ditarët, vektorët, arkivat dhe skedarët fizik në sekonda.
                      </p>
                  </div>

                  {/* Point 4: European Sovereignty */}
                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <Globe size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-sm uppercase tracking-wide">Ligji i Kosovës & GDPR</h4>
                      <p className="text-text-secondary text-xs leading-relaxed">
                          Të dhënat tuaja ruhen në përputhje të plotë me ligjet e Kosovës dhe rregulloret strikte evropiane të privatësisë (GDPR).
                      </p>
                  </div>

              </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-main py-12 text-center text-text-muted text-sm relative z-10 bg-canvas/30 backdrop-blur-md">
        <p className="select-none">{t('footer.copyright', { year: new Date().getFullYear() })}</p>
        <div className="flex justify-center gap-6 mt-4 select-none">
            <span className="flex items-center gap-1.5"><Lock size={12} className="text-text-muted"/> {t('footer.encryption')}</span>
            <span className="flex items-center gap-1.5"><Globe size={12} className="text-text-muted"/> {t('footer.jurisdiction')}</span>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;