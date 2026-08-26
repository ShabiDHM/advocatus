// FILE: src/pages/LandingPage.tsx
// PHOENIX PROTOCOL - JURISTI.TECH LANDING PAGE V15.1 (0 WARNINGS & CLEAN IMPORTS)

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  Scale,
  Swords,
  Sparkles,
  Search,
  CheckCircle2,
  Lock,
  ArrowRight,
  ShieldCheck,
  ChevronRight,
  Database,
  FileCheck2,
  Film,
  BookOpen,
  Gavel
} from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

type RoleTab = 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL';

export const LandingPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeRole, setActiveRole] = useState<RoleTab>('DEFENDANT');

  const trustMetrics = [
    {
      value: '700+ Faqe',
      title: 'Jurisprudencë Supreme',
      desc: 'Vendimet parimore dhe Aktgjykimet e Kolegjit Penal të Gjykatës Supreme.',
      icon: Gavel,
    },
    {
      value: '1-Kliko ⚖️',
      title: 'Forenzika Ligjore',
      desc: 'Skanim i neneve, zbulimi i lapsuseve dhe verifikimi me Gazetën Zyrtare.',
      icon: Scale,
    },
    {
      value: '100% e Verifikueshme',
      title: 'Burime të Qarta',
      desc: 'Çdo përgjigje shoqërohet me referencën e nenit dhe dokumentit.',
      icon: FileCheck2,
    },
    {
      value: 'Taktikë Procedurale',
      title: 'Përvojë Praktike',
      desc: 'Strukturuar posaçërisht për procedurat gjyqësore në Kosovë.',
      icon: ShieldCheck,
    },
  ];

  const rolePillars = {
    DEFENDANT: {
      roleTitle: 'I PADITUR / MBROJTJE GJYQËSORE',
      badge: 'STRATEGJIA E MBROJTJES',
      badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
      icon: Shield,
      pillars: [
        {
          num: '01',
          title: 'Zbulimi i Mospërputhjeve dhe Datave',
          desc: 'Evidenton mospërputhjet e datave në procesverbale, tejkalimin e afateve prekluzive dhe zbatimin e rehabilitimit ligjor (Neni 93 i KPRK-së).',
          code: 'KPRK 93 / 427',
        },
        {
          num: '02',
          title: 'Ballafaqimi me Shkresat e Fashikullit',
          desc: 'Krahason raportet zyrtare dhe laboratorike me pretendimet gojore për të vërtetuar prapësimet ligjore dhe të pavërtetat.',
          code: 'KPRK 387 / LPK',
        },
        {
          num: '03',
          title: 'Kryqëzimi i Dëshmitarëve (Pyetësori Taktik)',
          desc: 'Përgatit pyetje të strukturuara për ballafaqimin e dëshmitarëve dhe ekspertëve gjatë marrjes në pyetje në seancë.',
          code: 'SEANCA GJYQËSORE',
        },
        {
          num: '04',
          title: 'Strategjia e Prapësimit dhe Kundërpadisë',
          desc: 'Ndërton përmbledhjen mbi prapësimet procedurale, mungesën e legjitimitetit aktiv dhe hapat për rrëzimin e kërkesëpadisë.',
          code: 'LPK / LMD',
        },
      ],
    },
    PLAINTIFF: {
      roleTitle: 'PADITËSI / SULMI PROCEDURAL',
      badge: 'STRATEGJIA E PADISË',
      badgeColor: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30',
      icon: Swords,
      pillars: [
        {
          num: '01',
          title: 'Përcaktimi i Përgjegjësisë dhe Detyrimit',
          desc: 'Strukturon bazën faktike dhe provat shkresore që mbështesin kërkesëpadinë dhe vërtetojnë detyrimin e palës kundërshtare.',
          code: 'BAZA E PADISË',
        },
        {
          num: '02',
          title: 'Kërkesat për Masa Emergjente Mbrojtëse',
          desc: 'Formulon propozimet për masa të përkohshme të sigurisë, sigurimin e kërkesëpadisë dhe mbrojtjen e të drejtave të palës.',
          code: 'KPPRK 188 / LPK',
        },
        {
          num: '03',
          title: 'Pyetjet Taktike për Seancë',
          desc: 'Gjeneron pyetje të qarta të bazuara në shkresat e fashikullit për të qartësuar faktet kontestuese para gjykatës.',
          code: 'PROVA MATRIKS',
        },
        {
          num: '04',
          title: 'Llogaritja e Dëmit dhe Përmbledhja',
          desc: 'Ndihmon në përllogaritjen e dëmeve materiale e jomateriale sipas LMD-së dhe përgatit përmbledhjen ekzekutive.',
          code: 'LMD 136 / DËMET',
        },
      ],
    },
    NEUTRAL: {
      roleTitle: 'EKSPERTI / GJYKATA / NDËRMJETËSIMI',
      badge: 'AUDITIMI OBJEKTIV',
      badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
      icon: Scale,
      pillars: [
        {
          num: '01',
          title: 'Detektori i Kontradiktave në Shkresa',
          desc: 'Krahason pretendimet e palëve me provat e administruara dhe evidenton mospërputhjet në deklarata.',
          code: 'KONTROLLI FAKTIK',
        },
        {
          num: '02',
          title: 'Barra e Provës dhe Ligji Procedural',
          desc: 'Analizon paanshëm barrën e provimit (kush duhet të provojë çfarë) sipas dispozitave të procedurës kontestimore.',
          code: 'BARRA E PROVËS',
        },
        {
          num: '03',
          title: 'Pyetjet Sqaruese për Zbardhjen e Fakteve',
          desc: 'Formulon pyetje objektive për të eliminuar paqartësitë dhe për të ndihmuar në administrimin e drejtë të provave.',
          code: 'SQARIM FAKTESH',
        },
        {
          num: '04',
          title: 'Memorandumi i Paanshëm i Çështjes',
          desc: 'Përgatit një sintezë të balancuar për të lehtësuar vendimmarrjen gjyqësore apo marrëveshjen me ndërmjetësim.',
          code: 'SINTEZA E LËNDËS',
        },
      ],
    },
  };

  const bentoFeatures = [
    {
      colSpan: 'lg:col-span-12',
      title: '⚖️ Forenzika Ligjore me 1-Klikim & Jurisprudenca Supreme (700+ Faqe)',
      subtitle: '1-CLICK STATUTORY FORENSICS',
      desc: 'Klikoni mbi çdo dokument në fashikull për të kryer auditimin e thellë ligjor: sistemi skanon provat, lidh çdo shkelje me nenet përkatëse të ligjeve të Kosovës (KPRK, KPPRK, LPK, LMD), zbulon automatikisht lapsuset e neneve apo referencat e gabuara, dhe nxjerr opinionin e Gjykatës Supreme të Kosovës bazuar në 700+ faqe të vendimeve të Kolegjit Penal e Civil (Aktgjykimet PML).',
      icon: Scale,
      gradient: 'from-amber-500/20 via-primary-start/15 to-transparent',
      borderColor: 'border-amber-500/40',
    },
    {
      colSpan: 'lg:col-span-8',
      title: 'Sokrati AI — Asistenti Inteligjent i Lëndës',
      subtitle: '4 SHTYLLAT PROCEDURALE',
      desc: 'Bashkëbisedoni direkt me dosjen tuaj. Sokrati nxjerr menjëherë 4 shtyllat kryesore sipas rolit tuaj procedural, analizon prapësimet dhe përgatit pyetësorët taktikë për seancë me citime ekzakte të neneve.',
      icon: Sparkles,
      gradient: 'from-primary-start/15 via-indigo-500/5 to-transparent',
      borderColor: 'border-primary-start/30',
    },
    {
      colSpan: 'lg:col-span-4',
      title: 'Leximi OCR i Shkresave të Skanuara',
      subtitle: 'DIGJITALIZIM NË ~3.5S',
      desc: 'Përpunon procesverbalet, aktvendimet e vjetra dhe faturat e skanuara, duke i kthyer në tekst të kërkueshëm me referenca faqe-për-faqe.',
      icon: Search,
      gradient: 'from-blue-500/15 via-cyan-500/5 to-transparent',
      borderColor: 'border-blue-500/30',
    },
    {
      colSpan: 'lg:col-span-4',
      title: 'Transkriptimi i Skedarëve Audio & Video',
      subtitle: 'MULTIMEDIA EVIDENCE',
      desc: 'Ngarkoni regjistrime audio apo video (MP3, WAV, MP4). Sistemi gjeneron transkriptin e plotë tekstual gati për referim në gjykatë.',
      icon: Film,
      gradient: 'from-rose-500/15 via-purple-500/5 to-transparent',
      borderColor: 'border-rose-500/30',
    },
    {
      colSpan: 'lg:col-span-8',
      title: 'Biblioteka Ligjore e Kosovës me Kërkim Semantik',
      subtitle: 'STATUTET ZYRTARE NË KOSOVË',
      desc: 'Qasje e menjëhershme në ligjet zyrtare të Kosovës me të gjitha nenet e indeksuara. Çdo referencë e cituar nga Sokrati hapet direkt në shikuesin e plotë PDF me kërcim automatik te neni përkatës.',
      icon: BookOpen,
      gradient: 'from-emerald-500/15 via-teal-500/5 to-transparent',
      borderColor: 'border-emerald-500/30',
    },
  ];

  const securityFeatures = [
    {
      title: 'Privatësi e Plotë e të Dhënave',
      desc: 'Dokumentet dhe shkresat e fashikullit tuaj mbeten private dhe nuk përdoren kurrë për trajnim publik.',
      icon: Lock,
    },
    {
      title: 'Enkriptim i Standardit të Lartë',
      desc: 'Çdo skedar në fashikull dhe çdo informacion i ruajtur mbrohet me enkriptim të avancuar AES-256.',
      icon: Shield,
    },
    {
      title: 'Fshirje e Menjëhershme',
      desc: 'Kur fshini një lëndë ose dokument, të gjitha të dhënat dhe kopjet e tyre fshihen përfundimisht nga serverët.',
      icon: Database,
    },
    {
      title: 'Përputhshmëri me Ligjin e Kosovës',
      desc: 'Ndërtuar në respektim të plotë të Ligjit Nr. 06/L-082 për Mbrojtjen e të Dhënave Personale.',
      icon: CheckCircle2,
    },
  ];

  return (
    <div className="min-h-screen bg-canvas text-text-primary selection:bg-primary-start selection:text-white font-sans">
      {/* 1. TOP NAVIGATION */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-canvas/95 backdrop-blur-xl border-b border-main">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BrandLogo />
          </div>

          <div className="hidden md:flex items-center gap-6 text-xs font-bold uppercase tracking-wider text-text-muted">
            <a href="#metrics" className="hover:text-text-primary transition-colors">Veçoritë</a>
            <a href="#pillars" className="hover:text-text-primary transition-colors">4 Shtyllat</a>
            <a href="#arsenal" className="hover:text-text-primary transition-colors">Forenzika</a>
            <a href="#security" className="hover:text-text-primary transition-colors">Siguria</a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:bg-hover transition-all cursor-pointer"
            >
              {t('auth.login', 'Hyr')}
            </button>
            <button
              onClick={() => navigate('/register')}
              className="px-4.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider bg-primary-start hover:bg-primary-start/90 text-white shadow-md shadow-primary-start/20 transition-all active:scale-95 cursor-pointer"
            >
              Fillo Falas
            </button>
          </div>
        </div>
      </nav>

      {/* 2. HERO SECTION */}
      <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28 overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-primary-start/15 blur-[120px] rounded-full pointer-events-none" />

        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-6 sm:space-y-8">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-start/10 border border-primary-start/25 text-primary-start text-[11px] sm:text-xs font-bold uppercase tracking-widest shadow-xs"
          >
            <Scale size={14} className="animate-pulse text-amber-500" />
            <span>Forenzikë Ligjore & Jurisprudenca e Gjykatës Supreme të Kosovës</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-3xl sm:text-5xl md:text-6xl font-black text-text-primary tracking-tight leading-[1.15] max-w-4xl mx-auto"
          >
            Forenzika dhe Strategjia Procedurale e{' '}
            <span className="bg-gradient-to-r from-primary-start via-indigo-500 to-amber-500 bg-clip-text text-transparent">
              Zyrës Suaj Ligjore
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-sm sm:text-base md:text-lg text-text-secondary leading-relaxed max-w-3xl mx-auto font-normal"
          >
            Auditim i saktë i çdo shkrese, zbulim i lapsuseve statutare dhe lidhje e menjëhershme me <strong>700+ faqe të vendimeve të Gjykatës Supreme të Kosovës</strong>. 
            <strong> Juristi.tech</strong> fuqizon avokatët në analizën kirurgjikale të provave dhe përgatitjen e seancave sipas <strong>KPRK, KPPRK, LPK dhe LMD</strong>.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-3.5 pt-2"
          >
            <button
              onClick={() => navigate('/register')}
              className="w-full sm:w-auto h-12 px-8 rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2.5 shadow-xl shadow-primary-start/25 hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
            >
              <span>Provo Falas në 1 Lëndë</span>
              <ArrowRight size={16} />
            </button>
            <a
              href="#arsenal"
              className="w-full sm:w-auto h-12 px-8 rounded-2xl bg-surface hover:bg-hover text-text-primary font-bold text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 border border-main transition-all cursor-pointer"
            >
              <Scale size={16} className="text-amber-500" />
              <span>Shiko Forenzikën ⚖️</span>
            </a>
          </motion.div>
        </div>
      </section>

      {/* 3. TRUST METRICS BANNER */}
      <section id="metrics" className="py-12 border-y border-main bg-surface/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {trustMetrics.map((m, i) => {
              const IconComp = m.icon;
              return (
                <div
                  key={i}
                  className="p-5 rounded-2xl bg-card border border-main shadow-xs flex items-start gap-4 hover:border-primary-start/40 transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center shrink-0 border border-primary-start/20">
                    <IconComp size={20} />
                  </div>
                  <div className="space-y-1 min-w-0">
                    <span className="text-xs font-bold uppercase text-primary-start tracking-wider block">
                      {m.value}
                    </span>
                    <h4 className="text-sm font-bold text-text-primary truncate">{m.title}</h4>
                    <p className="text-xs text-text-secondary leading-snug">{m.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. THE 4 PILLARS BY PROCEDURAL ROLE */}
      <section id="pillars" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-4 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-primary-start">
              STRUKTURA PROCEDURALE
            </span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">
              4 Shtyllat sipas Rolit në Çështje
            </h2>
            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
              Përshtatni këndvështrimin e analizës sipas pozitës suaj procedurale në lëndë.
            </p>

            {/* Role Switcher */}
            <div className="inline-flex p-1.5 rounded-2xl bg-surface border border-main shadow-sm gap-1.5 mt-4">
              <button
                onClick={() => setActiveRole('DEFENDANT')}
                className={`px-4 sm:px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer ${
                  activeRole === 'DEFENDANT'
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                <Shield size={14} /> I Paditur / Mbrojtje
              </button>
              <button
                onClick={() => setActiveRole('PLAINTIFF')}
                className={`px-4 sm:px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer ${
                  activeRole === 'PLAINTIFF'
                    ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                <Swords size={14} /> Paditës / Sulm
              </button>
              <button
                onClick={() => setActiveRole('NEUTRAL')}
                className={`px-4 sm:px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer ${
                  activeRole === 'NEUTRAL'
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                <Scale size={14} /> Neutral / Gjykata
              </button>
            </div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeRole}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.25 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
            >
              {rolePillars[activeRole].pillars.map((p, idx) => (
                <div
                  key={idx}
                  className="p-6 rounded-3xl bg-card border border-main shadow-xs flex flex-col justify-between gap-6 hover:border-primary-start/50 hover:shadow-lg transition-all"
                >
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-2xl font-black font-mono text-primary-start/40">
                        {p.num}
                      </span>
                      <span className="text-[9px] font-bold uppercase font-mono px-2 py-0.5 rounded-md bg-surface border border-main text-text-muted">
                        {p.code}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-text-primary leading-snug">
                      {p.title}
                    </h3>
                    <p className="text-xs text-text-secondary leading-relaxed font-normal">
                      {p.desc}
                    </p>
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

      {/* 5. ARSENALI I VEÇORIVE REALE */}
      <section id="arsenal" className="py-24 border-t border-main bg-surface/30 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500">
              VEÇORITË KRYESORE FORENZIKE
            </span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">
              Mjetet për Punën Tuaj të Përditshme
            </h2>
            <p className="text-xs sm:text-sm text-text-secondary">
              Teknologji e avancuar forenzike e mbështetur në Gazetën Zyrtare dhe precedentët e Gjykatës Supreme të Kosovës.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {bentoFeatures.map((b, i) => {
              const IconComponent = b.icon;
              return (
                <div
                  key={i}
                  className={`${b.colSpan} p-7 sm:p-9 rounded-3xl bg-card border ${b.borderColor} shadow-xs relative overflow-hidden flex flex-col justify-between gap-6 hover:shadow-xl transition-all duration-300`}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${b.gradient} pointer-events-none`} />
                  
                  <div className="relative z-10 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="w-12 h-12 rounded-2xl bg-surface border border-main flex items-center justify-center text-primary-start shadow-xs">
                        <IconComponent size={22} className={b.subtitle.includes('FORENSICS') ? 'text-amber-500' : ''} />
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted font-mono">
                        {b.subtitle}
                      </span>
                    </div>

                    <h3 className="text-lg sm:text-xl font-bold text-text-primary tracking-tight leading-snug">
                      {b.title}
                    </h3>
                    <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
                      {b.desc}
                    </p>
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

      {/* 6. SECURITY & GDPR */}
      <section id="security" className="py-24 border-t border-main bg-canvas relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-status-success">
              SIGURIA DHE PRIVATËSIA
            </span>
            <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">
              Mbrojtja e të Dhënave dhe Konfidencialiteti
            </h2>
            <p className="text-xs sm:text-sm text-text-secondary">
              Besueshmëria dhe ruajtja e sekretit profesional janë parimi ynë kryesor.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {securityFeatures.map((sec, idx) => {
              const SecIcon = sec.icon;
              return (
                <div
                  key={idx}
                  className="p-6 rounded-3xl bg-surface border border-main flex flex-col justify-between gap-4 hover:border-status-success/40 transition-colors"
                >
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

      {/* 7. BOTTOM CTA */}
      <section className="py-20 border-t border-main bg-gradient-to-b from-surface/50 to-canvas text-center relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 relative z-10">
          <h2 className="text-2xl sm:text-4xl font-black text-text-primary tracking-tight">
            Gati për të Filluar?
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary max-w-xl mx-auto leading-relaxed">
            Ngarkoni fashikullin tuaj të parë dhe eksploroni mjetet ndihmëse për analizën e shkresave të lëndës.
          </p>
          <div className="pt-2">
            <button
              onClick={() => navigate('/register')}
              className="h-12 px-9 rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs sm:text-sm uppercase tracking-wider shadow-xl shadow-primary-start/30 transition-all hover:scale-105 active:scale-95 cursor-pointer"
            >
              Fillo Falas Tani
            </button>
          </div>
        </div>
      </section>

      {/* 8. FOOTER */}
      <footer className="py-8 border-t border-main bg-canvas text-center text-xs text-text-muted">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© {new Date().getFullYear()} Juristi.tech. Të gjitha të drejtat të rezervuara.</p>
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