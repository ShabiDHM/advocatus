// FILE: frontend/src/components/landing/ProductShowcase.tsx
// PHOENIX PROTOCOL - PRODUCT SHOWCASE V9.1 (0 WARNINGS - CLEAN IMPORTS)

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { 
    ShieldAlert, FileText, ScanEye, BrainCircuit, 
    CheckCircle, PenTool, 
    Sparkles, Calculator, Network, ArrowRight, AlertTriangle, ChevronRight,
    Scale, CheckCircle2
} from 'lucide-react';

const ProductShowcase = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState(0);

    // Auto-rotate slides every 8 seconds
    useEffect(() => {
        const timer = setInterval(() => {
            setActiveTab((prev) => (prev + 1) % 6);
        }, 8000);
        return () => clearInterval(timer);
    }, []);

    const features = [
        {
            id: 0,
            title: t('showcase.slide1_title', 'Dhoma e Luftës (War Room)'),
            desc: t('showcase.slide1_desc', 'Simulim i strategjisë së kundërshtarit, pyetje kryqëzuese dhe detektim automatik i kontradiktave.'),
            icon: <SwordsIcon className="w-5 h-5" />,
            badge: "ANALIZË ADVERSARE SOKRATIKE",
            color: "from-rose-600 to-red-600",
            mockup: <WarRoomMockup />
        },
        {
            id: 1,
            title: t('showcase.slide_ontology_title', 'Zero Halucinacione & Citime Zyrtare'),
            desc: t('showcase.slide_ontology_desc', 'Çdo citim lidhet drejtpërdrejt me nene zyrtare të Kosovës (LPK, LMD, LSHT). Avokati mbetet Kryeredaktori.'),
            icon: <CheckCircle2 className="w-5 h-5" />,
            badge: "VERIFIKIM ME LIGJET E KOSOVËS",
            color: "from-emerald-600 to-teal-600",
            mockup: <LegalGroundingMockup />
        },
        {
            id: 2,
            title: t('showcase.slide2_title', 'Leximi i Provave të Skanuara (HD OCR)'),
            desc: t('showcase.slide2_desc', 'Lexim me precizion i fotokopjeve të dëmtuara, vulave dhe kontratave të nënshkruara pa përzierje skedarësh.'),
            icon: <ScanEye className="w-5 h-5" />,
            badge: "KOSOVO SCANNED OCR HD",
            color: "from-blue-600 to-cyan-600",
            mockup: <DeepScanMockup />
        },
        {
            id: 3,
            title: t('showcase.slide3_title', 'Hartimi i Shkresave (Drafting Engine)'),
            desc: t('showcase.slide3_desc', 'Gjenerim automatik i Përgjigjeve në Padi, Kundërpadive dhe Masave të Sigurisë sipas mandatit të klientit.'),
            icon: <PenTool className="w-5 h-5" />,
            badge: "MANDATI I AVOKATIT",
            color: "from-purple-600 to-indigo-600",
            mockup: <DraftingMockup />
        },
        {
            id: 4,
            title: t('showcase.slide4_title', 'Ontologjia e Provave & Grafiku'),
            desc: t('showcase.slide4_desc', 'Grafik interaktiv i lidhjeve midis personave, kompanive, llogarive bankare dhe kontratave.'),
            icon: <Network className="w-5 h-5" />,
            badge: "GRAPH RELATIONSHIP ENGINE",
            color: "from-indigo-600 to-violet-600",
            mockup: <OntologyMockup />
        },
        {
            id: 5,
            title: t('showcase.slide5_title', 'Analisti Financiar Forenzik'),
            desc: t('showcase.slide5_desc', 'Auditim automatik i librave bankarë, Benford Check dhe analizë e parregullsive financiare.'),
            icon: <Calculator className="w-5 h-5" />,
            badge: "BENFORD'S LAW AUDIT",
            color: "from-amber-600 to-yellow-600",
            mockup: <FinanceMockup />
        }
    ];

    return (
        <div className="py-20 lg:py-28 bg-canvas relative overflow-hidden border-y border-main">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] bg-primary-start/5 rounded-full blur-[140px] pointer-events-none" />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                
                <div className="text-center mb-12 lg:mb-16 space-y-4">
                    <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary-start/10 border border-primary-start/20 text-primary-start text-xs font-black uppercase tracking-widest">
                        <Sparkles size={13} />
                        <span>Platforma Ekzekutive për Avokatë</span>
                    </div>
                    <h2 className="text-3xl sm:text-5xl font-black text-text-primary tracking-tight uppercase">
                        Salla e Komandimit të Lëndëve Ligjore
                    </h2>
                    <p className="text-base sm:text-lg text-text-secondary max-w-2xl mx-auto font-medium leading-relaxed">
                        Teknologjia më e avancuar e inteligjencës artificiale në Kosovë, e ndërtuar për të mbrojtur avokatin dhe për të siguruar fitoren gjyqësore.
                    </p>
                </div>

                {/* Mobile Tab Selector */}
                <div className="lg:hidden flex overflow-x-auto gap-2 mb-8 no-scrollbar pb-2 px-1">
                    {features.map((feature, index) => (
                        <button
                            key={feature.id}
                            onClick={() => setActiveTab(index)}
                            className={`flex-shrink-0 flex items-center gap-2 px-3.5 py-2 rounded-xl border transition-all text-xs font-bold uppercase tracking-wider ${
                                activeTab === index 
                                ? 'bg-primary-start text-white border-primary-start shadow-md' 
                                : 'bg-surface border-main text-text-muted hover:text-text-primary'
                            }`}
                        >
                            {feature.title}
                        </button>
                    ))}
                </div>

                {/* Stage Grid Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-stretch">
                    
                    {/* Desktop Control Buttons List */}
                    <div className="hidden lg:flex lg:col-span-5 flex-col justify-between space-y-3">
                        {features.map((feature, index) => {
                            const isActive = activeTab === index;
                            return (
                                <button
                                    key={feature.id}
                                    onClick={() => setActiveTab(index)}
                                    className={`w-full text-left p-4 lg:p-5 rounded-2xl transition-all duration-300 border flex items-center justify-between group cursor-pointer ${
                                        isActive 
                                        ? 'bg-surface border-primary-start/60 shadow-xl ring-1 ring-primary-start/30 scale-[1.02]' 
                                        : 'bg-surface/40 hover:bg-surface/80 border-main'
                                    }`}
                                >
                                    <div className="flex items-center gap-4 min-w-0">
                                        <div className={`p-3 rounded-xl bg-gradient-to-br ${feature.color} text-white shadow-md shrink-0 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-105'}`}>
                                            {feature.icon}
                                        </div>
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md ${
                                                    isActive ? 'bg-primary-start/15 text-primary-start border border-primary-start/30' : 'bg-canvas text-text-muted border border-main'
                                                }`}>
                                                    {feature.badge}
                                                </span>
                                            </div>
                                            <h3 className="text-sm font-black uppercase text-text-primary tracking-tight truncate">
                                                {feature.title}
                                            </h3>
                                            <p className="text-xs text-text-secondary leading-relaxed font-medium line-clamp-1 mt-0.5">
                                                {feature.desc}
                                            </p>
                                        </div>
                                    </div>

                                    <ChevronRight size={18} className={`shrink-0 transition-transform duration-300 ${isActive ? 'text-primary-start translate-x-1' : 'text-text-muted opacity-40 group-hover:opacity-100'}`} />
                                </button>
                            );
                        })}
                    </div>

                    {/* Interactive Stage Viewport */}
                    <div className="lg:col-span-7 h-[420px] sm:h-[480px] lg:h-[540px] w-full relative">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeTab}
                                initial={{ opacity: 0, scale: 0.97, y: 10 }}
                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.97, y: -10 }}
                                transition={{ duration: 0.3, ease: "easeOut" }}
                                className="absolute inset-0"
                            >
                                <div className="w-full h-full glass-panel border border-main rounded-3xl shadow-2xl overflow-hidden relative flex flex-col bg-slate-950 text-slate-100">
                                    <div className="h-10 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 shrink-0">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                                            <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                                            <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                                            <span className="text-[10px] font-mono text-slate-400 font-bold ml-2 uppercase tracking-widest">
                                                Juristi AI — {features[activeTab].badge}
                                            </span>
                                        </div>
                                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded uppercase font-bold">
                                            LIVE ENGINE
                                        </span>
                                    </div>
                                    
                                    <div className="p-5 lg:p-8 flex-1 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] relative overflow-hidden flex flex-col justify-center">
                                        {features[activeTab].mockup}
                                    </div>

                                    <div className="lg:hidden p-3.5 bg-slate-900 border-t border-slate-800">
                                        <p className="text-xs text-slate-300 text-center font-medium">
                                            {features[activeTab].desc}
                                        </p>
                                    </div>
                                </div>
                            </motion.div>
                        </AnimatePresence>
                    </div>

                </div>
            </div>
        </div>
    );
};

// --- MOCKUP COMPONENTS ---

const SwordsIcon = ({ className }: { className?: string }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.7 6.3a1 1 0 000 1.4l1.6 1.4a1 1 0 001.4 0l3.7-3.7a1 1 0 000-1.4l-1.6-1.4a1 1 0 00-1.4 0l-3.7 3.7z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.7 6.3L4.5 16.5M3 21l3-1.5M16.5 4.5L21 3" />
    </svg>
);

const WarRoomMockup = () => (
    <div className="space-y-4 h-full flex flex-col justify-center animate-in fade-in duration-500">
        <div className="flex items-center justify-between bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 text-xs font-bold text-rose-400 uppercase tracking-wider">
                <ShieldAlert size={16} /> Analiza Adversare e Mbrojtjes (I PADITUR)
            </div>
            <span className="text-[10px] font-mono bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded uppercase font-bold border border-rose-500/30">
                PALA KUNDËRSHTARE
            </span>
        </div>

        <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-rose-400 font-bold text-xs uppercase">
                <AlertTriangle size={14} /> Pika e Sulmit të Kundërshtarit
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-mono">
                &quot;Paditësi pretendoi se ekziston marrëveshje verbale, por nuk ka prokurë përfaqësimi (LPK Neni 98/99)...&quot;
            </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-blue-950/40 border border-blue-800/50 rounded-xl">
                <span className="text-[10px] font-bold text-blue-400 uppercase block mb-1">Mbrojtja Jonë & Prapësimi</span>
                <p className="text-xs text-slate-300 font-medium">Kalimi i afatit prekluziv 7-ditor (LPK Neni 99 par. 3) për Hudhje Padie.</p>
            </div>
            <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded-xl">
                <span className="text-[10px] font-bold text-emerald-400 uppercase block mb-1">Probabiliteti i Fitores</span>
                <p className="text-sm font-mono font-black text-emerald-300">85% Sukses</p>
            </div>
        </div>
    </div>
);

const LegalGroundingMockup = () => (
    <div className="h-full flex flex-col justify-between animate-in fade-in duration-500 space-y-3">
        <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 flex justify-between items-center">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 size={16} /> Verifikim me Bazën Ligjore të Kosovës
            </span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                100% SAKTI
            </span>
        </div>

        <div className="space-y-2 my-1">
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                    <span className="text-xs font-bold text-slate-100 block">Ligji Nr. 06/L-016 për Shoqëritë Tregtare</span>
                    <span className="text-[10px] text-slate-400">Neni 258 (Detyrimi i Besnikërisë) & Neni 259 (Ndalimi i Konkurrencës)</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 font-bold">
                    ✅ Verifikuar
                </span>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                    <span className="text-xs font-bold text-slate-100 block">Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve</span>
                    <span className="text-[10px] text-slate-400">Neni 180 (Shpërblimi i Dëmit) & Neni 210 (Përfitimi pa Bazë)</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 font-bold">
                    ✅ Verifikuar
                </span>
            </div>
        </div>

        <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded-xl flex items-center gap-3">
            <Scale size={20} className="text-emerald-400 shrink-0" />
            <p className="text-xs text-emerald-200 font-medium leading-normal">
                Kryeredaktori: Çdo citim përmban numrin zyrtar të ligjit dhe mund të verifikohet me klikim te burimi origjinal.
            </p>
        </div>
    </div>
);

const DeepScanMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500">
        <div className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2 mb-1">
            <ScanEye size={16} /> Leximi i Shkresave të Skanuara (HD OCR 10.0)
        </div>
        {[
            { name: "Contract - Rainer Gerke_countersigned.pdf", pages: "5 Faqe", status: "100% Skanuar (€51,500 EUR)" },
            { name: "Seanca_E_Pare_GetCom.pdf", pages: "12 Faqe", status: "100% Skanuar" },
            { name: "Raporti_Zyrtar_ATK_0.00.pdf", pages: "4 Faqe", status: "100% Skanuar" },
        ].map((item, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-900 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20">
                        <FileText size={16} />
                    </div>
                    <div>
                        <p className="text-xs font-bold text-slate-200">{item.name}</p>
                        <p className="text-[10px] text-slate-400 font-mono">{item.pages}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                        {item.status}
                    </span>
                    <CheckCircle size={16} className="text-emerald-400" />
                </div>
            </div>
        ))}
    </div>
);

const DraftingMockup = () => (
    <div className="h-full flex flex-col justify-between animate-in fade-in duration-500">
        <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 flex justify-between items-center">
            <span className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-2">
                <PenTool size={16} /> Gjeneruesi i Prapësimit & Kundërpadisë
            </span>
            <span className="text-[10px] font-mono text-slate-400">FORMATI .DOCX</span>
        </div>

        <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 text-xs text-slate-300 font-serif leading-relaxed my-2 space-y-2">
            <p className="font-bold uppercase text-center text-slate-100 border-b border-slate-800 pb-2">
                GJYKATA THEMELORE NË PRISHTINË — DEPARTAMENTI PËR ÇËSHTJE EKONOMIKE
            </p>
            <p className="italic text-slate-400">
                Lënda: Përgjigje në Padi dhe Kundërpadi sipas Nenit 160 të LPK-së dhe Nenit 258 të LSHT-së...
            </p>
        </div>

        <div className="p-3 bg-purple-950/40 border border-purple-800/50 rounded-xl flex items-center gap-3">
            <BrainCircuit size={20} className="text-purple-400 shrink-0" />
            <p className="text-xs text-purple-200 font-medium leading-normal">
                AI futi automatikisht emrat e palëve (INTEGRATION GmbH / Dr. Rainer Gerke) dhe kërkesën për shpërblim dëmi.
            </p>
        </div>
    </div>
);

const OntologyMockup = () => (
    <div className="h-full flex flex-col justify-between relative overflow-hidden animate-in fade-in duration-500">
        <div className="flex justify-between items-center bg-slate-900/90 p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                <Network size={16} /> Ontologjia e Provave
            </div>
            <span className="px-2.5 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono font-bold">
                17 ENTITETE • 1 KUNDËRTHËNJE
            </span>
        </div>

        <div className="flex-1 relative flex items-center justify-center my-3">
            <svg className="w-full h-full" viewBox="-220 -130 440 260">
                <path d="M -120 -40 Q 0 20 120 -40" fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="5,5" className="animate-pulse" />
                <path d="M -120 -40 Q -60 50 0 50" fill="none" stroke="#3b82f6" strokeWidth="2" />
                <path d="M 0 50 Q 60 50 120 -40" fill="none" stroke="#8b5cf6" strokeWidth="2" />
                
                <rect x="-45" y="-12" width="90" height="18" rx="5" fill="#450a0a" stroke="#ef4444" strokeWidth="1" />
                <text x="0" y="0" textAnchor="middle" fill="#fca5a5" fontSize="8" fontWeight="black">KUNDËRTHËNJE</text>

                <rect x="-30" y="42" width="60" height="16" rx="4" fill="#0f172a" stroke="#3b82f6" strokeWidth="1" />
                <text x="0" y="53" textAnchor="middle" fill="#93c5fd" fontSize="8" fontWeight="bold">€51,500</text>

                <g transform="translate(-120, -40)" className="cursor-pointer">
                    <circle r="22" fill="rgba(59, 130, 246, 0.25)" stroke="#3b82f6" strokeWidth="2.5" />
                    <text y="36" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">Shaban Bala</text>
                </g>

                <g transform="translate(0, 50)" className="cursor-pointer">
                    <circle r="22" fill="rgba(139, 92, 246, 0.25)" stroke="#8b5cf6" strokeWidth="2.5" />
                    <text y="36" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">Getting Competent Sh.p.k.</text>
                </g>

                <g transform="translate(120, -40)" className="cursor-pointer">
                    <circle r="22" fill="rgba(16, 185, 129, 0.25)" stroke="#10b981" strokeWidth="2.5" />
                    <text y="36" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">TEB Bank QAFA</text>
                </g>
            </svg>
        </div>

        <div className="p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs text-slate-300 flex justify-between items-center">
            <span className="font-semibold text-slate-400">Gjurmim i automatizuar i rrjedhës financiare</span>
            <span className="text-indigo-400 font-bold flex items-center gap-1">Eksporto Raportin <ArrowRight size={12} /></span>
        </div>
    </div>
);

const FinanceMockup = () => (
    <div className="h-full flex flex-col justify-between animate-in fade-in duration-500">
        <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 flex justify-between items-center">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-2">
                <Calculator size={16} /> Auditimi Financiar & Benford Check
            </span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                PASQYRAT E RREGULLTA
            </span>
        </div>

        <div className="grid grid-cols-2 gap-3 my-2">
            <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-xl">
                <span className="text-[10px] font-bold text-emerald-400 uppercase block">Qarkullimi Total</span>
                <span className="text-base font-mono font-black text-slate-100">€ 142,500.00</span>
            </div>
            <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-xl">
                <span className="text-[10px] font-bold text-amber-400 uppercase block">Depozitë e Mbrojtur</span>
                <span className="text-base font-mono font-black text-amber-300">€ 52,000.00</span>
            </div>
        </div>

        <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl space-y-1">
            <div className="flex justify-between text-xs font-bold text-slate-200">
                <span>Rezultati i Ligjit të Benfordit:</span>
                <span className="text-emerald-400 font-mono">98.4% Normal</span>
            </div>
            <p className="text-[10px] text-slate-400">Nuk u gjetën manipulime të shifrave në ditarin e arkës.</p>
        </div>
    </div>
);

export default ProductShowcase;