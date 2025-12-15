// FILE: src/components/landing/ProductShowcase.tsx
// PHOENIX PROTOCOL - LANDING PRESENTATION V1.1 (LINTER CLEANUP)
// 1. CLEANUP: Removed unused imports (React, Search, ArrowRight).
// 2. STATUS: Clean build.

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { 
    ShieldAlert, FileText, ScanEye, BrainCircuit, 
    CheckCircle, PenTool, FolderOpen, 
    Sparkles, Gavel
} from 'lucide-react';

const ProductShowcase = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState(0);

    // Auto-rotate slides every 8 seconds if user doesn't interact
    useEffect(() => {
        const timer = setInterval(() => {
            setActiveTab((prev) => (prev + 1) % 4);
        }, 8000);
        return () => clearInterval(timer);
    }, []);

    const features = [
        {
            id: 0,
            title: t('showcase.slide1_title', 'Dhoma e Luftës'),
            desc: t('showcase.slide1_desc', 'Gjeni gënjeshtrat automatikisht.'),
            icon: <Gavel className="w-6 h-6" />,
            color: "from-orange-500 to-red-600",
            mockup: <WarRoomMockup />
        },
        {
            id: 1,
            title: t('showcase.slide2_title', 'Deep Scan OCR'),
            desc: t('showcase.slide2_desc', 'Skanoni 50+ dokumente në sekonda.'),
            icon: <ScanEye className="w-6 h-6" />,
            color: "from-blue-500 to-cyan-500",
            mockup: <DeepScanMockup />
        },
        {
            id: 2,
            title: t('showcase.slide3_title', 'Hartim i Padukshëm'),
            desc: t('showcase.slide3_desc', 'Ju shkruani strategjinë, ne shkruajmë nenet.'),
            icon: <PenTool className="w-6 h-6" />,
            color: "from-emerald-500 to-green-500",
            mockup: <DraftingMockup />
        },
        {
            id: 3,
            title: t('showcase.slide4_title', 'Arkiva e Gjallë'),
            desc: t('showcase.slide4_desc', 'Çdo dokument, i indeksuar dhe i sigurt.'),
            icon: <FolderOpen className="w-6 h-6" />,
            color: "from-purple-500 to-indigo-500",
            mockup: <ArchiveMockup />
        }
    ];

    return (
        <div className="py-24 bg-background-dark relative overflow-hidden">
            {/* Background Gradients */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-primary-start/10 rounded-full blur-[100px]" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-secondary-start/10 rounded-full blur-[100px]" />
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                <div className="text-center mb-16">
                    <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                        {t('showcase.title', 'Jo Thjesht Softuer. Partneri Juaj.')}
                    </h2>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                        {t('showcase.subtitle', 'Inteligjencë Artificiale e ndërtuar për sistemin e Kosovës.')}
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    {/* LEFT: Controls */}
                    <div className="space-y-6">
                        {features.map((feature, index) => (
                            <button
                                key={feature.id}
                                onClick={() => setActiveTab(index)}
                                className={`w-full text-left p-6 rounded-2xl transition-all duration-300 border group ${
                                    activeTab === index 
                                    ? 'bg-white/10 border-white/20 shadow-2xl scale-[1.02]' 
                                    : 'bg-transparent border-transparent hover:bg-white/5'
                                }`}
                            >
                                <div className="flex items-center gap-4">
                                    <div className={`p-3 rounded-xl bg-gradient-to-br ${feature.color} text-white shadow-lg`}>
                                        {feature.icon}
                                    </div>
                                    <div>
                                        <h3 className={`text-lg font-bold mb-1 transition-colors ${activeTab === index ? 'text-white' : 'text-gray-300'}`}>
                                            {feature.title}
                                        </h3>
                                        <p className={`text-sm leading-relaxed transition-colors ${activeTab === index ? 'text-gray-300' : 'text-gray-500'}`}>
                                            {feature.desc}
                                        </p>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* RIGHT: Visual Stage */}
                    <div className="relative h-[500px] w-full perspective-1000">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={activeTab}
                                initial={{ opacity: 0, x: 50, rotateY: 10 }}
                                animate={{ opacity: 1, x: 0, rotateY: 0 }}
                                exit={{ opacity: 0, x: -50, rotateY: -10 }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                                className="absolute inset-0"
                            >
                                <div className="w-full h-full bg-gray-900 rounded-3xl border border-glass-edge shadow-2xl overflow-hidden relative">
                                    {/* Mockup Header */}
                                    <div className="h-10 bg-black/40 border-b border-white/5 flex items-center px-4 gap-2">
                                        <div className="w-3 h-3 rounded-full bg-red-500" />
                                        <div className="w-3 h-3 rounded-full bg-yellow-500" />
                                        <div className="w-3 h-3 rounded-full bg-green-500" />
                                    </div>
                                    
                                    {/* Mockup Body */}
                                    <div className="p-6 h-full bg-gradient-to-b from-gray-900 to-gray-800">
                                        {features[activeTab].mockup}
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

// --- CSS MOCKUPS (Abstract UI Representations) ---

const WarRoomMockup = () => (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-orange-500/20 rounded-lg"><ShieldAlert className="text-orange-500 w-6 h-6" /></div>
            <div className="h-4 w-32 bg-gray-700 rounded animate-pulse" />
        </div>
        
        {/* Contradiction Card */}
        <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-xl">
            <div className="flex items-center gap-2 mb-2 text-red-400 font-bold text-xs uppercase">
                <Sparkles size={12} /> Kontradiktë e Gjetur
            </div>
            <div className="space-y-2">
                <div className="h-3 w-full bg-red-500/10 rounded" />
                <div className="h-3 w-3/4 bg-red-500/10 rounded" />
            </div>
        </div>

        {/* Evidence Link */}
        <div className="flex gap-4">
            <div className="flex-1 p-4 bg-blue-900/20 border border-blue-500/30 rounded-xl">
                <div className="text-blue-400 font-bold text-xs mb-2">PALA E PADITUR</div>
                <div className="h-2 w-full bg-blue-500/10 rounded mb-1" />
                <div className="h-2 w-1/2 bg-blue-500/10 rounded" />
            </div>
            <div className="flex-1 p-4 bg-gray-800 border border-white/5 rounded-xl opacity-50">
                <div className="text-gray-500 font-bold text-xs mb-2">PROVA</div>
                <div className="h-2 w-full bg-gray-700 rounded mb-1" />
                <div className="h-2 w-1/2 bg-gray-700 rounded" />
            </div>
        </div>
    </div>
);

const DeepScanMockup = () => (
    <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
            <motion.div 
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.2 }}
                className="flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-lg"
            >
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded"><FileText className="w-4 h-4 text-blue-400" /></div>
                    <div className="space-y-1">
                        <div className="h-2 w-24 bg-gray-700 rounded" />
                        <div className="h-1.5 w-16 bg-gray-800 rounded" />
                    </div>
                </div>
                {/* Progress Bar Animation */}
                <div className="flex items-center gap-3">
                    <div className="w-24 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: "100%" }}
                            transition={{ duration: 1.5, delay: i * 0.2 }}
                            className="h-full bg-green-500"
                        />
                    </div>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                </div>
            </motion.div>
        ))}
    </div>
);

const DraftingMockup = () => (
    <div className="relative h-full">
        {/* Editor Toolbar */}
        <div className="flex gap-2 mb-4 border-b border-white/5 pb-2">
            <div className="w-6 h-6 bg-gray-800 rounded" />
            <div className="w-6 h-6 bg-gray-800 rounded" />
            <div className="w-6 h-6 bg-gray-800 rounded" />
            <div className="flex-1" />
            <div className="w-20 h-6 bg-primary-600/30 rounded" />
        </div>
        
        {/* Typing Animation */}
        <div className="space-y-3">
            <motion.div 
                initial={{ width: 0 }} animate={{ width: "60%" }} 
                transition={{ duration: 1 }} className="h-4 bg-gray-600 rounded opacity-50" 
            />
            <motion.div 
                initial={{ width: 0 }} animate={{ width: "90%" }} 
                transition={{ duration: 1.5, delay: 0.5 }} className="h-3 bg-gray-700 rounded opacity-30" 
            />
            <motion.div 
                initial={{ width: 0 }} animate={{ width: "85%" }} 
                transition={{ duration: 1.5, delay: 1 }} className="h-3 bg-gray-700 rounded opacity-30" 
            />
             <motion.div 
                initial={{ width: 0 }} animate={{ width: "40%" }} 
                transition={{ duration: 0.5, delay: 2 }} className="h-3 bg-gray-700 rounded opacity-30" 
            />
        </div>

        {/* AI Suggestion Pop-up */}
        <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 2.5 }}
            className="absolute bottom-10 right-0 left-0 mx-4 p-3 bg-indigo-900/80 backdrop-blur border border-indigo-500/50 rounded-xl"
        >
            <div className="flex items-center gap-2 mb-1">
                <BrainCircuit className="w-4 h-4 text-indigo-300" />
                <span className="text-[10px] text-indigo-200 font-bold uppercase">Juristi AI</span>
            </div>
            <div className="text-xs text-white">
                Duke analizuar Ligjin nr. 03/L-006... Sugjeroj të shtoni Nenin 14.
            </div>
        </motion.div>
    </div>
);

const ArchiveMockup = () => (
    <div className="grid grid-cols-2 gap-4">
        {[1, 2, 3, 4].map(i => (
            <motion.div 
                key={i}
                whileHover={{ scale: 1.05 }}
                className="aspect-square bg-gray-800/50 border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center gap-3 cursor-pointer"
            >
                <FolderOpen className={`w-10 h-10 ${i === 1 ? 'text-yellow-500' : 'text-blue-500'}`} />
                <div className="h-2 w-16 bg-gray-700 rounded" />
            </motion.div>
        ))}
    </div>
);

export default ProductShowcase;