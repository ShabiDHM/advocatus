// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING V8.1 (0 WARNINGS - CLEAN IMPORTS)

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
    ArrowRight, Lock, Globe, ChevronRight, 
    Database, FileText, Swords, ShieldCheck, BarChart2, Network, Cpu, Zap
} from 'lucide-react';
import { motion } from 'framer-motion';
import BrandLogo from '../components/BrandLogo';
import ProductShowcase from '../components/landing/ProductShowcase';

const LandingPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-canvas text-text-primary overflow-x-hidden relative selection:bg-primary-start/30 font-sans">
      
      {/* Ambient Mesh Glow */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-primary-start/10 rounded-full blur-[160px] opacity-40 animate-pulse-slow" />
        <div className="absolute top-1/3 right-10 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-[130px] opacity-30" />
      </div>

      {/* Navbar */}
      <nav className="relative z-50 px-6 py-6 max-w-7xl mx-auto flex justify-between items-center h-20 shrink-0">
        <BrandLogo />
        <div className="flex gap-3 sm:gap-4 h-11 items-center">
            <Link to="/login" className="flex items-center justify-center px-5 sm:px-6 h-11 text-xs sm:text-sm font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary transition-colors focus:outline-none">
                {t('landing.login', 'Hyni Këtu')}
            </Link>
            <Link to="/register" className="flex px-5 sm:px-6 h-11 btn-primary text-xs sm:text-sm font-extrabold uppercase tracking-wider rounded-xl items-center gap-2 focus:outline-none shadow-lg shadow-primary-start/20 hover-lift">
                <span>{t('landing.getStarted', 'Fillo Tani')}</span>
                <ArrowRight size={15} />
            </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 pt-10 sm:pt-16 pb-16 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto text-center mb-16 sm:mb-20">
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
                className="space-y-6"
            >
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface border border-main text-xs font-black uppercase tracking-widest text-primary-start shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-primary-start animate-ping shrink-0" />
                    <span>Inteligjenca Artificiale Ligjore për Kosovë</span>
                </div>

                <h1 className="text-4xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[1.1] text-text-primary uppercase select-none">
                    Salla e Komandimit <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-start via-purple-500 to-primary-end">
                        dhe Strategjisë Gjyqësore
                    </span>
                </h1>
                
                <p className="text-base sm:text-lg md:text-xl text-text-secondary max-w-3xl mx-auto leading-relaxed font-medium">
                    Zëvendësoni orët e gjata të leximit me analizë të menjëhershme të provave, detektim automatik të kontradiktave dhe hartim shkresash me inteligjencë Sokratike.
                </p>
                
                <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                    <Link to="/register" className="btn-primary px-8 py-4 rounded-2xl text-sm sm:text-base font-extrabold uppercase tracking-wider shadow-2xl shadow-primary-start/30 hover-lift flex items-center justify-center gap-2.5 focus:outline-none">
                        <span>Përdore Gratis Sot</span>
                        <ChevronRight size={18} />
                    </Link>
                    <a href="#showcase" className="px-8 py-4 rounded-2xl bg-surface border border-main hover:bg-hover text-text-primary text-sm sm:text-base font-extrabold uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-sm">
                        <Cpu size={18} className="text-primary-start" />
                        <span>Shiko Platformën</span>
                    </a>
                </div>
            </motion.div>
        </div>

        {/* --- METRICS TRUST BANNER --- */}
        <div className="max-w-6xl mx-auto my-12 grid grid-cols-2 md:grid-cols-4 gap-4 p-6 bg-surface/50 border border-main rounded-3xl backdrop-blur-md shadow-sm text-center">
          <div>
            <p className="text-2xl sm:text-3xl font-black text-primary-start font-mono">50,000+</p>
            <p className="text-[11px] sm:text-xs font-bold text-text-muted uppercase tracking-wider mt-1">Dokumente të Skanuara</p>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-black text-purple-500 font-mono">100%</p>
            <p className="text-[11px] sm:text-xs font-bold text-text-muted uppercase tracking-wider mt-1">GDPR & Sovranitet i Të Dhënave</p>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-black text-emerald-500 font-mono">0.02s</p>
            <p className="text-[11px] sm:text-xs font-bold text-text-muted uppercase tracking-wider mt-1">Koha e Kërkimit Vektorial</p>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-black text-amber-500 font-mono">24 / 7</p>
            <p className="text-[11px] sm:text-xs font-bold text-text-muted uppercase tracking-wider mt-1">Asistent Ligjor Sokratik</p>
          </div>
        </div>

        {/* --- PREMIUM INTERACTIVE PRODUCT SHOWCASE SECTION --- */}
        <div id="showcase">
          <ProductShowcase />
        </div>

        {/* --- ACTUAL PLATFORM CAPABILITIES SECTION --- */}
        <section className="py-24 max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-4 max-w-3xl mx-auto">
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary-start/10 text-primary-start text-xs font-black uppercase tracking-widest border border-primary-start/20">
                <Zap size={14} />
                <span>Teknologji e Nivelit Botëror</span>
              </div>
              <h2 className="text-3xl md:text-5xl font-black tracking-tight uppercase text-text-primary">
                  Sistemi i Inteligjencës Ligjore
              </h2>
              <p className="text-text-secondary text-sm md:text-base leading-relaxed font-medium">
                  Mjetet dhe algoritmet e thella që kemi integruar për të shndërruar dokumentet e lëndës në strategji të pakontestueshme gjyqësore.
              </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[320px]">
            
            {/* Box 1: Socratic RAG Chat & War Room */}
            <div className="md:col-span-2 row-span-1 glass-panel p-8 relative overflow-hidden group hover:border-primary-start/40 transition-colors border border-main bg-surface rounded-3xl shadow-sm">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none">
                    <Swords className="w-48 h-48 text-primary-start" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-primary-start/15 rounded-2xl flex items-center justify-center mb-4 text-primary-start border border-primary-start/20 shadow-sm">
                        <Swords className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-black uppercase text-text-primary tracking-tight mb-2">Asistenti Sokratik & Dhoma e Luftës</h3>
                    <p className="text-text-secondary leading-relaxed text-sm font-medium">
                        Bëni pyetje mbi fashikullin e lëndës dhe hyni në &quot;Dhomën e Luftës&quot; për të simuluar strategjinë e palës kundërshtare, nxjerrë kronologjinë e saktë dhe detektuar mospërputhjet procedural.
                    </p>
                </div>
            </div>

            {/* Box 2: Forensic Accounting Analyst */}
            <div className="md:col-span-1 row-span-1 glass-panel p-8 relative group hover:border-status-success/40 transition-colors border border-main bg-surface rounded-3xl shadow-sm">
                 <div className="w-12 h-12 bg-status-success/15 rounded-2xl flex items-center justify-center mb-4 text-status-success border border-status-success/20 shadow-sm">
                    <BarChart2 className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-black uppercase text-text-primary tracking-tight mb-2">Analizë Financiare Forenzike</h3>
                <p className="text-text-secondary text-sm leading-relaxed font-medium">
                    Auditim i librave bankarë, vlerësim i anomalisë financiare përmes Ligjit të Benfordit, zbulim i transaksioneve të dyshimta dhe bisedë direkte me ditarin e arkës.
                </p>
            </div>

            {/* Box 3: Ontologjia e Provave */}
            <div className="md:col-span-2 row-span-1 glass-panel p-8 relative overflow-hidden group hover:border-purple-500/40 transition-colors border border-main bg-surface rounded-3xl shadow-sm">
                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none">
                    <Network className="w-48 h-48 text-purple-500" />
                </div>
                <div className="relative z-10 h-full flex flex-col justify-end">
                    <div className="w-12 h-12 bg-purple-500/15 rounded-2xl flex items-center justify-center mb-4 text-purple-500 border border-purple-500/30 shadow-sm">
                        <Network className="w-6 h-6" />
                    </div>
                    <h3 className="text-2xl font-black uppercase text-text-primary tracking-tight mb-2">Ontologjia e Provave & Radar i Kontradiktave</h3>
                    <p className="text-text-secondary leading-relaxed text-sm font-medium">
                        Ndërtoni hartën vizuale të të gjitha entiteteve (Personave, Kompanive, Llogarive Bankare dhe Lokacioneve). AI detekton automatikisht kontradiktat factual mes dëshmive dhe gjurmon rrjedhën e parave në Euro (€).
                    </p>
                </div>
            </div>

            {/* Box 4: Context-Aware Drafting */}
            <div className="md:col-span-1 row-span-1 glass-panel p-8 relative hover:border-accent-start/40 transition-colors border border-main bg-surface rounded-3xl shadow-sm">
                <div className="w-12 h-12 bg-accent-start/15 rounded-2xl flex items-center justify-center mb-4 text-accent-start border border-accent-start/20 shadow-sm">
                    <FileText className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-black uppercase text-text-primary tracking-tight mb-2">Hartimi i Dokumenteve</h3>
                <p className="text-text-secondary text-sm leading-relaxed font-medium">
                    Gjeneroni shkresa ligjore, Kundërpadi, padi apo kontrata të ndryshme direkt me AI. Përfshin automatikisht nenet e LPK-së, emrat dhe numrat zyrtarë nga lënda.
                </p>
            </div>

          </div>
        </section>

        {/* --- HIGH-TRUST SECURITY & GDPR COMPLIANCE SECTION --- */}
        <section className="py-20 border-t border-b border-main/60 bg-surface/20 backdrop-blur-md relative z-20">
          <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              
              <div className="space-y-6">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-status-success/10 text-status-success border border-status-success/20 rounded-full text-xs font-black tracking-widest uppercase">
                      <ShieldCheck size={14} /> GDPR & SIGURIA E TË DHËNAVE
                  </div>
                  <h2 className="text-3xl md:text-5xl font-black text-text-primary tracking-tight uppercase">
                      Privatësia dhe Sovraniteti i Të Dhënave
                  </h2>
                  <p className="text-text-secondary leading-relaxed text-sm md:text-base font-medium">
                      Ne i trajtojmë shkresat gjyqësore dhe të dhënat tuaja financiare me diskrecionin më të lartë bankar. Çdo linjë kodi në platformën tonë është zhvilluar në përputhje të plotë me rregulloret e GDPR dhe Ligjin për Mbrojtjen e të Dhënave Personale të Republikës së Kosovës.
                  </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <Lock size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-xs uppercase tracking-wider">Zero Retention AI</h4>
                      <p className="text-text-secondary text-xs leading-relaxed font-medium">
                          Dokumentet tuaja analizohen në kujtesën e përkohshme (RAM) dhe nuk përdoren asnjëherë nga modelet e jashtme AI për trajnim.
                      </p>
                  </div>

                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <ShieldCheck size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-xs uppercase tracking-wider">Enkriptimi AES-256</h4>
                      <p className="text-text-secondary text-xs leading-relaxed font-medium">
                          Të gjitha dosjet e lëndëve tuaja ligjore dhe dëshmitë e ngarkuara enkriptohen me çelësa bankar para se të ruhen në Cloud.
                      </p>
                  </div>

                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <Database size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-xs uppercase tracking-wider">Fshirja Kaskadë</h4>
                      <p className="text-text-secondary text-xs leading-relaxed font-medium">
                          Kur fshini një dokument apo lëndë, sistemi ynë spastron menjëherë të gjithë ditarët, vektorët, arkivat dhe skedarët fizik në sekonda.
                      </p>
                  </div>

                  <div className="bg-surface border border-main rounded-2xl p-6 space-y-3 hover:border-primary-start/40 transition-colors shadow-sm">
                      <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                          <Globe size={18} />
                      </div>
                      <h4 className="font-bold text-text-primary text-xs uppercase tracking-wider">Ligji i Kosovës & GDPR</h4>
                      <p className="text-text-secondary text-xs leading-relaxed font-medium">
                          Të dhënat tuaja ruhen në përputhje të plotë me ligjet e Kosovës dhe rregulloret strikte evropiane të privatësisë (GDPR).
                      </p>
                  </div>
              </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-main py-12 text-center text-text-muted text-sm relative z-10 bg-canvas/30 backdrop-blur-md">
        <p className="select-none text-xs font-semibold">{t('footer.copyright', { year: new Date().getFullYear() })}</p>
        <div className="flex justify-center gap-6 mt-4 select-none text-xs font-bold uppercase tracking-wider">
            <span className="flex items-center gap-1.5"><Lock size={12} className="text-primary-start"/> {t('footer.encryption', 'AES-256 ENCRYPTED')}</span>
            <span className="flex items-center gap-1.5"><Globe size={12} className="text-primary-start"/> {t('footer.jurisdiction', 'REPUBLIKA E KOSOVËS')}</span>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;