// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V2.9.1 (CLEANUP)
// 1. FIX: Removed unused 'Scale' import to resolve TypeScript warning.

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Calendar, AlertCircle, Loader2, 
    FileText, Gavel, Users, ShieldCheck, 
    Briefcase, Euro, Download, Eye, Building2
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
    const [activeTab, setActiveTab] = useState<'timeline' | 'documents' | 'finance'>('timeline');
    const [imgError, setImgError] = useState(false); // Track image loading errors

    // Viewer State
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);

    useEffect(() => {
        const fetchPublicData = async () => {
            try {
                const response = await axios.get(`${API_V1_URL}/cases/public/${caseId}/timeline`);
                setData(response.data);
            } catch (err) {
                console.error(err);
                setError(t('portal.error_not_found', "Dosja nuk u gjet ose nuk keni qasje."));
            } finally {
                setLoading(false);
            }
        };
        if (caseId) fetchPublicData();
    }, [caseId, t]);

    // --- LOGO URL CONSTRUCTOR ---
    const getLogoUrl = () => {
        if (!data?.logo) return null;
        if (data.logo.startsWith('http')) return data.logo;
        // Prepend API URL if it's a relative path from backend
        // Remove trailing slash from API_URL if exists, ensure leading slash on logo
        const baseUrl = API_V1_URL.replace(/\/$/, '');
        const path = data.logo.startsWith('/') ? data.logo : `/${data.logo}`;
        return `${baseUrl}${path}`;
    };

    const getDownloadUrl = (docId: string, source: 'ACTIVE' | 'ARCHIVE' | 'INVOICE') => {
        if (source === 'INVOICE') {
             return `${API_V1_URL}/cases/public/${caseId}/invoices/${docId}/download`;
        }
        return `${API_V1_URL}/cases/public/${caseId}/documents/${docId}/download?source=${source}`;
    };

    const handleDownload = (docId: string, source: 'ACTIVE' | 'ARCHIVE' | 'INVOICE') => {
        if (!caseId) return;
        const url = getDownloadUrl(docId, source);
        window.open(url, '_blank');
    };

    const handleView = (docId: string, source: 'ACTIVE' | 'ARCHIVE' | 'INVOICE', filename: string, mimeType: string) => {
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

    const getStatusBadge = (status: string) => {
        const normalizedStatus = status ? status.toUpperCase() : 'OPEN';
        const color = normalizedStatus === 'PAID' ? 'bg-green-500/20 text-green-400' : 
                      normalizedStatus === 'SENT' ? 'bg-blue-500/20 text-blue-400' : 
                      'bg-gray-500/20 text-gray-400';
        
        return (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border border-white/5 ${color}`}>
                {t(`status.${normalizedStatus}`, normalizedStatus)}
            </span>
        );
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
        <div className="min-h-screen bg-[#0a0a0a] font-sans text-gray-100 selection:bg-indigo-500/30 pb-20">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-white/5">
                <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {logoSrc && !imgError ? (
                            <img 
                                src={logoSrc} 
                                alt="Firm Logo" 
                                className="w-8 h-8 rounded-lg object-contain bg-white/5" 
                                onError={() => setImgError(true)}
                            />
                        ) : (
                            // Fallback Icon if logo missing or fails to load
                            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                <Building2 className="text-white w-4 h-4" />
                            </div>
                        )}
                        <span className="font-bold text-lg tracking-tight">
                            {data.organization_name || t('branding.fallback', 'Zyra Ligjore')}
                        </span>
                    </div>
                    <div className="hidden sm:flex items-center gap-4 text-xs font-medium text-gray-500">
                        <span className="flex items-center gap-2">
                            <ShieldCheck size={14} className="text-green-500"/> 
                            {t('portal.secure_connection', 'Lidhje e Sigurt')}
                        </span>
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-10">
                {/* Dashboard Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                    <div className="md:col-span-2 bg-white/5 border border-white/10 rounded-3xl p-8 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/20 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                        <div className="relative z-10">
                            <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2 leading-tight">
                                {data.title}
                            </h1>
                            <p className="text-gray-400 flex items-center gap-2 text-sm mt-4">
                                <Briefcase size={16} /> 
                                {t('portal.client_label', 'Klient')}: <span className="text-white font-medium">{data.client_name}</span>
                            </p>
                        </div>
                    </div>

                    <div className="bg-white/5 border border-white/10 rounded-3xl p-6 flex flex-col justify-center items-center text-center relative overflow-hidden">
                        <div className="w-3 h-3 bg-green-500 rounded-full shadow-[0_0_10px_rgba(34,197,94,0.6)] mb-4 animate-pulse" />
                        <h3 className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1">
                            {t('portal.status_label', 'Statusi i Çështjes')}
                        </h3>
                        <p className="text-2xl font-bold text-white">
                            {t(`status.${data.status.toUpperCase()}`, data.status)}
                        </p>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-8 overflow-x-auto no-scrollbar pb-2">
                    <button 
                        onClick={() => setActiveTab('timeline')} 
                        className={`px-6 py-3 rounded-full text-sm font-bold transition-all whitespace-nowrap ${activeTab === 'timeline' ? 'bg-white text-black shadow-lg shadow-white/10' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}
                    >
                        {t('portal.timeline', 'Kronologjia')}
                    </button>
                    <button 
                        onClick={() => setActiveTab('documents')} 
                        className={`px-6 py-3 rounded-full text-sm font-bold transition-all whitespace-nowrap flex items-center gap-2 ${activeTab === 'documents' ? 'bg-white text-black shadow-lg shadow-white/10' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}
                    >
                        {t('portal.documents', 'Dokumentet')} 
                        <span className="bg-black/20 px-2 py-0.5 rounded-full text-xs">{data.documents.length}</span>
                    </button>
                    <button 
                        onClick={() => setActiveTab('finance')} 
                        className={`px-6 py-3 rounded-full text-sm font-bold transition-all whitespace-nowrap flex items-center gap-2 ${activeTab === 'finance' ? 'bg-white text-black shadow-lg shadow-white/10' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}
                    >
                        {t('portal.finances', 'Financat')} 
                        <span className="bg-black/20 px-2 py-0.5 rounded-full text-xs">{data.invoices.length}</span>
                    </button>
                </div>

                {/* Tab Content */}
                <AnimatePresence mode="wait">
                    {activeTab === 'timeline' && (
                        <motion.div key="timeline" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                            {data.timeline.length === 0 ? (
                                <div className="text-center py-20 text-gray-500 italic border border-dashed border-white/10 rounded-3xl">
                                    {t('portal.empty_timeline', 'Nuk ka ngjarje në kronologji.')}
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {data.timeline.map((ev, i) => (
                                        <div key={i} className="flex gap-6 group">
                                            <div className="flex flex-col items-center">
                                                <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-indigo-500/20 group-hover:border-indigo-500/50 transition-colors">
                                                    {getEventIcon(ev.type)}
                                                </div>
                                                <div className="w-px h-full bg-white/10 my-2 group-last:hidden" />
                                            </div>
                                            <div className="flex-1 bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all mb-2">
                                                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-2">
                                                    <h3 className="text-lg font-bold text-white">{ev.title}</h3>
                                                    <span className="text-xs font-mono text-gray-400 bg-black/30 px-3 py-1 rounded-lg border border-white/5">
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
                        <motion.div key="documents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {data.documents.length === 0 ? (
                                    <div className="md:col-span-2 text-center py-20 text-gray-500 italic border border-dashed border-white/10 rounded-3xl">
                                        {t('portal.empty_documents', 'Nuk ka dokumente të ndara me ju.')}
                                    </div>
                                ) : (
                                    data.documents.map((doc, i) => (
                                        <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:bg-white/10 transition-colors flex items-center justify-between group">
                                            <div className="flex items-center gap-4 min-w-0">
                                                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 flex-shrink-0">
                                                    <FileText size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <h4 className="text-sm font-bold text-white truncate max-w-[200px]">{doc.file_name}</h4>
                                                    <p className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                                                        {new Date(doc.created_at).toLocaleDateString()}
                                                        {doc.source === 'ARCHIVE' && (
                                                            <span className="bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded text-[9px] uppercase font-bold">
                                                                {t('portal.archive', 'Arkivë')}
                                                            </span>
                                                        )}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <button 
                                                    onClick={() => handleView(doc.id, doc.source, doc.file_name, doc.file_type)} 
                                                    className="p-2 bg-white/5 hover:bg-white/20 rounded-lg text-blue-400 transition-colors" 
                                                    title={t('actions.view', 'Shiko')}
                                                >
                                                    <Eye size={18} />
                                                </button>
                                                <button 
                                                    onClick={() => handleDownload(doc.id, doc.source)} 
                                                    className="p-2 bg-white/5 hover:bg-white/20 rounded-lg text-gray-300 transition-colors" 
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

                    {activeTab === 'finance' && (
                        <motion.div key="finance" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                            <div className="space-y-3">
                                {data.invoices.length === 0 ? (
                                    <div className="text-center py-20 text-gray-500 italic border border-dashed border-white/10 rounded-3xl">
                                        {t('portal.empty_invoices', 'Nuk ka fatura aktive.')}
                                    </div>
                                ) : (
                                    data.invoices.map((inv, i) => (
                                        <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-5 flex items-center justify-between hover:bg-white/10 transition-colors">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                                                    <Euro size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <h4 className="text-sm font-bold text-white truncate max-w-[150px]">
                                                        {t('portal.invoice_prefix', 'Fatura #')}{inv.number}
                                                    </h4>
                                                    <p className="text-xs text-gray-500 mt-0.5">{new Date(inv.date).toLocaleDateString()}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="text-right">
                                                    <p className="text-lg font-bold text-white mb-1">€{inv.amount.toFixed(2)}</p>
                                                    {getStatusBadge(inv.status)}
                                                </div>
                                                
                                                <div className="flex flex-col gap-1 ml-2">
                                                    <button 
                                                        onClick={() => handleView(inv.id, 'INVOICE', `Fatura_${inv.number}.pdf`, 'application/pdf')} 
                                                        className="p-1.5 bg-white/5 hover:bg-white/20 rounded-lg text-blue-400 transition-colors" 
                                                        title={t('actions.view', 'Shiko')}
                                                    >
                                                        <Eye size={16} />
                                                    </button>
                                                    <button 
                                                        onClick={() => handleDownload(inv.id, 'INVOICE')} 
                                                        className="p-1.5 bg-white/5 hover:bg-white/20 rounded-lg text-green-400 transition-colors" 
                                                        title={t('actions.download', 'Shkarko')}
                                                    >
                                                        <Download size={18} />
                                                    </button>
                                                </div>
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