// FILE: src/components/landing/ProductShowcase.tsx
// PHOENIX PROTOCOL - PRODUCT SHOWCASE V15.1 (0 WARNINGS & STRICT CLEAN IMPORTS)

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileText, Sparkles, ChevronRight,
    Scale, CheckCircle2, Zap, Film, BookOpen, AlertTriangle, Gavel 
} from 'lucide-react';

const ProductShowcase: React.FC = () => {
    const [activeTab, setActiveTab] = useState(0);

    const features = [
        {
            id: 0,
            title: "Forenzika Ligjore ⚖️ & Gjykata Supreme",
            desc: "Klikoni mbi çdo dokument për auditim forenzik: lidh automatikisht nenet, zbulon lapsuset e shkresave dhe nxjerr opinionin e Gjykatës Supreme nga 700+ faqe jurisprudencë.",
            icon: <Scale className="w-5 h-5 text-amber-400" />,
            badge: "AUDITIM ME 1-KLIKIM",
            color: "from-amber-600 via-orange-600 to-primary-start",
            mockup: <ForensicAuditMockup />
        },
        {
            id: 1,
            title: "Sokrati AI — 4 Shtyllat Procedurale",
            desc: "Përgatitje e menjëhershme e lëndës sipas rolit (Paditës, I Paditur apo Neutral): Strategjia, Baza Ligjore, Pyetësori i Seancës dhe Raporti Ekzekutiv.",
            icon: <Sparkles className="w-5 h-5" />,
            badge: "ASISTENTI I LËNDËS",
            color: "from-blue-600 to-indigo-600",
            mockup: <FourPillarsMockup />
        },
        {
            id: 2,
            title: "Fashikulli i Provave & Leximi OCR (~3.5s)",
            desc: "Digjitalizim i shpejtë i shkresave dhe vendimeve të skanuara me njohje të plotë të karaktereve shqipe dhe referenca faqe-për-faqe.",
            icon: <Zap className="w-5 h-5" />,
            badge: "DIGJITALIZIM I SHPEJTË",
            color: "from-amber-600 to-yellow-600",
            mockup: <SpeedScanMockup />
        },
        {
            id: 3,
            title: "Transkriptimi i Skedarëve Audio & Video",
            desc: "Ngarkoni regjistrime audio apo video të bisedave e dëshmive. Sistemi nxjerr menjëherë transkriptin e plotë me minuta për përdorim në seancë.",
            icon: <Film className="w-5 h-5" />,
            badge: "MULTIMEDIA",
            color: "from-purple-600 to-pink-600",
            mockup: <MediaTranscriptMockup />
        },
        {
            id: 4,
            title: "Biblioteka Ligjore e Kosovës me Kërkim Semantik",
            desc: "Qasje e drejtpërdrejtë në ligjet zyrtare (LPK, KPRK, KPPRK, LFK, LMD) me nene të verifikuara dhe lexim të plotë të PDF-së origjinale.",
            icon: <BookOpen className="w-5 h-5" />,
            badge: "STATUTET E KOSOVËS",
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
                        <Scale size={13} className="text-amber-500" />
                        <span>Forenzikë Ligjore & Jurisprudencë Supreme për Avokatë</span>
                    </div>
                    <h2 className="text-3xl sm:text-5xl font-black text-text-primary tracking-tight uppercase">
                        Mjetet e Punës së Përditshme Ligjore
                    </h2>
                    <p className="text-base sm:text-lg text-text-secondary max-w-2xl mx-auto font-normal leading-relaxed">
                        Teknologji e pastër e ndërtuar posaçërisht për praktikat gjyqësore në Kosovë, për të lehtësuar analizën e provave dhe përgatitjen e seancave.
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

const ForensicAuditMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Scale size={16} /> Forenzika Ligjore (1-Kliko ⚖️)</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">100% E VERIFIKUAR</span>
        </div>

        <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-rose-400">
                <AlertTriangle size={13} className="shrink-0" />
                <span>⚠️ Zbulimi i Lapsusit Statutar:</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
                Në shkresë citohet <strong>Neni 250</strong> i KPRK-së (që në ligj është <em>Mosveprimi gjatë epidemisë</em>). 
                <span className="text-emerald-400 font-bold ml-1">➔ Sugjerohet Neni 247 i KPRK-së (Keqtrajtimi i fëmijës).</span>
            </p>
        </div>

        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1.5">
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase text-amber-400 flex items-center gap-1">
                    <Gavel size={13} /> Gjykata Supreme e Kosovës (700+ Faqe)
                </span>
                <span className="text-[9px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">PML.Nr.85/2025</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed font-serif">
                &quot;Ndalohet zbatimi i ligjit penal në dëm të palës duke përdorur dënime të shlyera automatikisht sipas <strong>Nenit 93 të KPRK-së</strong>.&quot;
            </p>
        </div>
    </div>
);

const FourPillarsMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Sparkles size={15} /> 4 Kartelat e Fillimit të Lëndës</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">Roli: 🛡️ I PADITUR</span>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">Shtyllë 1</span>
                <p className="text-xs font-bold text-slate-100">Strategjia e Mbrojtjes</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Identifikon 3 prapësimet kryesore dhe faktet shfajësuese.</p>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">Shtyllë 2</span>
                <p className="text-xs font-bold text-slate-100">Baza Ligjore (LPK/KPRK)</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Nenet statutore dhe parashkrimi i afateve.</p>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">Shtyllë 3</span>
                <p className="text-xs font-bold text-slate-100">Pyetësori i Seancës</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Kundër-pyetje të strukturuara për dëshmitarët e paditësit.</p>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
                <span className="text-[9px] font-bold uppercase text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">Shtyllë 4</span>
                <p className="text-xs font-bold text-slate-100">Raporti për Klientin</p>
                <p className="text-[10px] text-slate-400 line-clamp-2">Përmbledhje ekzekutive mbi hapat e mëtejshëm proceduralë.</p>
            </div>
        </div>
    </div>
);

const SpeedScanMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Zap size={16} /> Vektorizim në Bllok (~3.5 Sekonda)</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">24/24 DOKUMENTE</span>
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

const MediaTranscriptMockup = () => (
    <div className="space-y-3 h-full flex flex-col justify-center animate-in fade-in duration-500 font-sans">
        <div className="text-xs font-bold text-pink-400 uppercase tracking-wider flex items-center justify-between mb-1">
            <span className="flex items-center gap-2"><Film size={16} /> Transkriptimi Audio & Video</span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-bold">READY</span>
        </div>

        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
            <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-200 truncate">Regjistrimi_Deklarates.mp3</span>
                <span className="text-[10px] font-mono text-slate-400">03:45 min</span>
            </div>
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 font-mono leading-relaxed space-y-1">
                <p><span className="text-primary-start font-bold">[00:14]</span> &quot;Biseda u zhvillua pa asnjë ofendim apo kërcënim...&quot;</p>
                <p><span className="text-primary-start font-bold">[01:22]</span> &quot;Palët ranë dakord për zbatimin e marrëveshjes me shkrim...&quot;</p>
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
                    <span className="text-xs font-bold text-slate-100 block">Ligji për Procedurën Kontestimore (LPK)</span>
                    <span className="text-[10px] text-slate-400">Nenet 100–115 (Ftesat dhe Dorëzimi i Rregullt)</span>
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

export default ProductShowcase;