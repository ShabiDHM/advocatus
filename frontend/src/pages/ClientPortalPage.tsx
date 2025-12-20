// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V4.1 (MINIMALIST HEADER)
// 1. UI: Removed Status Badge and Case Number as requested.
// 2. CLEANUP: Removed unused status logic and icons.

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
        <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center text-white">
            <Loader2 className="w-12 h-12 animate-spin text-indigo-500 mb-6" />
            <p className="text-gray-500 text-sm font-medium tracking-widest uppercase animate-pulse">
                {t('portal.loading', 'Duke ngarkuar të dhënat...')}
            </p>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-6">
            <div className="bg-red-500/5 border border-red-500/20 p-10 rounded-3xl text-center max-w-md backdrop-blur-md">
                <ShieldCheck className="w-16 h-16 text-red-500 mx-auto mb-6" />
                <h1 className="text-2xl font-bold text-white mb-3">{t('portal.access_denied', 'Qasja u Refuzua')}</h1>
                <p className="text-gray-400 leading-relaxed">{error}</p>
            </div>
        </div>
    );

    const logoSrc = getLogoUrl();

    return (
        <div className="min-h-screen bg-[#050505] font-sans text-gray-100 selection:bg-indigo-500/30 pb-20">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-[#050505]/90 backdrop-blur-xl border-b border-white/5">
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
                            <div className="w-8 h-8 bg-indigo-900/30 border border-indigo-500/30 rounded-lg flex items-center justify-center">
                                <Building2 className="text-indigo-400 w-4 h-4" />
                            </div>
                        )}
                        <span className="font-semibold text-sm tracking-wide text-gray-200">
                            {data.organization_name || t('branding.fallback', 'Zyra Ligjore')}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] sm:text-xs font-medium text-emerald-500 bg-emerald-500/5 px-3 py-1.5 rounded-full border border-emerald-500/10">
                        <ShieldCheck size={12} />
                        {t('portal.secure_connection', 'Lidhje e Sigurt')}
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-8">
                
                {/* HERO SECTION - Minimalist */}
                <div className="relative mb-10 group">
                    <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 via-purple-500/5 to-transparent rounded-3xl blur-2xl group-hover:from-indigo-500/15 transition-all duration-700" />
                    
                    <div className="relative bg-[#0F0F0F] border border-white/10 rounded-3xl p-6 sm:p-10 shadow-2xl overflow-hidden">
                        {/* Decorative Background Elements */}
                        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-600/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                        
                        <div className="flex flex-col sm:flex-row justify-between items-start gap-6 relative z-10">
                            <div className="space-y-4 max-w-2xl">
                                
                                {/* PHOENIX FIX: Removed Status and Case Number Badges here */}
                                
                                <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white leading-tight tracking-tight mt-2">
                                    {data.title}
                                </h1>
                                
                                <div className="flex items-center gap-2 text-gray-400 pt-2">
                                    <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center">
                                        <Briefcase size={14} className="text-gray-300"/>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">{t('portal.client_label', 'Klient')}</span>
                                        <span className="text-sm font-medium text-gray-200">{data.client_name}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* TABS */}
                <div className="flex justify-center mb-8">
                    <div className="bg-white/5 border border-white/10 p-1 rounded-full flex gap-1">
                        <button 
                            onClick={() => setActiveTab('timeline')} 
                            className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
                                activeTab === 'timeline' 
                                ? 'bg-white text-black shadow-lg shadow-white/5' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            {t('portal.timeline', 'Kronologjia')}
                        </button>
                        <button 
                            onClick={() => setActiveTab('documents')} 
                            className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                                activeTab === 'documents' 
                                ? 'bg-white text-black shadow-lg shadow-white/5' 
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                        >
                            {t('portal.documents', 'Dokumentet')} 
                            {data.documents.length > 0 && (
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${activeTab === 'documents' ? 'bg-black/10 text-black' : 'bg-white/10 text-white'}`}>
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
                                <div className="text-center py-20 bg-[#0F0F0F] border border-dashed border-white/10 rounded-3xl">
                                    <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <Calendar className="text-gray-500 opacity-50" size={32} />
                                    </div>
                                    <p className="text-gray-500 text-sm">{t('portal.empty_timeline', 'Nuk ka ngjarje në kronologji.')}</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {data.timeline.map((ev, i) => (
                                        <div key={i} className="group relative pl-8 pb-8 last:pb-0">
                                            {/* Timeline Line */}
                                            <div className="absolute left-[15px] top-[24px] bottom-0 w-px bg-white/10 group-last:hidden" />
                                            
                                            {/* Timeline Dot */}
                                            <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-[#0F0F0F] border border-white/10 flex items-center justify-center z-10 group-hover:border-indigo-500/50 group-hover:shadow-[0_0_15px_rgba(99,102,241,0.2)] transition-all">
                                                <div className="scale-75 text-gray-400 group-hover:text-indigo-400 transition-colors">
                                                    {getEventIcon(ev.type)}
                                                </div>
                                            </div>

                                            {/* Event Card */}
                                            <div className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-5 hover:bg-white/[0.02] hover:border-white/20 transition-all ml-4">
                                                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-2 gap-2">
                                                    <h3 className="text-base font-bold text-gray-200">{ev.title}</h3>
                                                    <span className="text-xs font-mono text-indigo-300 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20 whitespace-nowrap self-start sm:self-auto">
                                                        {new Date(ev.date).toLocaleDateString(t('locale.date', 'sq-AL'))}
                                                    </span>
                                                </div>
                                                <p className="text-gray-400 text-sm leading-relaxed">{ev.description}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </motion.div>
                    )}

                    {activeTab === 'documents' && (
                        <motion.div key="documents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }}>
                            <div className="grid grid-cols-1 gap-3">
                                {data.documents.length === 0 ? (
                                    <div className="text-center py-20 bg-[#0F0F0F] border border-dashed border-white/10 rounded-3xl">
                                        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <FileText className="text-gray-500 opacity-50" size={32} />
                                        </div>
                                        <p className="text-gray-500 text-sm">{t('portal.empty_documents', 'Nuk ka dokumente të ndara me ju.')}</p>
                                    </div>
                                ) : (
                                    data.documents.map((doc, i) => (
                                        <div key={i} className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-4 hover:border-white/20 hover:bg-white/[0.02] transition-all flex items-center justify-between group">
                                            <div className="flex items-center gap-4 min-w-0">
                                                <div className="w-12 h-12 rounded-xl bg-blue-500/5 border border-blue-500/10 flex items-center justify-center text-blue-400 flex-shrink-0 group-hover:bg-blue-500/10 transition-colors">
                                                    <FileText size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <h4 className="text-sm font-bold text-gray-200 truncate pr-4">{doc.file_name}</h4>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span className="text-[10px] text-gray-500 font-mono">{new Date(doc.created_at).toLocaleDateString()}</span>
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
                                                    className="p-2.5 bg-white/5 hover:bg-white/10 hover:text-white rounded-xl text-gray-400 transition-all border border-transparent hover:border-white/10" 
                                                    title={t('actions.view', 'Shiko')}
                                                >
                                                    <Eye size={18} />
                                                </button>
                                                <button 
                                                    onClick={() => handleDownload(doc.id, doc.source)} 
                                                    className="p-2.5 bg-white/5 hover:bg-white/10 hover:text-white rounded-xl text-gray-400 transition-all border border-transparent hover:border-white/10" 
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