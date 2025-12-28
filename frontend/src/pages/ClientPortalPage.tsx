// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V5.0 (GLASS & EXTERNAL)
// 1. VISUALS: Full Glassmorphism adoption for external client view.
// 2. HEADER: Frosted glass sticky header for premium feel.
// 3. UX: Smoother transitions and refined document cards.

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Calendar, AlertCircle, Loader2, 
    FileText, Gavel, Users, ShieldCheck, 
    Briefcase, Download, Eye, Building2
} from 'lucide-react';
import axios from 'axios';
import { API_V1_URL } from '../services/api';
import PDFViewerModal from '../components/PDFViewerModal';
import { Document } from '../data/types';
import { useTranslation } from 'react-i18next';

// --- TYPES ---
interface PublicEvent {
    title: string; date: string; type: string; description: string;
}

interface SharedDocument {
    id: string; file_name: string; created_at: string; file_type: string; source: 'ACTIVE' | 'ARCHIVE';
}

interface SharedInvoice {
    id: string; number: string; amount: number; status: string; date: string;
}

interface PublicCaseData {
    case_number: string; 
    title: string; 
    client_name: string; 
    status: string;
    organization_name?: string; 
    logo?: string; 
    timeline: PublicEvent[];
    documents: SharedDocument[];
    invoices: SharedInvoice[];
}

// --- MAIN COMPONENT ---
const ClientPortalPage: React.FC = () => {
    const { caseId } = useParams<{ caseId: string }>();
    const { t } = useTranslation();
    const [data, setData] = useState<PublicCaseData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState<'timeline' | 'documents'>('timeline');
    const [imgError, setImgError] = useState(false);

    // Viewer State
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);

    useEffect(() => {
        const fetchPublicData = async () => {
            try {
                const response = await axios.get(`${API_V1_URL}/cases/public/${caseId}/timeline`);
                const caseData = response.data;
                setData(caseData);

                if (caseData) {
                    const pageTitle = `${caseData.title} | ${caseData.organization_name || 'Portal'}`;
                    document.title = pageTitle;
                    
                    updateMetaTag('og:title', pageTitle);
                    updateMetaTag('og:description', `Dosja: ${caseData.case_number} - Klient: ${caseData.client_name}`);
                }

            } catch (err) {
                console.error(err);
                setError(t('portal.error_not_found', "Dosja nuk u gjet ose nuk keni qasje."));
            } finally {
                setLoading(false);
            }
        };
        if (caseId) fetchPublicData();
    }, [caseId, t]);

    const updateMetaTag = (property: string, content: string) => {
        let meta = document.querySelector(`meta[property="${property}"]`);
        if (!meta) {
            meta = document.createElement('meta');
            meta.setAttribute('property', property);
            document.head.appendChild(meta);
        }
        meta.setAttribute('content', content);
    };

    const getLogoUrl = () => {
        if (!data?.logo) return null;
        if (data.logo.startsWith('http')) return data.logo;
        const baseUrl = API_V1_URL.replace(/\/$/, '');
        const path = data.logo.startsWith('/') ? data.logo : `/${data.logo}`;
        return `${baseUrl}${path}`;
    };

    const getDownloadUrl = (docId: string, source: 'ACTIVE' | 'ARCHIVE') => {
        return `${API_V1_URL}/cases/public/${caseId}/documents/${docId}/download?source=${source}`;
    };

    const handleDownload = (docId: string, source: 'ACTIVE' | 'ARCHIVE') => {
        if (!caseId) return;
        const url = getDownloadUrl(docId, source);
        window.open(url, '_blank');
    };

    const handleView = (docId: string, source: 'ACTIVE' | 'ARCHIVE', filename: string, mimeType: string) => {
        const url = getDownloadUrl(docId, source);
        if (!url) return;
        
        setViewingUrl(url);
        setViewingDoc({
            id: docId,
            file_name: filename,
            mime_type: mimeType,
            status: 'READY'
        } as Document);
    };
    
    const closeViewer = () => {
        setViewingDoc(null);
        setViewingUrl(null);
    };

    const getEventIcon = (type: string) => {
        switch (type) {
            case 'DEADLINE': return <AlertCircle className="text-rose-400" />;
            case 'HEARING': return <Gavel className="text-purple-400" />;
            case 'MEETING': return <Users className="text-blue-400" />;
            default: return <Calendar className="text-gray-400" />;
        }
    };

    if (loading) return (
        <div className="min-h-screen bg-background-dark flex flex-col items-center justify-center text-white">
            <Loader2 className="w-12 h-12 animate-spin text-primary-start mb-6" />
            <p className="text-gray-500 text-sm font-medium tracking-widest uppercase animate-pulse">
                {t('portal.loading', 'Duke ngarkuar të dhënat...')}
            </p>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-background-dark flex flex-col items-center justify-center p-6">
            <div className="bg-red-500/5 border border-red-500/20 p-10 rounded-3xl text-center max-w-md backdrop-blur-md shadow-2xl">
                <ShieldCheck className="w-16 h-16 text-red-500 mx-auto mb-6" />
                <h1 className="text-2xl font-bold text-white mb-3">{t('portal.access_denied', 'Qasja u Refuzua')}</h1>
                <p className="text-gray-400 leading-relaxed">{error}</p>
            </div>
        </div>
    );

    const logoSrc = getLogoUrl();

    return (
        <div className="min-h-screen bg-background-dark font-sans text-gray-100 selection:bg-primary-start/30 pb-20 relative overflow-hidden">
            {/* Ambient Background */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary-start/10 rounded-full blur-[120px] opacity-40"></div>
                <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-secondary-start/10 rounded-full blur-[100px] opacity-30"></div>
            </div>

            {/* Header - Glass Style */}
            <header className="sticky top-0 z-50 bg-background-dark/80 backdrop-blur-xl border-b border-white/5 transition-all">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {logoSrc && !imgError ? (
                            <img 
                                src={logoSrc} 
                                alt="Firm Logo" 
                                className="w-8 h-8 rounded-lg object-contain bg-white/5 border border-white/10" 
                                onError={() => setImgError(true)}
                            />
                        ) : (
                            <div className="w-8 h-8 bg-gradient-to-br from-primary-start to-primary-end rounded-lg flex items-center justify-center shadow-lg shadow-primary-start/20">
                                <Building2 className="text-white w-4 h-4" />
                            </div>
                        )}
                        <span className="font-bold text-sm tracking-wide text-white">
                            {data.organization_name || t('branding.fallback', 'Zyra Ligjore')}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] sm:text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
                        <ShieldCheck size={12} />
                        {t('portal.secure_connection', 'Lidhje e Sigurt')}
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-8 relative z-10">
                
                {/* HERO SECTION - Glass Card */}
                <div className="relative mb-10 group">
                    <div className="absolute inset-0 bg-gradient-to-r from-primary-start/20 via-secondary-start/10 to-transparent rounded-3xl blur-xl opacity-50 group-hover:opacity-70 transition-opacity duration-700" />
                    
                    <div className="glass-panel p-6 sm:p-10 rounded-3xl shadow-2xl relative overflow-hidden">
                        <div className="flex flex-col sm:flex-row justify-between items-start gap-6 relative z-10">
                            <div className="space-y-4 max-w-2xl">
                                <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white leading-tight tracking-tight mt-2 drop-shadow-sm">
                                    {data.title}
                                </h1>
                                
                                <div className="flex items-center gap-3 text-gray-400 pt-2">
                                    <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/5">
                                        <Briefcase size={16} className="text-gray-300"/>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">{t('portal.client_label', 'Klient')}</span>
                                        <span className="text-base font-medium text-white">{data.client_name}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* TABS - Glass Style */}
                <div className="flex justify-center mb-8">
                    <div className="glass-panel p-1.5 rounded-full flex gap-1 shadow-lg">
                        <button 
                            onClick={() => setActiveTab('timeline')} 
                            className={`px-6 py-2.5 rounded-full text-sm font-bold transition-all duration-300 ${
                                activeTab === 'timeline' 
                                ? 'bg-white text-black shadow-lg' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            {t('portal.timeline', 'Kronologjia')}
                        </button>
                        <button 
                            onClick={() => setActiveTab('documents')} 
                            className={`px-6 py-2.5 rounded-full text-sm font-bold transition-all duration-300 flex items-center gap-2 ${
                                activeTab === 'documents' 
                                ? 'bg-white text-black shadow-lg' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            {t('portal.documents', 'Dokumentet')} 
                            {data.documents.length > 0 && (
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${activeTab === 'documents' ? 'bg-black/10 text-black' : 'bg-white/20 text-white'}`}>
                                    {data.documents.length}
                                </span>
                            )}
                        </button>
                    </div>
                </div>

                {/* CONTENT AREA */}
                <AnimatePresence mode="wait">
                    {activeTab === 'timeline' && (
                        <motion.div key="timeline" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
                            {data.timeline.length === 0 ? (
                                <div className="glass-panel text-center py-20 rounded-3xl border-dashed">
                                    <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <Calendar className="text-gray-500 opacity-50" size={32} />
                                    </div>
                                    <p className="text-gray-500 text-sm">{t('portal.empty_timeline', 'Nuk ka ngjarje në kronologji.')}</p>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {data.timeline.map((ev, i) => (
                                        <div key={i} className="group relative pl-8 pb-8 last:pb-0">
                                            {/* Timeline Line */}
                                            <div className="absolute left-[15px] top-[24px] bottom-0 w-px bg-gradient-to-b from-white/20 to-transparent group-last:hidden" />
                                            
                                            {/* Timeline Dot */}
                                            <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-background-dark border border-white/20 flex items-center justify-center z-10 group-hover:border-primary-start group-hover:shadow-[0_0_15px_rgba(37,99,235,0.4)] transition-all">
                                                <div className="scale-75 text-gray-400 group-hover:text-primary-start transition-colors">
                                                    {getEventIcon(ev.type)}
                                                </div>
                                            </div>

                                            {/* Event Card - Glass Style */}
                                            <div className="glass-panel rounded-2xl p-6 hover:bg-white/5 transition-all ml-4 group-hover:-translate-y-1 duration-300">
                                                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-2">
                                                    <h3 className="text-base font-bold text-white">{ev.title}</h3>
                                                    <span className="text-xs font-mono font-bold text-primary-300 bg-primary-500/10 px-2 py-1 rounded-lg border border-primary-500/20 whitespace-nowrap self-start sm:self-auto">
                                                        {new Date(ev.date).toLocaleDateString(t('locale.date', 'sq-AL'))}
                                                    </span>
                                                </div>
                                                <p className="text-gray-300 text-sm leading-relaxed">{ev.description}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </motion.div>
                    )}

                    {activeTab === 'documents' && (
                        <motion.div key="documents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
                            <div className="grid grid-cols-1 gap-4">
                                {data.documents.length === 0 ? (
                                    <div className="glass-panel text-center py-20 rounded-3xl border-dashed">
                                        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <FileText className="text-gray-500 opacity-50" size={32} />
                                        </div>
                                        <p className="text-gray-500 text-sm">{t('portal.empty_documents', 'Nuk ka dokumente të ndara me ju.')}</p>
                                    </div>
                                ) : (
                                    data.documents.map((doc, i) => (
                                        <div key={i} className="glass-panel rounded-2xl p-4 hover:bg-white/5 transition-all flex items-center justify-between group hover:-translate-y-0.5 duration-200">
                                            <div className="flex items-center gap-4 min-w-0">
                                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400 flex-shrink-0 group-hover:shadow-[0_0_15px_rgba(59,130,246,0.2)] transition-all">
                                                    <FileText size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <h4 className="text-sm font-bold text-white truncate pr-4">{doc.file_name}</h4>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span className="text-[10px] text-gray-400 font-mono font-medium">{new Date(doc.created_at).toLocaleDateString()}</span>
                                                        {doc.source === 'ARCHIVE' && (
                                                            <span className="bg-purple-500/10 text-purple-300 border border-purple-500/20 px-1.5 py-0.5 rounded-[4px] text-[9px] uppercase font-bold tracking-wider">
                                                                {t('portal.archive', 'Arkivë')}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <button 
                                                    onClick={() => handleView(doc.id, doc.source, doc.file_name, doc.file_type)} 
                                                    className="p-2.5 bg-white/5 hover:bg-white/20 hover:text-white rounded-xl text-gray-400 transition-all border border-white/5 hover:border-white/20" 
                                                    title={t('actions.view', 'Shiko')}
                                                >
                                                    <Eye size={18} />
                                                </button>
                                                <button 
                                                    onClick={() => handleDownload(doc.id, doc.source)} 
                                                    className="p-2.5 bg-white/5 hover:bg-white/20 hover:text-white rounded-xl text-gray-400 transition-all border border-white/5 hover:border-white/20" 
                                                    title={t('actions.download', 'Shkarko')}
                                                >
                                                    <Download size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={closeViewer} t={t} directUrl={viewingUrl} isAuth={false} />}
        </div>
    );
};

export default ClientPortalPage;