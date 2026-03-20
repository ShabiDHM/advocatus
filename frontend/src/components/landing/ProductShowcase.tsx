// FILE: src/components/landing/ProductShowcase.tsx
// PHOENIX PROTOCOL - PRODUCT SHOWCASE V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary.
// 2. Updated all mockups to use semantic color variables.
// 3. Preserved all animations and functionality.

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { 
    ShieldAlert, FileText, ScanEye, BrainCircuit, 
    CheckCircle, PenTool, FolderOpen, 
    Sparkles, Gavel, Calculator, TrendingUp
} from 'lucide-react';

const ProductShowcase = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState(0);

    // Auto-rotate slides (5 slides)
    useEffect(() => {
        const timer = setInterval(() => {
            setActiveTab((prev) => (prev + 1) % 5);
        }, 8000);
        return () => clearInterval(timer);
    }, []);

    const features = [
        {
            id: 0,
            title: t('showcase.slide1_title', 'Dhoma e Luftës'),
            desc: t('showcase.slide1_desc', 'Gjeni gënjeshtrat automatikisht.'),
            icon: <Gavel className="w-5 h-5 lg:w-6 lg:h-6" />,
            color: "from-red-500 to-orange-500",
            mockup: <WarRoomMockup />
        },
        {
            id: 1,
            title: t('showcase.slide2_title', 'Deep Scan OCR'),
            desc: t('showcase.slide2_desc', 'Skanoni 50+ dokumente në sekonda.'),
            icon: <ScanEye className="w-5 h-5 lg:w-6 lg:h-6" />,
            color: "from-blue-500 to-cyan-500",
            mockup: <DeepScanMockup />
        },
        {
            id: 2,
            title: t('showcase.slide3_title', 'Hartim i Padukshëm'),
            desc: t('showcase.slide3_desc', 'Ju shkruani strategjinë, ne shkruajmë nenet.'),
            icon: <PenTool className="w-5 h-5 lg:w-6 lg:h-6" />,
            color: "from-emerald-500 to-green-500",
            mockup: <DraftingMockup />
        },
        {
            id: 3,
            title: t('showcase.slide4_title', 'Arkiva e Gjallë'),
            desc: t('showcase.slide4_desc', 'Çdo dokument, i indeksuar dhe i sigurt.'),
            icon: <FolderOpen className="w-5 h-5 lg:w-6 lg:h-6" />,
            color: "from-purple-500 to-indigo-500",
            mockup: <ArchiveMockup />
        },
        {
            id: 4,
            title: t('showcase.slide5_title', 'Kontabilisti i Zyrës'),
            desc: t('showcase.slide5_desc', 'Menaxhoni financat dhe tatimet automatikisht.'),
            icon: <Calculator className="w-5 h-5 lg:w-6 lg:h-6" />,
            color: "from-amber-500 to-yellow-500",
            mockup: <FinanceMockup />
        }
    ];

    return (
        <div className="py-16 lg:py-24 bg-canvas/50 relative overflow-hidden backdrop-blur-sm border-y border-main">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                <div className="text-center mb-10 lg:mb-16">
                    <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
                        {t('showcase.title', 'Jo Thjesht Softuer. Partneri Juaj.')}
                    </h2>
                    <p className="text-lg lg:text-xl text-text-secondary max-w-2xl mx-auto">
                        {t('showcase.subtitle', 'Inteligjencë Artificiale e ndërtuar për sistemin e Kosovës.')}
                    </p>
                </div>

                {/* --- MOBILE NAVIGATION --- */}
                <div className="lg:hidden flex overflow-x-auto gap-3 mb-8 no-scrollbar pb-2 px-2">
                    {features.map((feature, index) => (
                        <button
                            key={feature.id}
                            onClick={() => setActiveTab(index)}
                            className={`flex-shrink-0 flex items-center gap-2 px-4 py-2 rounded-full border transition-all whitespace-nowrap ${
                                activeTab === index 
                                ? 'btn-primary border-transparent shadow-lg' 
                                : 'bg-surface/30 border-main text-text-secondary'
                            }`}
                        >
                            <div className={`p-1 rounded-full ${activeTab === index ? '' : `bg-gradient-to-br ${feature.color}`}`}>
                                {React.cloneElement(feature.icon, {className: `w-4 h-4 ${activeTab === index ? 'text-text-primary' : 'text-text-primary'}`})}
                            </div>
                            <span className="text-sm font-bold">{feature.title}</span>
                        </button>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
                    
                    {/* --- DESKTOP CONTROLS --- */}
                    <div className="hidden lg:block space-y-4">
                        {features.map((feature, index) => (
                            <button
                                key={feature.id}
                                onClick={() => setActiveTab(index)}
                                className={`w-full text-left p-5 rounded-2xl transition-all duration-300 border group glass-panel ${
                                    activeTab === index 
                                    ? 'bg-surface/30 border-primary-start/50 shadow-2xl scale-[1.02]' 
                                    : 'hover:bg-surface/20 border-main'
                                }`}
                            >
                                <div className="flex items-center gap-4">
                                    <div className={`p-3 rounded-xl bg-gradient-to-br ${feature.color} text-text-primary shadow-lg transition-transform duration-300 ${activeTab === index ? 'scale-110' : 'group-hover:scale-105'}`}>
                                        {feature.icon}
                                    </div>
                                    <div>
                                        <h3 className={`text-base font-bold mb-0.5 transition-colors ${activeTab === index ? 'text-text-primary' : 'text-text-primary'}`}>
                                            {feature.title}
                                        </h3>
                                        <p className={`text-sm leading-relaxed transition-colors ${activeTab === index ? 'text-text-secondary' : 'text-text-muted'}`}>
                                            {feature.desc}
                                        </p>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* --- VISUAL STAGE --- */}
                    <div className="relative h-[350px] sm:h-[400px] lg:h-[500px] w-full perspective-1000">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeTab}
                                initial={{ opacity: 0, x: 20, rotateY: 5 }}
                                animate={{ opacity: 1, x: 0, rotateY: 0 }}
                                exit={{ opacity: 0, x: -20, rotateY: -5 }}
                                transition={{ duration: 0.4, ease: "easeOut" }}
                                className="absolute inset-0"
                            >
                                <div className="w-full h-full glass-panel border border-main rounded-3xl shadow-2xl overflow-hidden relative flex flex-col">
                                    {/* Mockup Header */}
                                    <div className="h-8 lg:h-10 bg-surface/40 border-b border-main flex items-center px-4 gap-2 flex-shrink-0">
                                        <div className="w-2.5 h-2.5 rounded-full bg-danger-start" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-warning-start" />
                                        <div className="w-2.5 h-2.5 rounded-full bg-success-start" />
                                    </div>
                                    
                                    {/* Mockup Body */}
                                    <div className="p-4 lg:p-6 flex-1 bg-gradient-to-b from-canvas/20 to-canvas/10 relative overflow-hidden">
                                        {features[activeTab].mockup}
                                    </div>

                                    {/* Mobile Footer Desc */}
                                    <div className="lg:hidden p-4 bg-surface/30 border-t border-main backdrop-blur-md">
                                        <p className="text-sm text-text-secondary text-center">
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

// --- MOCKUPS (Glass Style with Semantic Colors) ---

const WarRoomMockup = () => (
    <div className="space-y-3 lg:space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700 h-full flex flex-col justify-center">
        <div className="flex items-center gap-3 mb-2 lg:mb-6">
            <div className="p-2 bg-danger-start/10 rounded-lg border border-danger-start/20"><ShieldAlert className="text-danger-start w-5 h-5 lg:w-6 lg:h-6" /></div>
            <div className="h-3 lg:h-4 w-32 bg-surface/20 rounded" />
        </div>
        <div className="p-3 lg:p-4 bg-danger-start/10 border border-danger-start/20 rounded-xl shadow-inner">
            <div className="flex items-center gap-2 mb-2 text-danger-start font-bold text-[10px] lg:text-xs uppercase">
                <Sparkles size={12} /> Kontradiktë e Gjetur
            </div>
            <div className="space-y-2">
                <div className="h-2 lg:h-3 w-full bg-danger-start/10 rounded" />
                <div className="h-2 lg:h-3 w-3/4 bg-danger-start/10 rounded" />
            </div>
        </div>
        <div className="flex gap-3 lg:gap-4">
            <div className="flex-1 p-3 lg:p-4 bg-primary-start/10 border border-primary-start/20 rounded-xl">
                <div className="text-primary-start font-bold text-[10px] lg:text-xs mb-2">PALA E PADITUR</div>
                <div className="h-1.5 lg:h-2 w-full bg-primary-start/10 rounded mb-1" />
                <div className="h-1.5 lg:h-2 w-1/2 bg-primary-start/10 rounded" />
            </div>
            <div className="flex-1 p-3 lg:p-4 bg-surface/20 border border-main rounded-xl opacity-60">
                <div className="text-text-muted font-bold text-[10px] lg:text-xs mb-2">PROVA</div>
                <div className="h-1.5 lg:h-2 w-full bg-surface/20 rounded mb-1" />
                <div className="h-1.5 lg:h-2 w-1/2 bg-surface/20 rounded" />
            </div>
        </div>
    </div>
);

const DeepScanMockup = () => (
    <div className="space-y-2 lg:space-y-3 h-full flex flex-col justify-center">
        {[1, 2, 3, 4].map((i) => (
            <motion.div key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.2 }} className="flex items-center justify-between p-2 lg:p-3 bg-surface/20 border border-main rounded-lg">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 lg:p-2 bg-primary-start/10 rounded-lg"><FileText className="w-3 h-3 lg:w-4 lg:h-4 text-primary-start" /></div>
                    <div className="space-y-1"><div className="h-1.5 lg:h-2 w-16 lg:w-24 bg-surface/30 rounded" /><div className="h-1 lg:h-1.5 w-10 lg:w-16 bg-surface/20 rounded" /></div>
                </div>
                <div className="flex items-center gap-2 lg:gap-3">
                    <div className="w-16 lg:w-24 h-1 lg:h-1.5 bg-surface/30 rounded-full overflow-hidden"><motion.div initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 1.5, delay: i * 0.2 }} className="h-full bg-success-start" /></div>
                    <CheckCircle className="w-3 h-3 lg:w-4 lg:h-4 text-success-start" />
                </div>
            </motion.div>
        ))}
    </div>
);

const DraftingMockup = () => (
    <div className="relative h-full flex flex-col">
        <div className="flex gap-2 mb-4 border-b border-main pb-2">
            <div className="w-4 h-4 lg:w-6 lg:h-6 bg-surface/30 rounded" />
            <div className="w-4 h-4 lg:w-6 lg:h-6 bg-surface/30 rounded" />
            <div className="w-4 h-4 lg:w-6 lg:h-6 bg-surface/30 rounded" />
            <div className="flex-1" />
            <div className="w-12 lg:w-20 h-4 lg:h-6 bg-primary-start/20 rounded" />
        </div>
        <div className="space-y-2 lg:space-y-3">
            <motion.div initial={{ width: 0 }} animate={{ width: "60%" }} transition={{ duration: 1 }} className="h-3 lg:h-4 bg-surface/30 rounded" />
            <motion.div initial={{ width: 0 }} animate={{ width: "90%" }} transition={{ duration: 1.5, delay: 0.5 }} className="h-2 lg:h-3 bg-surface/20 rounded" />
            <motion.div initial={{ width: 0 }} animate={{ width: "85%" }} transition={{ duration: 1.5, delay: 1 }} className="h-2 lg:h-3 bg-surface/20 rounded" />
             <motion.div initial={{ width: 0 }} animate={{ width: "40%" }} transition={{ duration: 0.5, delay: 2 }} className="h-2 lg:h-3 bg-surface/20 rounded" />
        </div>
        <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 2.5 }} className="absolute bottom-2 lg:bottom-10 right-0 left-0 mx-2 lg:mx-4 p-3 bg-primary-start/90 backdrop-blur-sm border border-primary-start/40 rounded-xl shadow-lg">
            <div className="flex items-center gap-2 mb-1"><BrainCircuit className="w-3 h-3 lg:w-4 lg:h-4 text-text-primary" /><span className="text-[9px] lg:text-[10px] text-text-primary font-bold uppercase">Juristi AI</span></div>
            <div className="text-[10px] lg:text-xs text-text-primary/90">Duke analizuar Ligjin nr. 03/L-006... Sugjeroj të shtoni Nenin 14.</div>
        </motion.div>
    </div>
);

const ArchiveMockup = () => (
    <div className="grid grid-cols-2 gap-3 lg:gap-4 h-full content-center">
        {[1, 2, 3, 4].map(i => (
            <motion.div key={i} whileHover={{ scale: 1.05 }} className="aspect-square bg-surface/20 border border-main rounded-xl p-3 lg:p-4 flex flex-col items-center justify-center gap-2 lg:gap-3 cursor-pointer hover:bg-surface/40 transition-colors">
                <FolderOpen className={`w-8 h-8 lg:w-10 lg:h-10 ${i === 1 ? 'text-accent-start' : 'text-primary-start'}`} />
                <div className="h-1.5 lg:h-2 w-12 lg:w-16 bg-surface/30 rounded" />
            </motion.div>
        ))}
    </div>
);

const FinanceMockup = () => (
    <div className="h-full flex flex-col gap-4 justify-center animate-in fade-in zoom-in-95 duration-500">
        <div className="flex gap-3">
            <div className="flex-1 bg-success-start/10 border border-success-start/20 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2 text-success-start font-bold text-[10px] uppercase"><TrendingUp size={12} /> Të Hyra</div>
                <div className="text-lg lg:text-xl font-mono text-text-primary">€ 2,450</div>
            </div>
            <div className="flex-1 bg-danger-start/10 border border-danger-start/20 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2 text-danger-start font-bold text-[10px] uppercase"><TrendingUp size={12} className="rotate-180" /> Shpenzime</div>
                <div className="text-lg lg:text-xl font-mono text-text-primary">€ 850</div>
            </div>
        </div>
        
        <div className="bg-surface/20 border border-main rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <span className="text-text-secondary text-xs uppercase font-bold tracking-wider">Tatimi i Llogaritur (ATK)</span>
                <span className="text-xs bg-accent-start/20 text-accent-start px-2 py-0.5 rounded font-bold">Q4 2025</span>
            </div>
            <div className="w-full bg-surface/30 rounded-full h-2 mb-2">
                <div className="bg-accent-start h-2 rounded-full w-[65%]"></div>
            </div>
            <div className="flex justify-between text-xs">
                <span className="text-text-muted">Progresi</span>
                <span className="text-text-primary font-mono">€ 144.00</span>
            </div>
        </div>

        <div className="space-y-2">
            {[1, 2].map(i => (
                <div key={i} className="flex justify-between items-center p-2 bg-surface/20 rounded-lg text-xs">
                    <div className="flex items-center gap-2">
                        <FileText size={12} className="text-text-muted" />
                        <span className="text-text-secondary">Fatura #{100+i} - Konsultim</span>
                    </div>
                    <span className="text-success-start font-mono">+ € 150</span>
                </div>
            ))}
        </div>
    </div>
);

export default ProductShowcase;