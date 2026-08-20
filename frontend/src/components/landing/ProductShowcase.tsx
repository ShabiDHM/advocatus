// FILE: src/components/landing/ProductShowcase.tsx
// PHOENIX PROTOCOL - PRODUCT SHOWCASE V13.0 (HONEST & PRESTIGIOUS LEGAL SHOWCASE)

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    ShieldAlert, FileText, BrainCircuit, 
    PenTool, Sparkles, AlertTriangle, ChevronRight,
    Scale, CheckCircle2, Swords, Zap
} from 'lucide-react';

const ProductShowcase: React.FC = () => {
    const [activeTab, setActiveTab] = useState(0);

    const features = [
        {
            id: 0,
            title: "Dhoma e Luftës (Simulimi Taktik)",
            desc: "Simulim i strategjisë së palës kundërshtare, parashikim i sulmeve dhe përgatitje e kundërsulmit procedural sipas rolit (Paditës / I Paditur).",
            icon: <Swords className="w-5 h-5" />,
            badge: "ANALIZË ADVERSARE",
            color: "from-rose-600 to-red-600",
            mockup: <WarRoomMockup />
        },
        {
            id: 1,
            title: "4 Shtyllat e Fillimit (Sokrati AI)",
            desc: "Strategjia e çështjes, Baza Ligjore sipas LPK/KPRK, Pyetësori Taktik i Seancës dhe Raporti Ekzekutiv me vlerësimin e rreziqeve.",
            icon: <Sparkles className="w-5 h-5" />,
            badge: "4 SHTYLLAT PROCEDURALE",
            color: "from-blue-600 to-indigo-600",
            mockup: <FourPillarsMockup />
        },
        {
            id: 2,
            title: "Citime të Klikueshme & Verifikim i Shpejtë",
            desc: "Çdo fakt dhe referencë lidhet me link direkt te faqja origjinale në PDF. Baza ligjore mbështetet në LPK, KPRK, KPPRK, LFK dhe LMD të Kosovës.",
            icon: <CheckCircle2 className="w-5 h-5" />,
            badge: "REFERENCA TË VERIFIKUESHME",
            color: "from-emerald-600 to-teal-600",
            mockup: <LegalGroundingMockup />
        },
        {
            id: 3,
            title: "Përpunim i Shpejtë i Fashikullit (~3.5s)",
            desc: "Teknologjia e vektorizimit në bllok përpunon shkresat dhe provat në sekonda pa bllokime dhe me saktësi në gjuhën shqipe.",
            icon: <Zap className="w-5 h-5" />,
            badge: "SHPEJTËSI ASINKRONE",
            color: "from-amber-600 to-yellow-600",
            mockup: <SpeedScanMockup />
        },
        {
            id: 4,
            title: "Ndihmës për Hartimin e Shkresave",
            desc: "Ndihmon në strukturimin e Padive, Përgjigjeve në Padi, Kundërpadive, Masave të Sigurisë dhe Shkresave Penale në format Word (.docx).",
            icon: <PenTool className="w-5 h-5" />,
            badge: "HARTIM I STRUKTURUAR",
            color: "from-cyan-600 to-blue-600",
            mockup: <DraftingMockup />
        }
    ];

    useEffect(() => {
        const timer = setInterval(() => {
            setActiveTab((prev) => (prev + 1) % features.length);
        }, 8000);
        return () => clearInterval(timer);
    }, [features.length]);

    return (
        <div className="py-20 lg:py-28 bg-canvas relative overflow-hidden border-y border-main font-sans">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] bg-primary-start/5 rounded-full blur-[140px] pointer-events-none" />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                
                <div className="text-center mb-12 lg:mb-16 space-y-4">
                    <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-primary-start/10 border border-primary-start/20 text-primary-start text-xs font-bold uppercase tracking-widest">
                        <Sparkles size={13} />
                        <span>Mjedisi i Punës për Avokatë dhe Juristë</span>
                    </div>
                    <h2 className="text-3xl sm:text-5xl font-black text-text-primary tracking-tight uppercase">
                        Salla e Menaxhimit të Çështjeve Ligjore
                    </h2>
                    <p className="text-base sm:text-lg text-text-secondary max-w-2xl mx-auto font-normal leading-relaxed">
                        Teknologji e avancuar e ndërtuar posaçërisht për praktikat gjyqësore në Kosovë, për të lehtësuar analizën e provave dhe përgatitjen e seancave.
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
                    <div className="hidden lg:flex lg:col-span-5 flex-col justify-between space-y-2.5">
                        {features.map((feature, index) => {
                            const isActive = activeTab === index;
                            return (
                                <button
                                    key={feature.id}
                                    onClick={() => setActiveTab(index)}
                                    className={`w-full text-left p-4 rounded-2xl transition-all duration-300 border flex items-center justify-between group cursor-pointer ${
                                        isActive 
                                        ? 'bg-surface border-primary-start/60 shadow-xl ring-1 ring-primary-start/30 scale-[1.02]' 
                                        : 'bg-surface/40 hover:bg-surface/80 border-main'
                                    }`}
                                >
                                    <div className="flex items-center gap-3.5 min-w-0">
                                        <div className={`p-2.5 rounded-xl bg-gradient-to-br ${feature.color} text-white shadow-md shrink-0 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-105'}`}>
                                            {feature.icon}
                                        </div>
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5">
                                                <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                                                    isActive ? 'bg-primary-start/15 text-primary-start border border-primary-start/30' : 'bg-canvas text-text-muted border border-main'
                                                }`}>
                                                    {feature.badge}
                                                </span>
                                            </div>
                                            <h3 className="text-sm font-bold uppercase text-text-primary tracking-tight truncate">
                                                {feature.title}
                                            </h3>
                                            <p className="text-xs text-text-secondary leading-relaxed font-normal line-clamp-1 mt-0.5">
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
                    <div className="lg:col-span-7 h-[440px] sm:h-[480px] lg:h-[540px] w-full relative">
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
                                                Juristi Virtual — {features[activeTab].badge}
                                            </span>
                                        </div>
                                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 font-bold px-2 py-0.5 rounded uppercase">
                                            PAMJE LIVE
                                        </span>
                                    </div>
                                    
                                    <div className="p-5 lg:p-7 flex-1 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] relative overflow-hidden flex flex-col justify-center">
                                        {features[activeTab].mockup}
                                    </div>

                                    <div className="lg:hidden p-3 bg-slate-900 border-t border-slate-800">
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

const WarRoomMockup = () => (
    <div className="space-y-3.5 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="flex items-center justify-between bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 text-xs font-bold text-rose-400 uppercase tracking-wider">
                <ShieldAlert size={16} /> Analiza Procedurale e Mbrojtjes (I PADITUR)
            </div>
            <span className="text-[10px] font-mono bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded uppercase font-bold border border-rose-500/30">
                PALA KUNDËRSHTARE
            </span>
        </div>

        <div className="p-3.5 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1.5">
            <div className="flex items-center gap-2 text-rose-400 font-bold text-xs uppercase">
                <AlertTriangle size={14} /> Pretendimi i Kundërshtarit
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-mono">
                &quot;Paditësi kërkoi kompensimin e dëmit material pa faturë tatimore dhe kërkoi masë sigurie...&quot;
            </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-blue-950/40 border border-blue-800/50 rounded-xl">
                <span className="text-[10px] font-bold text-blue-400 uppercase block mb-1">Mbrojtja & Prapësimi</span>
                <p className="text-xs text-slate-300 font-medium">Parashkrimi i kërkesës sipas LMD Neni 376 dhe mungesa e legjitimitetit aktiv.</p>
            </div>
            <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded-xl">
                <span className="text-[10px] font-bold text-emerald-400 uppercase block mb-1">Vlerësimi Procedural</span>
                <p className="text-sm font-mono font-bold text-emerald-300">Prapësim i Bazuar</p>
            </div>
        </div>
    </div>
);

const FourPillarsMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Sparkles size={15} /> 4 Kartelat e Fillimit të Lëndës</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">Roli: ⚔️ PADITËS</span>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">Shtyllë 1</span>
                <p className="text-xs font-bold text-slate-100">Strategjia e Padisë</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Identifikon 3 pikat kryesore me lidhje te provat materiale.</p>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">Shtyllë 2</span>
                <p className="text-xs font-bold text-slate-100">Baza Ligjore (LPK/LMD)</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Nenet statutore dhe llogaritja e kamatës ligjore.</p>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">Shtyllë 3</span>
                <p className="text-xs font-bold text-slate-100">Pyetësori i Seancës</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Pyetje të strukturuara për dëgjimin e dëshmitarëve.</p>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">Shtyllë 4</span>
                <p className="text-xs font-bold text-slate-100">Raporti për Klientin</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Përmbledhje ekzekutive mbi hapat e ardhshëm proceduralë.</p>
            </div>
        </div>
    </div>
);

const LegalGroundingMockup = () => (
    <div className="h-full flex flex-col justify-between animate-in fade-in duration-500 space-y-2.5 font-sans">
        <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800 flex justify-between items-center">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 size={16} /> Citime me Referenca të Drejtpërdrejta
            </span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                E VERIFIKUESHME
            </span>
        </div>

        <div className="space-y-2 my-1">
            <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                    <span className="text-xs font-bold text-slate-100 block">Kodi i Procedurës Penale (KPPRK)</span>
                    <span className="text-[10px] text-slate-400">Neni 188 (Masa Mbrojtëse për Dëshmitarin e Mitur)</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 font-bold">
                    Neni përkatës
                </span>
            </div>

            <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                    <span className="text-xs font-bold text-slate-100 block">Shkresa në Dosje</span>
                    <span className="text-[10px] text-blue-400 font-mono underline">[Certifikata_Laboratorike.pdf](/documents/6a80)</span>
                </div>
                <span className="text-[10px] font-mono text-blue-400 bg-blue-500/10 px-2 py-1 rounded border border-blue-500/20 font-bold">
                    Hap Shkresën
                </span>
            </div>
        </div>

        <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/50 rounded-xl flex items-center gap-3">
            <Scale size={18} className="text-emerald-400 shrink-0" />
            <p className="text-xs text-emerald-200 font-medium leading-tight">
                Avokati mban kontrollin: çdo fakt verifikohet me një klikim mbi shkresën origjinale të lëndës.
            </p>
        </div>
    </div>
);

const SpeedScanMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Zap size={16} /> Vektorizim në Bllok (~3.5 Sekonda)</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">32/32 DOKUMENTE</span>
        </div>

        {[
            { name: "Procesverbali_Seanca_1.pdf", status: "✅ Përpunuar", size: "14 Faqe" },
            { name: "Raporti_Mjekesor.pdf", status: "✅ Përpunuar", size: "8 Faqe" },
            { name: "Certifikata_Laboratorike.pdf", status: "✅ Përpunuar", size: "4 Faqe" },
        ].map((item, i) => (
            <div key={i} className="flex items-center justify-between p-2.5 bg-slate-900 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-2.5">
                    <div className="p-1.5 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20">
                        <FileText size={15} />
                    </div>
                    <div>
                        <p className="text-xs font-bold text-slate-200">{item.name}</p>
                        <p className="text-[10px] text-slate-400 font-mono">{item.size}</p>
                    </div>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                    {item.status}
                </span>
            </div>
        ))}
    </div>
);

const DraftingMockup = () => (
    <div className="h-full flex flex-col justify-between animate-in fade-in duration-500 font-sans">
        <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800 flex justify-between items-center">
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                <PenTool size={16} /> Moduli i Hartimit të Shkresave
            </span>
            <span className="text-[10px] font-mono text-slate-400">FORMATI .DOCX / PDF</span>
        </div>

        <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800 text-xs text-slate-300 font-serif leading-relaxed my-1.5 space-y-1.5">
            <p className="font-bold uppercase text-center text-slate-100 border-b border-slate-800 pb-1.5 text-[11px]">
                GJYKATA THEMELORE NË PRISHTINË — DEPARTAMENTI PËR ÇËSHTJE EKONOMIKE
            </p>
            <p className="italic text-slate-400 text-[11px]">
                Lënda: Përgjigje në Padi me Prapësim Procedural dhe Kërkesë për Shpërblim Dëmi...
            </p>
        </div>

        <div className="p-2.5 bg-cyan-950/40 border border-cyan-800/50 rounded-xl flex items-center gap-3">
            <BrainCircuit size={18} className="text-cyan-400 shrink-0" />
            <p className="text-xs text-cyan-200 font-medium leading-tight">
                Sistemi ndihmon në strukturimin e fakteve dhe neneve statutore përkatëse sipas ligjeve të Kosovës.
            </p>
        </div>
    </div>
);

export default ProductShowcase;