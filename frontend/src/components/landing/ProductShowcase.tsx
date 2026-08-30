// FILE: src/components/landing/ProductShowcase.tsx
// PHOENIX PROTOCOL - PRODUCT SHOWCASE V17.0 (ANALIZO RASTIN SPOTLIGHT)

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileText, ChevronRight,
    Scale, CheckCircle2, Zap, BookOpen, AlertTriangle, Mic, Volume2,
    FileSearch
} from 'lucide-react';

const ProductShowcase: React.FC = () => {
    const [activeTab, setActiveTab] = useState(0);

    const features = [
        {
            id: 0,
            title: "⚖️ Analizo Rastin — Raporti i Plotë Forenzik",
            desc: "Një klik — Sokrati lexon të gjitha shkresat e fashikullit, ndjek Protokollin e Gjyqtarit Suprem dhe gjeneron raportin e plotë me 10 seksione: shkeljet me nene, provat, aktorët, dëmet, plani i veprimit.",
            icon: <FileSearch className="w-5 h-5 text-amber-400" />,
            badge: "RAPORTI ME 1 KLIK",
            color: "from-amber-600 via-orange-600 to-primary-start",
            mockup: <ComprehensiveAnalysisMockup />
        },
        {
            id: 1,
            title: "Forenzika e Dokumentit ⚖️",
            desc: "Klikoni mbi çdo dokument për auditim forenzik: lidh nenet me Gazetën Zyrtare, zbulon prapadatimet dhe nxjerr opinionin e Gjykatës Supreme nga 700+ faqe jurisprudencë.",
            icon: <Scale className="w-5 h-5" />,
            badge: "AUDITIM ME 1-KLIKIM",
            color: "from-blue-600 to-indigo-600",
            mockup: <ForensicAuditMockup />
        },
        {
            id: 2,
            title: "Transkriptimi Forenzik Audio & Video",
            desc: "Ngarkoni biseda telefonike, regjistrime audio nga xhepi apo video. Whisper Large-v3 nxjerr transkriptin 100% fjalë për fjalë me sekonda, në gjuhë të përzier shqip-anglisht.",
            icon: <Mic className="w-5 h-5" />,
            badge: "FORENZIKË MULTIMEDIALE",
            color: "from-rose-600 to-purple-600",
            mockup: <MediaTranscriptMockup />
        },
        {
            id: 3,
            title: "Fashikulli i Provave & Leximi OCR",
            desc: "Digjitalizim i shpejtë i shkresave dhe vendimeve të skanuara me PyMuPDF, me njohje të plotë të karaktereve shqipe.",
            icon: <Zap className="w-5 h-5" />,
            badge: "DIGJITALIZIM I SHPEJTË",
            color: "from-amber-600 to-yellow-600",
            mockup: <SpeedScanMockup />
        },
        {
            id: 4,
            title: "Biblioteka Ligjore e Kosovës (5,024 Nene)",
            desc: "Qasje e drejtpërdrejtë në 19 Ligjet dhe Kodet zyrtare me të gjitha nenet e indeksuara.",
            icon: <BookOpen className="w-5 h-5" />,
            badge: "5,024 NENE TË VERIFIKUARA",
            color: "from-emerald-600 to-teal-600",
            mockup: <LegalGroundingMockup />
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
                        <FileSearch size={13} className="text-amber-500" />
                        <span>Analizo Rastin — Raporti i Plotë Forenzik me 1 Klik</span>
                    </div>
                    <h2 className="text-3xl sm:text-5xl font-black text-text-primary tracking-tight uppercase">
                        Mjetet e Punës së Përditshme Ligjore
                    </h2>
                    <p className="text-base sm:text-lg text-text-secondary max-w-2xl mx-auto font-normal leading-relaxed">
                        Teknologji e pastër e ndërtuar posaçërisht për praktikat gjyqësore në Kosovë.
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
                                                Ndihmë Juridike — {features[activeTab].badge}
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

const ComprehensiveAnalysisMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><FileSearch size={16} /> Analizo Rastin — Raporti i Plotë</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">10 SEKSIONE</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
            {[
                "📋 Përmbledhja Ekzekutive",
                "📅 Kronologjia e Rastit",
                "⚖️ Shkeljet me Nene",
                "🔬 Matrica e Provave",
                "👥 Aktorët dhe Rolet",
                "🏛️ Baza Statutore",
                "🔨 Opinioni Suprem",
                "💶 Dëmet dhe Kamata",
                "🎯 Plani i Veprimit",
                "💡 Rekomandimet"
            ].map((item, i) => (
                <div key={i} className="p-2 bg-slate-900 border border-slate-800 rounded-lg">
                    <p className="text-[10px] text-slate-300 font-medium">{item}</p>
                </div>
            ))}
        </div>

        <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/50 rounded-xl">
            <p className="text-[10px] text-emerald-200 font-bold text-center">
                ⚡ Një Klik — Raporti i Plotë Forenzik
            </p>
        </div>
    </div>
);

const ForensicAuditMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Scale size={16} /> Forenzika e Dokumentit</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">100% E VERIFIKUAR</span>
        </div>

        <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-rose-400">
                <AlertTriangle size={13} className="shrink-0" />
                <span>⚠️ Zbulimi i Lapsusit Statutar:</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
                Në shkresë citohet <strong>Neni 372</strong> i KPRK-së. 
                <span className="text-emerald-400 font-bold ml-1">➔ Dispozita e saktë është Neni 387 i KPRK-së.</span>
            </p>
        </div>

        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1.5">
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase text-amber-400 flex items-center gap-1">
                    Gjykata Supreme e Kosovës
                </span>
                <span className="text-[9px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">Rev.Nr.541/2024</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed font-serif">
                &quot;Trajtimi psikiatrik kërkon baza të forta shkencore laboratorike.&quot;
            </p>
        </div>
    </div>
);

const SpeedScanMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Zap size={16} /> Vektorizim në Bllok</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">147 FAQE LIVE</span>
        </div>

        {[
            { name: "Vendimi_Gjyqesor_C_nr_385.pdf", status: "✅ Përpunuar", size: "14 Faqe" },
            { name: "Raporti_Psikiatrise_QKUK.pdf", status: "✅ Përpunuar", size: "8 Faqe" },
            { name: "Certifikata_Toksikologjike_Koslabor.pdf", status: "✅ 100% Negativ", size: "2 Faqe" },
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

const MediaTranscriptMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-rose-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Volume2 size={16} /> Forenzika e Provës Audio</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">VERBATIM 100%</span>
        </div>

        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
            <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-200 truncate flex items-center gap-1.5">
                    <Mic size={13} className="text-rose-400" /> Biseda_Femija_Andi_Bala.m4a
                </span>
                <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">04:18 min</span>
            </div>
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 font-mono leading-relaxed space-y-1.5">
                <p><span className="text-primary-start font-bold">[00:14 - 00:22]</span> Fëmija: &quot;Te dua edhe te babi...&quot;</p>
                <p><span className="text-primary-start font-bold">[01:15 - 01:25]</span> Prindi: &quot;Do ta zbatojmë marrëveshjen...&quot;</p>
            </div>
        </div>
    </div>
);

const LegalGroundingMockup = () => (
    <div className="h-full flex flex-col justify-between animate-in fade-in duration-500 space-y-2.5 font-sans">
        <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800 flex justify-between items-center">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 size={16} /> 5,024 Nene të Gazetës Zyrtare
            </span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-bold">
                E VERIFIKUESHME
            </span>
        </div>

        <div className="space-y-2 my-1">
            <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                    <span className="text-xs font-bold text-slate-100 block">Kodi Penal i Kosovës (Nr. 06/L-074)</span>
                    <span className="text-[10px] text-slate-400">Neni 390 (Lajmërimi i rremë) & Neni 387 (Mjekët)</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 font-bold">
                    Neni 390
                </span>
            </div>

            <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                    <span className="text-xs font-bold text-slate-100 block">Ligji për Familjen (Nr. 2004/32)</span>
                    <span className="text-[10px] text-blue-400 font-mono">Neni 145 (Interesi superior i fëmijës)</span>
                </div>
                <span className="text-[10px] font-mono text-blue-400 bg-blue-500/10 px-2 py-1 rounded border border-blue-500/20 font-bold">
                    Neni 145
                </span>
            </div>
        </div>
    </div>
);

export default ProductShowcase;