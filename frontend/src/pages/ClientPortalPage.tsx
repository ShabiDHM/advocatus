// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V6.6 (DOWNLOAD RESTORATION & SYNC)
// 1. FIX: Restored Download button and handled TS6133 unused import warning.
// 2. MIRROR: Fully aligned with Manual Share logic (is_public/is_shared).
// 3. STABILITY: Hardened date parsing to eliminate "Invalid Date" errors.

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Calendar, AlertCircle, Loader2, 
    FileText, Gavel, Users, ShieldCheck, 
    Download, Eye, Building2, Mail, Phone, User
} from 'lucide-react';
import axios from 'axios';
import { API_V1_URL } from '../services/api';
import PDFViewerModal from '../components/FileViewerModal';
import { Document } from '../data/types';
import { useTranslation } from 'react-i18next';

interface PublicEvent {
    title: string; 
    date: string; // ISO String from backend
    type: string; 
    description: string;
}

interface SharedDocument {
    id: string; 
    file_name: string; 
    created_at: string; 
    file_type: string; 
    source: 'ACTIVE' | 'ARCHIVE';
}

interface PublicCaseData {
    case_number: string; 
    title: string; 
    client_name: string; 
    client_email?: string;
    client_phone?: string;
    created_at?: string;
    status: string;
    organization_name?: string; 
    logo?: string; 
    timeline: PublicEvent[];
    documents: SharedDocument[];
}

const ClientPortalPage: React.FC = () => {
    const { caseId } = useParams<{ caseId: string }>();
    const { t } = useTranslation();
    const [data, setData] = useState<PublicCaseData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState<'timeline' | 'documents'>('timeline');
    const [imgError, setImgError] = useState(false);

    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);

    useEffect(() => {
        const fetchPublicData = async () => {
            try {
                const response = await axios.get(`${API_V1_URL}/cases/public/${caseId}/timeline`);
                const portalData = response.data;
                setData(portalData);

                if (portalData) {
                    document.title = `${portalData.title || 'Portal'} | ${portalData.organization_name || 'Juristi'}`;
                }
            } catch (err) {
                console.error('Portal Sync Error:', err);
                setError(t('portal.error_not_found', "Dosja nuk u gjet ose nuk keni qasje."));
            } finally {
                setLoading(false);
            }
        };
        if (caseId) fetchPublicData();
    }, [caseId, t]);

    const formatPortalDate = (dateStr: string | undefined) => {
        if (!dateStr) return '---';
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return '---';
        return date.toLocaleDateString(t('locale.date', 'sq-AL'), {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    };

    const getLogoUrl = () => {
        if (!data?.logo) return null;
        if (data.logo.startsWith('http')) return data.logo;
        const baseUrl = API_V1_URL.replace(/\/$/, '');
        return `${baseUrl}${data.logo.startsWith('/') ? data.logo : `/${data.logo}`}`;
    };

    const getDownloadUrl = (docId: string, source: 'ACTIVE' | 'ARCHIVE') => {
        return `${API_V1_URL}/cases/public/${caseId}/documents/${docId}/download?source=${source}`;
    };

    const handleDownload = (docId: string, source: 'ACTIVE' | 'ARCHIVE') => {
        const url = getDownloadUrl(docId, source);
        window.open(url, '_blank');
    };

    const handleView = (docId: string, source: 'ACTIVE' | 'ARCHIVE', filename: string, mimeType: string) => {
        const url = getDownloadUrl(docId, source);
        setViewingUrl(url);
        setViewingDoc({ id: docId, file_name: filename, mime_type: mimeType, status: 'READY' } as Document);
    };

    const getEventIcon = (type: string) => {
        switch (type.toUpperCase()) {
            case 'DEADLINE': return <AlertCircle className="text-rose-400" />;
            case 'HEARING': return <Gavel className="text-purple-400" />;
            case 'MEETING': return <Users className="text-blue-400" />;
            default: return <Calendar className="text-gray-400" />;
        }
    };

    if (loading) return (
        <div className="min-h-screen bg-background-dark flex flex-col items-center justify-center text-white">
            <Loader2 className="w-12 h-12 animate-spin text-primary-start mb-6" />
            <p className="text-gray-500 text-sm font-medium uppercase animate-pulse">{t('portal.loading', 'Duke ngarkuar...')}</p>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-background-dark flex flex-col items-center justify-center p-6 text-center">
            <ShieldCheck className="w-16 h-16 text-red-500 mb-6 mx-auto" />
            <h1 className="text-2xl font-bold text-white mb-2">{t('portal.error', 'Gabim')}</h1>
            <p className="text-gray-400">{error}</p>
        </div>
    );

    const logoSrc = getLogoUrl();
    const timeline = data.timeline || [];
    const documents = data.documents || [];

    return (
        <div className="min-h-screen bg-background-dark font-sans text-gray-100 selection:bg-primary-start/30 pb-20 relative overflow-hidden">
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary-start/5 rounded-full blur-[120px]"></div>
            </div>

            <header className="sticky top-0 z-50 bg-background-dark/80 backdrop-blur-xl border-b border-white/5 h-16 flex items-center">
                <div className="max-w-4xl mx-auto px-6 w-full flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {logoSrc && !imgError ? (
                            <img src={logoSrc} alt="Logo" className="w-8 h-8 rounded-lg object-contain bg-white/5" onError={() => setImgError(true)} />
                        ) : (
                            <div className="w-8 h-8 bg-primary-start rounded-lg flex items-center justify-center"><Building2 className="text-white w-4 h-4" /></div>
                        )}
                        <span className="font-bold text-sm text-white">{data.organization_name || 'Juristi'}</span>
                    </div>
                    <div className="text-[10px] sm:text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20 flex items-center gap-2">
                        <ShieldCheck size={12} /> {t('portal.secure_connection', 'Lidhje e Sigurt')}
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-6 pt-8 relative z-10">
                <div className="glass-panel p-8 rounded-3xl border border-white/5 mb-8 bg-white/5 backdrop-blur-md shadow-2xl">
                    <h1 className="text-3xl font-bold text-blue-400 mb-2">{data.title}</h1>
                    <p className="text-gray-400 text-sm mb-8">{t('portal.created_at', 'Krijuar më')}: {formatPortalDate(data.created_at)}</p>
                    
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 text-primary-300 text-xs font-bold uppercase tracking-wider opacity-60">
                            <User size={14} /> {t('portal.client_info', 'Informacioni i Klientit')}
                        </div>
                        <div className="text-xl font-bold text-white">{data.client_name}</div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {data.client_email && (
                                <div className="flex items-center gap-3 text-gray-400">
                                    <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center border border-white/10"><Mail size={14} /></div>
                                    <span className="text-sm">{data.client_email}</span>
                                </div>
                            )}
                            {data.client_phone && (
                                <div className="flex items-center gap-3 text-gray-400">
                                    <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center border border-white/10"><Phone size={14} /></div>
                                    <span className="text-sm">{data.client_phone}</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex justify-center mb-10">
                    <div className="bg-white/5 p-1 rounded-full flex gap-1 border border-white/5 backdrop-blur-md">
                        <button onClick={() => setActiveTab('timeline')} className={`px-8 py-2.5 rounded-full text-sm font-bold transition-all duration-300 ${activeTab === 'timeline' ? 'bg-white text-black shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>{t('portal.timeline', 'Terminet')}</button>
                        <button onClick={() => setActiveTab('documents')} className={`px-8 py-2.5 rounded-full text-sm font-bold transition-all duration-300 ${activeTab === 'documents' ? 'bg-white text-black shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>{t('portal.documents', 'Dokumentet')}</button>
                    </div>
                </div>

                <AnimatePresence mode="wait">
                    {activeTab === 'timeline' ? (
                        <motion.div key="timeline" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-6">
                            {timeline.length === 0 ? (
                                <div className="text-center py-20 opacity-30 bg-white/5 rounded-3xl border border-dashed border-white/10"><Calendar size={48} className="mx-auto mb-4" /><p>{t('portal.empty_timeline', 'Nuk ka termine.')}</p></div>
                            ) : (
                                timeline.map((ev, i) => (
                                    <div key={i} className="relative pl-8 pb-8 last:pb-0 group">
                                        <div className="absolute left-[15px] top-[24px] bottom-0 w-px bg-white/10 last:hidden" />
                                        <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-background-dark border border-white/20 flex items-center justify-center z-10 group-hover:border-primary-start transition-colors duration-300">{getEventIcon(ev.type)}</div>
                                        <div className="glass-panel p-6 rounded-2xl ml-4 hover:bg-white/5 transition-all duration-300 border border-white/5 hover:border-white/20">
                                            <div className="flex justify-between items-start mb-2 gap-4">
                                                <h3 className="font-bold text-white">{ev.title}</h3>
                                                <span className="text-[10px] font-mono font-bold bg-white/10 px-2 py-1 rounded text-primary-300 whitespace-nowrap">{formatPortalDate(ev.date)}</span>
                                            </div>
                                            <p className="text-gray-400 text-sm leading-relaxed">{ev.description}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </motion.div>
                    ) : (
                        <motion.div key="documents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid gap-4">
                            {documents.length === 0 ? (
                                <div className="text-center py-20 opacity-30 bg-white/5 rounded-3xl border border-dashed border-white/10"><FileText size={48} className="mx-auto mb-4" /><p>{t('portal.empty_documents', 'Nuk ka dokumente.')}</p></div>
                            ) : (
                                documents.map((doc, i) => (
                                    <div key={i} className="glass-panel p-4 rounded-2xl flex items-center justify-between group hover:bg-white/5 transition-all duration-300 border border-white/5 hover:border-white/20">
                                        <div className="flex items-center gap-4 min-w-0">
                                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 flex-shrink-0 group-hover:bg-blue-500/20 transition-colors"><FileText size={20} /></div>
                                            <div className="min-w-0"><h4 className="text-sm font-bold text-white truncate pr-4">{doc.file_name}</h4><span className="text-[10px] text-gray-500 font-medium">{formatPortalDate(doc.created_at)}</span></div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button 
                                                onClick={() => handleView(doc.id, doc.source, doc.file_name, doc.file_type)} 
                                                className="p-2.5 bg-white/5 hover:bg-white/20 rounded-xl text-gray-400 hover:text-white transition-all border border-white/5 hover:border-white/20"
                                                title={t('actions.view', 'Shiko')}
                                            >
                                                <Eye size={18} />
                                            </button>
                                            <button 
                                                onClick={() => handleDownload(doc.id, doc.source)} 
                                                className="p-2.5 bg-white/5 hover:bg-white/20 rounded-xl text-gray-400 hover:text-white transition-all border border-white/5 hover:border-white/20"
                                                title={t('actions.download', 'Shkarko')}
                                            >
                                                <Download size={18} />
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={() => setViewingDoc(null)} t={t} directUrl={viewingUrl} isAuth={false} />}
        </div>
    );
};

export default ClientPortalPage;