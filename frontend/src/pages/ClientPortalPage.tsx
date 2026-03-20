// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary, text-text-muted, btn-primary.
// 2. Preserved all client portal functionality: timeline, documents, PDF viewer.
// 3. Maintained mobile responsiveness and touch-optimized targets.

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
    date: string; 
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
        const fetchPortal = async () => {
            try {
                const res = await axios.get(`${API_V1_URL}/cases/public/${caseId}/timeline`);
                setData(res.data);
                if (res.data) {
                    document.title = `${res.data.title || 'Portal'} | ${res.data.organization_name || 'Juristi'}`;
                }
            } catch (err) { 
                console.error("Portal Fetch Error:", err);
                setError(t('portal.error_not_found', "Dosja nuk u gjet ose nuk keni qasje.")); 
            } finally { 
                setLoading(false); 
            }
        };
        if (caseId) fetchPortal();
    }, [caseId, t]);

    const getDocUrl = (id: string, src: string) => `${API_V1_URL}/cases/public/${caseId}/documents/${id}/download?source=${src}`;

    const handleView = (doc: SharedDocument) => {
        setViewingUrl(getDocUrl(doc.id, doc.source));
        setViewingDoc({ id: doc.id, file_name: doc.file_name, mime_type: doc.file_type, status: 'READY' } as Document);
    };

    const getEventIcon = (type: string) => {
        const typeKey = type.toUpperCase();
        if (typeKey === 'DEADLINE') return <AlertCircle size={14} className="text-accent-start" />;
        if (typeKey === 'HEARING') return <Gavel size={14} className="text-secondary-start" />;
        if (typeKey === 'MEETING') return <Users size={14} className="text-primary-start" />;
        return <Calendar size={14} className="text-text-muted" />;
    };

    if (loading) return (
        <div className="min-h-screen bg-canvas flex flex-col items-center justify-center">
            <Loader2 className="w-10 h-10 animate-spin text-primary-start mb-4" />
            <p className="text-text-muted text-[10px] font-bold uppercase tracking-widest">{t('portal.loading', 'Ngarkimi...')}</p>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-canvas flex flex-col items-center justify-center p-6 text-center">
            <ShieldCheck className="w-12 h-12 text-danger-start mb-4 mx-auto" />
            <h1 className="text-xl font-bold text-text-primary mb-2">{t('portal.error', 'Gabim')}</h1>
            <p className="text-text-secondary text-sm">{error}</p>
        </div>
    );

    const logoSrc = data.logo ? (data.logo.startsWith('http') ? data.logo : `${API_V1_URL.replace(/\/$/, '')}${data.logo.startsWith('/') ? data.logo : `/${data.logo}`}`) : null;
    const documents = data.documents || [];
    const timeline = data.timeline || [];

    return (
        <div className="min-h-screen bg-canvas text-text-primary pb-10 relative overflow-x-hidden">
            {/* Subtle ambient effect using semantic colors */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary-start/5 rounded-full blur-[120px]"></div>
            </div>

            <header className="sticky top-0 z-50 bg-canvas/80 backdrop-blur-xl border-b border-main h-16 flex items-center px-4 sm:px-6">
                <div className="max-w-4xl mx-auto w-full flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {logoSrc && !imgError ? (
                            <img src={logoSrc} className="w-7 h-7 rounded bg-surface/20 object-contain" onError={() => setImgError(true)} />
                        ) : (
                            <div className="w-7 h-7 bg-primary-start rounded flex items-center justify-center text-text-primary">
                                <Building2 size={16} />
                            </div>
                        )}
                        <span className="font-bold text-xs sm:text-sm truncate max-w-[150px] text-text-primary">
                            {data.organization_name || t('branding.fallback', 'Zyra Ligjore')}
                        </span>
                    </div>
                    <div className="text-[10px] font-bold text-success-start bg-success-start/10 px-2.5 py-1 rounded-full border border-success-start/20 flex items-center gap-1.5">
                        <ShieldCheck size={12} /> {t('portal.secure_connection', 'Sigurt')}
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-6 relative z-10">
                {/* Hero Panel */}
                <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-main mb-6 shadow-2xl">
                    <h1 className="text-2xl sm:text-3xl font-bold text-primary-start mb-1">{data.title}</h1>
                    <p className="text-text-muted text-[10px] sm:text-sm mb-6">
                        {t('portal.created_at', 'Krijuar më')}: {new Date(data.created_at || Date.now()).toLocaleDateString(t('locale.date', 'sq-AL'))}
                    </p>
                    
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 text-primary-start text-[10px] uppercase font-bold tracking-widest opacity-60">
                            <User size={14} /> {t('portal.client_info', 'Klienti')}
                        </div>
                        <div className="text-lg font-bold text-text-primary">{data.client_name}</div>
                        <div className="flex flex-col gap-2">
                            {data.client_email && (
                                <div className="flex items-center gap-2 text-text-secondary text-xs sm:text-sm">
                                    <Mail size={14} className="text-primary-start opacity-70" /> {data.client_email}
                                </div>
                            )}
                            {data.client_phone && (
                                <div className="flex items-center gap-2 text-text-secondary text-xs sm:text-sm">
                                    <Phone size={14} className="text-primary-start opacity-70" /> {data.client_phone}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Tabs Switcher */}
                <div className="flex justify-center mb-8 gap-1 p-1 bg-surface/30 rounded-full w-fit mx-auto border border-main backdrop-blur-md">
                    <button 
                        onClick={() => setActiveTab('timeline')} 
                        className={`px-6 sm:px-10 py-2 rounded-full text-xs sm:text-sm font-bold transition-all duration-300 ${
                            activeTab === 'timeline' 
                                ? 'btn-primary shadow-lg' 
                                : 'text-text-secondary hover:text-text-primary'
                        }`}
                    >
                        {t('portal.timeline', 'Terminet')}
                    </button>
                    <button 
                        onClick={() => setActiveTab('documents')} 
                        className={`px-6 sm:px-10 py-2 rounded-full text-xs sm:text-sm font-bold transition-all duration-300 flex items-center gap-2 ${
                            activeTab === 'documents' 
                                ? 'btn-primary shadow-lg' 
                                : 'text-text-secondary hover:text-text-primary'
                        }`}
                    >
                        {t('portal.documents', 'Skedarët')}
                        {documents.length > 0 && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold transition-colors ${
                                activeTab === 'documents' ? 'bg-primary-start/20 text-primary-start' : 'bg-surface/50 text-text-muted'
                            }`}>
                                {documents.length}
                            </span>
                        )}
                    </button>
                </div>

                <AnimatePresence mode="wait">
                    {activeTab === 'timeline' ? (
                        <motion.div key="timeline" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-4">
                            {timeline.length === 0 ? (
                                <div className="text-center py-20 opacity-30 text-xs bg-surface/20 rounded-2xl border border-dashed border-main">
                                    <Calendar size={48} className="mx-auto mb-4 text-text-muted" />
                                    <p className="text-text-secondary">{t('portal.empty_timeline', 'Nuk ka termine.')}</p>
                                </div>
                            ) : (
                                timeline.map((ev, i) => (
                                    <div key={i} className="relative pl-6 pb-6 last:pb-0 group">
                                        <div className="absolute left-[11px] top-[24px] bottom-0 w-px bg-main last:hidden" />
                                        <div className="absolute left-0 top-0 w-6 h-6 rounded-full bg-canvas border border-main flex items-center justify-center z-10 group-hover:border-primary-start transition-colors">
                                            {getEventIcon(ev.type)}
                                        </div>
                                        <div className="glass-panel p-4 sm:p-6 rounded-xl border border-main ml-3 hover:bg-surface/20 transition-all">
                                            <div className="flex flex-col sm:flex-row justify-between items-start mb-2 gap-1">
                                                <h3 className="font-bold text-text-primary text-sm sm:text-base">{ev.title}</h3>
                                                <span className="text-[9px] font-mono font-bold bg-surface/30 px-2 py-0.5 rounded text-primary-start">
                                                    {new Date(ev.date).toLocaleDateString(t('locale.date', 'sq-AL'))}
                                                </span>
                                            </div>
                                            <p className="text-text-secondary text-xs sm:text-sm leading-relaxed">{ev.description}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </motion.div>
                    ) : (
                        <motion.div key="documents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid gap-3">
                            {documents.length === 0 ? (
                                <div className="text-center py-20 opacity-30 text-xs bg-surface/20 rounded-2xl border border-dashed border-main">
                                    <FileText size={48} className="mx-auto mb-4 text-text-muted" />
                                    <p className="text-text-secondary">{t('portal.empty_documents', 'Nuk ka skedarë.')}</p>
                                </div>
                            ) : (
                                documents.map((doc, i) => (
                                    <div key={i} className="glass-panel p-3 rounded-xl flex items-center justify-between border border-main hover:bg-surface/20 transition-all">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <div className="w-10 h-10 rounded-lg bg-primary-start/10 flex items-center justify-center text-primary-start shrink-0">
                                                <FileText size={18} />
                                            </div>
                                            <div className="min-w-0">
                                                <h4 className="text-xs sm:text-sm font-bold text-text-primary truncate pr-2">{doc.file_name}</h4>
                                                <span className="text-[9px] text-text-muted">
                                                    {new Date(doc.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex gap-1 sm:gap-2">
                                            <button 
                                                onClick={() => handleView(doc)} 
                                                className="p-2 bg-surface/30 hover:bg-surface/60 rounded-lg text-text-secondary hover:text-text-primary transition-all"
                                                title={t('actions.view', 'Shiko')}
                                            >
                                                <Eye size={16} />
                                            </button>
                                            <button 
                                                onClick={() => window.open(getDocUrl(doc.id, doc.source), '_blank')} 
                                                className="p-2 bg-surface/30 hover:bg-surface/60 rounded-lg text-text-secondary hover:text-text-primary transition-all"
                                                title={t('actions.download', 'Shkarko')}
                                            >
                                                <Download size={16} />
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