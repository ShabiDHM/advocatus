// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - LANDING PAGE V50.0 (TIER-1 SUPREME SHOWCASE & UNIFIED KOSOVO PRICING)

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  Scale,
  Swords,
  CheckCircle2,
  Lock,
  ArrowRight,
  ChevronRight,
  Database,
  FileCheck2,
  Film,
  BookOpen,
  Mic,
  FileSearch,
  Sparkles,
  CreditCard,
  Building2,
  User as UserIcon,
  Banknote,
  Smartphone
} from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

type RoleTab = 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL';

export const LandingPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeRole, setActiveRole] = useState<RoleTab>('DEFENDANT');

  const trustMetrics = [
    {
      value: '⚖️ Butoni Analizë',
      title: 'Raporti Suprem i Fashikullit',
      desc: 'Një klik — analiza e thellë e gjithë sagës shumëvjeçare me standardin e Gjykatës Supreme (KPK, KPPRK, LPK, LMD).',
      icon: FileSearch,
    },
    {
      value: '🔬 Butoni Forenzikë',
      title: 'Auditimi i 1 Dokumenti',
      desc: 'Zbulon shkeljet Contra Legem, afatet prekluzive, ligjshmërinë e provave dhe auditon petitumin.',
      icon: Scale,
    },
    {
      value: 'Audio & Video 🎙️',
      title: 'Transkriptim Verbatim',
      desc: 'Transkriptim fjalë-për-fjalë me sekonda [MM:SS] i të gjitha provave materiale audio/video.',
      icon: Mic,
    },
    {
      value: '100% e Verifikueshme',
      title: '5,024 Nene të Plota',
      desc: 'Baza statutore dhe jurisprudenca e plotë e Republikës së Kosovës.',
      icon: FileCheck2,
    },
  ];

  const rolePillars = {
    DEFENDANT: {
      roleTitle: 'I PADITUR / I PANDEHUR (MBROJTJE STRATEGJIKE)',
      badge: 'STRATEGJIA E MBROJTJES',
      badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
      icon: Shield,
      pillars: [
        {
          num: '01',
          title: 'Zbulimi i Shkeljeve & Prapadatimeve',
          desc: 'Evidenton mospërputhjet e datave në procesverbale, tejkalimin e afateve dhe shkeljen e rehabilitimit ligjor (Neni 93 KPK).',
          code: 'KPK / KPPRK 384',
        },
        {
          num: '02',
          title: 'Ballafaqimi me Provat Shkencore',
          desc: 'Krahason raportet zyrtare e laboratorike me pretendimet e rreme gojore të palës kundërshtare.',
          code: 'NENI 257 KPPRK',
        },
        {
          num: '03',
          title: 'Pyetësori Taktik për Seancë (Cross-Exam)',
          desc: 'Përgatit pyetje kirurgjike të strukturuara në thonjëza për ballafaqimin e dëshmitarëve dhe ekspertëve.',
          code: 'BALLAFAQIMI',
        },
        {
          num: '04',
          title: 'Mjetet e Jashtëzakonshme & Kallëzimi Penal',
          desc: 'Aktivizon Revizionin, Mbrojtjen e Ligjshmërisë dhe Kallëzimin Penal në PSRK (Nenet 414 & 425 KPK).',
          code: 'PSRK / SUPREME',
        },
      ],
    },
    PLAINTIFF: {
      roleTitle: 'PADITËSI / I DËMTUAR (PADIA & NDJEKJA)',
      badge: 'STRATEGJIA E PADISË',
      badgeColor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
      icon: Swords,
      pillars: [
        {
          num: '01',
          title: 'Ndërtimi i Padisë dhe Përgjegjësisë',
          desc: 'Strukturon bazën e pakontestueshme faktike, dëmet e shkaktuara dhe inventarin e provave shkresore.',
          code: 'BAZA E PADISË',
        },
        {
          num: '02',
          title: 'Kërkesat për Masa Emergjente Mbrojtëse',
          desc: 'Formulon propozimet për sigurimin e kërkesëpadisë, masat e përkohshme dhe urdhrat emergjentë.',
          code: 'MASAT E SIGURIMIT',
        },
        {
          num: '03',
          title: 'Pyetjet Taktike për Zbardhjen e Fakteve',
          desc: 'Gjeneron pyetje të qarta për të ekspozuar mashtrimin para trupit gjykues në shqyrtim kryesor.',
          code: 'PYETËSORI',
        },
        {
          num: '04',
          title: 'Llogaritja e Dëmit dhe Kamata Ligjore',
          desc: 'Llogarit saktë dëmet materiale dhe jomateriale sipas LMD-së me kamatën ligjore përkatëse.',
          code: 'LMD / DËMET',
        },
      ],
    },
    NEUTRAL: {
      roleTitle: 'GJYQTAR / ARBITËR / EKSPERT LIGJOR',
      badge: 'AUDITIMI OBJEKTIV',
      badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
      icon: Scale,
      pillars: [
        {
          num: '01',
          title: 'Detektori i Kontradiktave në Fashikull',
          desc: 'Krahason pretendimet e të dyja palëve me provat shkencore dhe evidenton mospërputhjet materiale.',
          code: 'KRYQËZIMI FAKTIK',
        },
        {
          num: '02',
          title: 'Vlerësimi i Barrës së Provës',
          desc: 'Analizon paanshëm ligjshmërinë e administrimit të provave sipas Neneve 7, 8 dhe 319 të LPK-së.',
          code: 'BARRA E PROVËS',
        },
        {
          num: '03',
          title: 'Pyetjet Sqaruese Doktrinare',
          desc: 'Formulon pyetje objektive për të eliminuar paqartësitë gjatë marrjes në pyetje.',
          code: 'SQARIM FAKTESH',
        },
        {
          num: '04',
          title: 'Memorandumi Doktrinar i Çështjes',
          desc: 'Përgatit një sintezë të balancuar për vendimmarrje gjyqësore të qëndrueshme në Apel.',
          code: 'SINTEZA SUPREME',
        },
      ],
    },
  };

  const bentoFeatures = [
    {
      colSpan: 'lg:col-span-12',
      title: '⚖️ Butoni Analizë — Ish-Gjyqtari i Gjykatës Supreme në Zyrën Tuaj',
      subtitle: 'ANALIZË GJITHËPËRFSHIRËSE E TË GJITHË FASHIKULLIT',
      desc: 'Ngarkoni të gjithë fashikullin e lëndës (Policia, QPS, Psikiatria Forenzike, Seancat, Apeli). Motori Tier-1 (Claude 3.5 Sonnet) kryqëzon të gjitha shkresat, zbulon shkeljet e fshehura me dashje (Nenet 414 & 425 KPK), vlerëson afatet e mbetura dhe ndërton Master Planin e Fitores me hapa të numëruar.',
      icon: FileSearch,
      gradient: 'from-amber-500/20 via-primary-start/15 to-transparent',
      borderColor: 'border-amber-500/40',
    },
    {
      colSpan: 'lg:col-span-6',
      title: '🔬 Butoni Forenzikë — Auditim Kirurgjikal i 1 Dokumenti',
      subtitle: 'SINGLE DOCUMENT FORENSIC AUDIT',
      desc: 'Keni marrë një Aktgjykim, Padi, Kallëzim Penal apo Kontratë? Klikoni mbi dokumentin dhe merrni auditimin nen-për-nen: zbulon gabimet Contra Legem, afatet prekluzive, kontrollon ekzekutueshmërinë e Petitumit dhe ju jep tekstin e korrigjuar gati për gjykatë.',
      icon: Scale,
      gradient: 'from-blue-500/20 via-cyan-500/10 to-transparent',
      borderColor: 'border-blue-500/40',
    },
    {
      colSpan: 'lg:col-span-6',
      title: '🎙️ Forenzika & Transkriptimi i Provave Audio dhe Video',
      subtitle: 'VERBATIM MULTIMEDIA FORENSICS',
      desc: 'Ngarkoni regjistrime audio dhe video. Motori Whisper nxjerr transkriptin zyrtar 100% fjalë për fjalë me sekonda [MM:SS], duke indeksuar çdo dëshmi si provë materiale të pakontestueshme për gjykatë.',
      icon: Film,
      gradient: 'from-rose-500/20 via-purple-500/10 to-transparent',
      borderColor: 'border-rose-500/40',
    },
    {
      colSpan: 'lg:col-span-12',
      title: '📚 Biblioteka Ligjore e Kosovës me 5,024 Nene & Vendime të Gjykatës Supreme',
      subtitle: 'LEGJISLACIONI POZITIV I KOSOVËS',
      desc: 'Baza e plotë e diturisë: Kodi i ri i Procedurës Penale (Nr. 08/L-032), Kodi Penal (Nr. 06/L-074), LPK, LMD, Ligji për Familjen dhe vendimet parimore të Gjykatës Supreme të Kosovës.',
      icon: BookOpen,
      gradient: 'from-emerald-500/15 via-teal-500/5 to-transparent',
      borderColor: 'border-emerald-500/30',
    },
  ];

  const securityFeatures = [
    {
      title: 'Privatësi e Plotë e të Dhënave',
      desc: 'Dokumentet dhe shkresat e fashikullit tuaj mbeten 100% konfidenciale.',
      icon: Lock,
    },
    {
      title: 'Enkriptim i Standardit Bankar',
      desc: 'Çdo skedar dhe transaksion mbrohet me enkriptim ushtarak AES-256.',
      icon: Shield,
    },
    {
      title: 'Izolim Hermetik i Lëndëve',
      desc: 'Çdo lëndë është e izoluar me Zero-Leakage midis përdoruesve.',
      icon: Database,
    },
    {
      title: 'Përputhshmëri me Ligjin e Kosovës',
      desc: 'Ndërtuar në përputhje me Ligjin Nr. 06/L-082 për Mbrojtjen e të Dhënave Personale.',
      icon: CheckCircle2,
    },
  ];

  return (
    <div className="min-h-screen bg-canvas text-text-primary selection:bg-primary-start selection:text-white font-sans">
      
      {/* NAVIGATION */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-canvas/95 backdrop-blur-xl border-b border-main">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BrandLogo />
          </div>
          <div className="hidden md:flex items-center gap-6 text-xs font-bold uppercase tracking-wider text-text-muted">
            <a href="#metrics" className="hover:text-text-primary transition-colors">Veçoritë</a>
            <a href="#pillars" className="hover:text-text-primary transition-colors">4 Shtyllat</a>
            <a href="#arsenal" className="hover:text-text-primary transition-colors">Motorët Elitarë</a>
            <a href="#pricing" className="hover:text-text-primary text-primary-start transition-colors">Çmimet & Planet</a>
            <a href="#security" className="hover:text-text-primary transition-colors">Siguria</a>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/login')} className="px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:bg-hover transition-all cursor-pointer">
              {t('auth.login', 'Hyr')}
            </button>
            <button onClick={() => navigate('/register')} className="px-4.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider bg-primary-start hover:bg-primary-start/90 text-white shadow-md shadow-primary-start/20 transition-all active:scale-95 cursor-pointer">
              Fillo Tani
            </button>
          </div>
        </div>
      </nav>

      {/* HERO SECTION */}
      <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28 overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-primary-start/15 blur-[120px] rounded-full pointer-events-none" />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-6 sm:space-y-8">
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-start/10 border border-primary-start/25 text-primary-start text-[11px] sm:text-xs font-bold uppercase tracking-widest shadow-xs">
            <Sparkles size={14} className="animate-pulse text-amber-500" />
            <span>Platforma Supreme e Inteligjencës Ligjore në Kosovë</span>
          </motion.div>
          
          <motion.h1 initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-3xl sm:text-5xl md:text-6xl font-black text-text-primary tracking-tight leading-[1.15] max-w-4xl mx-auto">
            Fuqia e Gjykatës Supreme në{' '}
            <span className="bg-gradient-to-r from-primary-start via-indigo-500 to-amber-500 bg-clip-text text-transparent">
              Zyrën Tuaj Ligjore
            </span>
          </motion.h1>
          
          <motion.p initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="text-sm sm:text-base md:text-lg text-text-secondary leading-relaxed max-w-3xl mx-auto font-normal">
            Zbardhni të vërtetën e fashikullit me dy motorët tanë elitarë: <strong>Butoni Analizë</strong> për kryqëzimin e të gjithë historikut gjyqësor dhe <strong>Butoni Forenzikë</strong> për auditimin kirurgjikal të çdo dokumenti.
          </motion.p>
          
          <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-2">
            <button onClick={() => navigate('/register')} className="w-full sm:w-auto h-12 px-8 rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2.5 shadow-xl shadow-primary-start/25 hover:scale-[1.02] active:scale-95 transition-all cursor-pointer">
              <span>Hap Llogari & Analizo Rastin</span>
              <ArrowRight size={16} />
            </button>
            <a href="#pricing" className="w-full sm:w-auto h-12 px-7 rounded-2xl bg-surface hover:bg-hover border border-main text-text-primary font-bold text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 transition-all">
              <span>Shiko Çmimet</span>
            </a>
          </motion.div>
        </div>
      </section>

      {/* TRUST METRICS */}
      <section id="metrics" className="py-12 border-y border-main bg-surface/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {trustMetrics.map((m, i) => {
              const IconComp = m.icon;
              return (
                <div key={i} className="p-5 rounded-2xl bg-card border border-main shadow-xs flex items-start gap-4 hover:border-primary-start/40 transition-colors">
                  <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center shrink-0 border border-primary-start/20">
                    <IconComp size={20} />
                  </div>
                  <div className="space-y-1 min-w-0">
                    <span className="text-xs font-bold uppercase text-primary-start tracking-wider block">{m.value}</span>
                    <h4 className="text-sm font-bold text-text-primary truncate">{m.title}</h4>
                    <p className="text-xs text-text-secondary leading-snug">{m.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4 SHTYLLAT SIPAS ROLIT */}
      <section id="pillars" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-4 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-primary-start">STRUKTURA PROCEDURALE</span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">4 Shtyllat sipas Rolit në Çështje</h2>
            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">Përshtatni këndvështrimin e analizës sipas pozitës suaj procedurale në gjykatë.</p>
            <div className="inline-flex p-1.5 rounded-2xl bg-surface border border-main shadow-sm gap-1.5 mt-4">
              <button onClick={() => setActiveRole('DEFENDANT')} className={`px-4 sm:px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer ${activeRole === 'DEFENDANT' ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20' : 'text-text-muted hover:text-text-primary'}`}>
                <Shield size={14} /> I Paditur / Mbrojtje
              </button>
              <button onClick={() => setActiveRole('PLAINTIFF')} className={`px-4 sm:px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer ${activeRole === 'PLAINTIFF' ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20' : 'text-text-muted hover:text-text-primary'}`}>
                <Swords size={14} /> Paditës / Sulm
              </button>
              <button onClick={() => setActiveRole('NEUTRAL')} className={`px-4 sm:px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer ${activeRole === 'NEUTRAL' ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20' : 'text-text-muted hover:text-text-primary'}`}>
                <Scale size={14} /> Neutral / Gjykata
              </button>
            </div>
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={activeRole} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.25 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {rolePillars[activeRole].pillars.map((p, idx) => (
                <div key={idx} className="p-6 rounded-3xl bg-card border border-main shadow-xs flex flex-col justify-between gap-6 hover:border-primary-start/50 hover:shadow-lg transition-all">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-black font-mono text-primary-start/40">{p.num}</span>
                      <span className="text-[9px] font-bold uppercase font-mono px-2 py-0.5 rounded-md bg-surface border border-main text-text-muted">{p.code}</span>
                    </div>
                    <h3 className="text-base font-bold text-text-primary leading-snug">{p.title}</h3>
                    <p className="text-xs text-text-secondary leading-relaxed font-normal">{p.desc}</p>
                  </div>
                  <div className="pt-4 border-t border-main/60 flex items-center justify-between text-xs font-bold text-primary-start">
                    <span>Shiko në Platformë</span>
                    <ArrowRight size={13} />
                  </div>
                </div>
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      </section>

      {/* ARSENALI I MOTORËVE ELITARË */}
      <section id="arsenal" className="py-24 border-t border-main bg-surface/30 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500">MOTORËT ELITARË</span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">Analizë & Forenzikë e Nivelit Suprem</h2>
            <p className="text-xs sm:text-sm text-text-secondary">Teknologji e kalibruar për drejtësinë e Kosovës me modelet më të avancuara në botë.</p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {bentoFeatures.map((b, i) => {
              const IconComponent = b.icon;
              return (
                <div key={i} className={`${b.colSpan} p-7 sm:p-9 rounded-3xl bg-card border ${b.borderColor} shadow-xs relative overflow-hidden flex flex-col justify-between gap-6 hover:shadow-xl transition-all duration-300`}>
                  <div className={`absolute inset-0 bg-gradient-to-br ${b.gradient} pointer-events-none`} />
                  <div className="relative z-10 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="w-12 h-12 rounded-2xl bg-surface border border-main flex items-center justify-center text-primary-start shadow-xs">
                        <IconComponent size={22} />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted font-mono">{b.subtitle}</span>
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-text-primary tracking-tight leading-snug">{b.title}</h3>
                    <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">{b.desc}</p>
                  </div>
                  <div className="relative z-10 pt-4 border-t border-main/60 flex items-center gap-2 text-xs font-bold text-primary-start">
                    <span>Mëso më shumë</span>
                    <ChevronRight size={14} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 💰 ÇMIMET DHE PLANET E REJA */}
      {/* ========================================================================= */}
      <section id="pricing" className="py-24 border-t border-main bg-canvas relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-primary-start">PLANET & ÇMIMET TRANZPARENTE</span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">Zgjidhni Zgjidhjen Tuaj Ligjore</h2>
            <p className="text-xs sm:text-sm text-text-secondary">Nga qytetarët që kërkojnë analizën e një rasti të vetëm, deri te zyrat e mëdha të avokatisë.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-4">
            
            {/* KARTA 1: QYTETARËT (ONE-TIME PASS) */}
            <div className="p-8 rounded-3xl bg-card border border-main shadow-md flex flex-col justify-between hover:border-primary-start/40 transition-all relative">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-text-muted bg-surface px-3 py-1 rounded-lg border border-main">
                    Për Qytetarët
                  </span>
                  <UserIcon className="w-5 h-5 text-text-muted" />
                </div>
                <div>
                  <h3 className="text-xl font-black text-text-primary">One-Time Pass</h3>
                  <p className="text-xs text-text-secondary mt-1">Zgjidhje e plotë për 1 lëndë të vetme gjyqësore.</p>
                </div>
                <div className="flex items-baseline gap-1 pt-2">
                  <span className="text-4xl font-black text-text-primary">19.99 €</span>
                  <span className="text-xs text-text-muted font-bold">/ pagesë njëherëshe</span>
                </div>

                <div className="space-y-3 pt-4 border-t border-main text-xs text-text-secondary">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span><strong>1 Lëndë e Plotë</strong> (E vlefshme përgjithmonë)</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Analiza Supreme me Claude 3.5 Sonnet</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Zbulimi i shkeljeve <strong>Contra Legem</strong></span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Skanim deri në 200 faqe & Audio me sekonda</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Raporti zyrtar në PDF i gatshëm për gjykatë</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => navigate('/register')}
                className="w-full h-12 mt-8 rounded-xl bg-surface hover:bg-hover border border-main text-text-primary font-bold text-xs uppercase tracking-wider transition-all focus:outline-none cursor-pointer"
              >
                Zhblloko 1 Lëndë Tani
              </button>
            </div>

            {/* KARTA 2: AVOKAT SOLO (MË I POPULLARIZUARI) */}
            <div className="p-8 rounded-3xl bg-gradient-to-b from-primary-start/10 via-card to-card border-2 border-primary-start shadow-xl flex flex-col justify-between relative transform lg:-translate-y-2">
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-primary-start text-white text-[10px] font-black uppercase tracking-widest px-4 py-1 rounded-full shadow-md">
                ⭐ Zgjedhja e Avokatëve
              </div>

              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-primary-start bg-primary-start/10 px-3 py-1 rounded-lg border border-primary-start/30">
                    Avokat Individual
                  </span>
                  <Scale className="w-5 h-5 text-primary-start" />
                </div>
                <div>
                  <h3 className="text-xl font-black text-text-primary">Solo Plan</h3>
                  <p className="text-xs text-text-secondary mt-1">Për avokatë të pavarur me shumë çështje aktive.</p>
                </div>
                <div className="flex items-baseline gap-1 pt-2">
                  <span className="text-4xl font-black text-text-primary">49.99 €</span>
                  <span className="text-xs text-text-muted font-bold">/ muaj</span>
                </div>

                <div className="space-y-3 pt-4 border-t border-main text-xs text-text-secondary">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-primary-start shrink-0" />
                    <span><strong>Lëndë të Pakufizuara</strong> çdo muaj</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-primary-start shrink-0" />
                    <span>Analiza e thellë materiale & procedurale</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-primary-start shrink-0" />
                    <span>Hartim automatik i Padive, Ankesave & Prapësimeve</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-primary-start shrink-0" />
                    <span>Chati inteligjent me Sokrati AI (DeepSeek-V3)</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-primary-start shrink-0" />
                    <span>Menaxhimi i financave dhe faturimit të zyrës</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => navigate('/register')}
                className="w-full h-12 mt-8 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-lg shadow-primary-start/20 transition-all focus:outline-none cursor-pointer"
              >
                Fillo me Solo Plan
              </button>
            </div>

            {/* KARTA 3: ZYRA AVOKATIE (TEAM PLAN) */}
            <div className="p-8 rounded-3xl bg-card border border-main shadow-md flex flex-col justify-between hover:border-primary-start/40 transition-all relative">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-text-muted bg-surface px-3 py-1 rounded-lg border border-main">
                    Firma & Zyra Ligjore
                  </span>
                  <Building2 className="w-5 h-5 text-text-muted" />
                </div>
                <div>
                  <h3 className="text-xl font-black text-text-primary">Team Plan</h3>
                  <p className="text-xs text-text-secondary mt-1">Bashkëpunim në ekip për zyra me disa avokatë.</p>
                </div>
                <div className="flex items-baseline gap-1 pt-2">
                  <span className="text-4xl font-black text-text-primary">99.99 €</span>
                  <span className="text-xs text-text-muted font-bold">/ muaj</span>
                </div>

                <div className="space-y-3 pt-4 border-t border-main text-xs text-text-secondary">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span><strong>Deri në 5 Avokatë / Vende</strong> në ekip</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Fashikuj dhe dosje të përbashkëta</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Kalendari dhe afatet e seancave për të gjithë ekipin</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Përpunim me prioritet maksimal Tier-1</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-success-start shrink-0" />
                    <span>Mbështetje e dedikuar 24/7</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => navigate('/register')}
                className="w-full h-12 mt-8 rounded-xl bg-surface hover:bg-hover border border-main text-text-primary font-bold text-xs uppercase tracking-wider transition-all focus:outline-none cursor-pointer"
              >
                Regjistro Ekipin Tuaj
              </button>
            </div>

          </div>

          {/* PAYMENT BADGES BANNER */}
          <div className="p-6 rounded-2xl bg-surface/60 border border-main flex flex-wrap items-center justify-between gap-4 select-none">
            <div className="flex items-center gap-2 text-xs font-bold text-text-primary">
              <CreditCard className="w-4 h-4 text-primary-start" />
              <span>Mënyrat e Pagesës në Kosovë:</span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs font-semibold text-text-secondary">
              <span className="px-3 py-1 bg-card border border-main rounded-lg flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5 text-blue-500" /> Visa & Mastercard
              </span>
              <span className="px-3 py-1 bg-card border border-main rounded-lg flex items-center gap-1.5">
                <Smartphone className="w-3.5 h-3.5 text-amber-500" /> Raiffeisen Bank (m-Banking)
              </span>
              <span className="px-3 py-1 bg-card border border-main rounded-lg flex items-center gap-1.5">
                <Banknote className="w-3.5 h-3.5 text-emerald-500" /> Para në dorë (Cash në Zyrë)
              </span>
            </div>
          </div>

        </div>
      </section>

      {/* SIGURIA DHE PRIVATËSIA */}
      <section id="security" className="py-24 border-t border-main bg-surface/30 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-status-success">SIGURIA DHE PRIVATËSIA</span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">Mbrojtja e të Dhënave Ligjore</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {securityFeatures.map((sec, idx) => {
              const SecIcon = sec.icon;
              return (
                <div key={idx} className="p-6 rounded-3xl bg-surface border border-main flex flex-col justify-between gap-4 hover:border-status-success/40 transition-colors">
                  <div className="w-10 h-10 rounded-xl bg-status-success/10 text-status-success flex items-center justify-center border border-status-success/20">
                    <SecIcon size={20} />
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-bold text-text-primary">{sec.title}</h4>
                    <p className="text-xs text-text-secondary leading-relaxed">{sec.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* BOTTOM CTA */}
      <section className="py-20 border-t border-main bg-gradient-to-b from-surface/50 to-canvas text-center relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 relative z-10">
          <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">Gati për të Fituar Çështjen Tuaj?</h2>
          <p className="text-xs sm:text-sm text-text-secondary max-w-xl mx-auto leading-relaxed">Ngarkoni fashikullin dhe merrni menjëherë Analizën e plotë të Gjykatës Supreme.</p>
          <div className="pt-2">
            <button onClick={() => navigate('/register')} className="h-12 px-9 rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs sm:text-sm uppercase tracking-wider shadow-xl shadow-primary-start/30 transition-all hover:scale-105 active:scale-95 cursor-pointer">
              Fillo Tani
            </button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-8 border-t border-main bg-canvas text-center text-xs text-text-muted">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© {new Date().getFullYear()} Juristi AI / Advocatus. Të gjitha të drejtat të rezervuara.</p>
          <div className="flex gap-6 text-text-muted">
            <a href="/privacy" className="hover:text-text-primary transition-colors">Privatësia</a>
            <a href="/support" className="hover:text-text-primary transition-colors">Mbështetja</a>
            <a href="/laws/search" className="hover:text-text-primary transition-colors">Biblioteka Ligjore</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;