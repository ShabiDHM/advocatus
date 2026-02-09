// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V7.1 (TAB COUNT RESTORATION)
// 1. FIX: Restored document count badge to the 'Skedarët' tab button.
// 2. UI: Maintained mobile responsiveness and touch-optimized targets.
// 3. INTEGRITY: Standardized icon mapping and TS6133 compliance.

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
        if (typeKey === 'DEADLINE') return <AlertCircle size={14} className="text-rose-400" />;
        if (typeKey === 'HEARING') return <Gavel size={14} className="text-purple-400" />;
        if (typeKey === 'MEETING') return <Users size={14} className="text-blue-400" />;
        return <Calendar size={14} className="text-gray-400" />;
    };

    if (loading) return (
        <div className="min-h-screen bg-background-dark flex flex-col items-center justify-center">
            <Loader2 className="w-10 h-10 animate-spin text-primary-start mb-4" />
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-widest">{t('portal.loading', 'Ngarkimi...')}</p>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-background-dark flex flex-col items-center justify-center p-6 text-center">
            <ShieldCheck className="w-12 h-12 text-red-500 mb-4 mx-auto" />
            <h1 className="text-xl font-bold text-white mb-2">{t('portal.error', 'Gabim')}</h1>
            <p className="text-gray-400 text-sm">{error}</p>
        </div>
    );

    const logoSrc = data.logo ? (data.logo.startsWith('http') ? data.logo : `${API_V1_URL.replace(/\/$/, '')}${data.logo.startsWith('/') ? data.logo : `/${data.logo}`}`) : null;
    const documents = data.documents || [];
    const timeline = data.timeline || [];

    return (
        <div className="min-h-screen bg-background-dark text-gray-100 pb-10 relative overflow-x-hidden">
            {/* Background Ambient Effect */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary-start/5 rounded-full blur-[120px]"></div>
            </div>

            <header className="sticky top-0 z-50 bg-background-dark/80 backdrop-blur-xl border-b border-white/5 h-16 flex items-center px-4 sm:px-6">
                <div className="max-w-4xl mx-auto w-full flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {logoSrc && !imgError ? (
                            <img src={logoSrc} className="w-7 h-7 rounded bg-white/5 object-contain" onError={() => setImgError(true)} />
                        ) : (
                            <div className="w-7 h-7 bg-primary-start rounded flex items-center justify-center text-white">
                                <Building2 size={16} />
                            </div>
                        )}
                        <span className="font-bold text-xs sm:text-sm truncate max-w-[150px]">{data.organization_name || t('branding.fallback', 'Zyra Ligjore')}</span>
                    </div>
                    <div className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 flex items-center gap-1.5">
                        <ShieldCheck size={12} /> {t('portal.secure_connection', 'Sigurt')}
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-6 relative z-10">
                {/* Hero Panel */}
                <div className="glass-panel p-6 sm:p-8 rounded-2xl bg-white/5 border border-white/5 mb-6 shadow-2xl">
                    <h1 className="text-2xl sm:text-3xl font-bold text-blue-400 mb-1">{data.title}</h1>
                    <p className="text-gray-400 text-[10px] sm:text-sm mb-6">
                        {t('portal.created_at', 'Krijuar më')}: {new Date(data.created_at || Date.now()).toLocaleDateString(t('locale.date', 'sq-AL'))}
                    </p>
                    
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 text-primary-300 text-[10px] uppercase font-bold tracking-widest opacity-60">
                            <User size={14} /> {t('portal.client_info', 'Klienti')}
                        </div>
                        <div className="text-lg font-bold text-white">{data.client_name}</div>
                        <div className="flex flex-col gap-2">
                            {data.client_email && (
                                <div className="flex items-center gap-2 text-gray-400 text-xs sm:text-sm">
                                    <Mail size={14} className="text-primary-start opacity-70" /> {data.client_email}
                                </div>
                            )}
                            {data.client_phone && (
                                <div className="flex items-center gap-2 text-gray-400 text-xs sm:text-sm">
                                    <Phone size={14} className="text-primary-start opacity-70" /> {data.client_phone}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Tabs Switcher */}
                <div className="flex justify-center mb-8 gap-1 p-1 bg-white/5 rounded-full w-fit mx-auto border border-white/5 backdrop-blur-md">
                    <button 
                        onClick={() => setActiveTab('timeline')} 
                        className={`px-6 sm:px-10 py-2 rounded-full text-xs sm:text-sm font-bold transition-all duration-300 ${
                            activeTab === 'timeline' ? 'bg-white text-black shadow-lg' : 'text-gray-400 hover:text-white'
                        }`}
                    >
                        {t('portal.timeline', 'Terminet')}
                    </button>
                    <button 
                        onClick={() => setActiveTab('documents')} 
                        className={`px-6 sm:px-10 py-2 rounded-full text-xs sm:text-sm font-bold transition-all duration-300 flex items-center gap-2 ${
                            activeTab === 'documents' ? 'bg-white text-black shadow-lg' : 'text-gray-400 hover:text-white'
                        }`}
                    >
                        {t('portal.documents', 'Skedarët')}
                        {documents.length > 0 && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold transition-colors ${
                                activeTab === 'documents' ? 'bg-blue-500/10 text-blue-600' : 'bg-white/10 text-white'
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
                                <div className="text-center py-20 opacity-30 text-xs bg-white/5 rounded-2xl border border-dashed border-white/10">
                                    <Calendar size={48} className="mx-auto mb-4" />
                                    <p>{t('portal.empty_timeline', 'Nuk ka termine.')}</p>
                                </div>
                            ) : (
                                timeline.map((ev, i) => (
                                    <div key={i} className="relative pl-6 pb-6 last:pb-0 group">
                                        <div className="absolute left-[11px] top-[24px] bottom-0 w-px bg-white/10 last:hidden" />
                                        <div className="absolute left-0 top-0 w-6 h-6 rounded-full bg-background-dark border border-white/20 flex items-center justify-center z-10 group-hover:border-primary-start transition-colors">
                                            {getEventIcon(ev.type)}
                                        </div>
                                        <div className="glass-panel p-4 sm:p-6 rounded-xl bg-white/5 border border-white/5 ml-3 hover:bg-white/10 transition-all">
                                            <div className="flex flex-col sm:flex-row justify-between items-start mb-2 gap-1">
                                                <h3 className="font-bold text-white text-sm sm:text-base">{ev.title}</h3>
                                                <span className="text-[9px] font-mono font-bold bg-white/10 px-2 py-0.5 rounded text-primary-300">
                                                    {new Date(ev.date).toLocaleDateString(t('locale.date', 'sq-AL'))}
                                                </span>
                                            </div>
                                            <p className="text-gray-400 text-xs sm:text-sm leading-relaxed">{ev.description}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </motion.div>
                    ) : (
                        <motion.div key="documents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid gap-3">
                            {documents.length === 0 ? (
                                <div className="text-center py-20 opacity-30 text-xs bg-white/5 rounded-2xl border border-dashed border-white/10">
                                    <FileText size={48} className="mx-auto mb-4" />
                                    <p>{t('portal.empty_documents', 'Nuk ka skedarë.')}</p>
                                </div>
                            ) : (
                                documents.map((doc, i) => (
                                    <div key={i} className="glass-panel p-3 rounded-xl flex items-center justify-between bg-white/5 border border-white/5 hover:bg-white/10 transition-all">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 shrink-0">
                                                <FileText size={18} />
                                            </div>
                                            <div className="min-w-0">
                                                <h4 className="text-xs sm:text-sm font-bold text-white truncate pr-2">{doc.file_name}</h4>
                                                <span className="text-[9px] text-gray-500">
                                                    {new Date(doc.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex gap-1 sm:gap-2">
                                            <button 
                                                onClick={() => handleView(doc)} 
                                                className="p-2 bg-white/5 hover:bg-white/20 rounded-lg text-gray-400 hover:text-white transition-all"
                                                title={t('actions.view', 'Shiko')}
                                            >
                                                <Eye size={16} />
                                            </button>
                                            <button 
                                                onClick={() => window.open(getDocUrl(doc.id, doc.source), '_blank')} 
                                                className="p-2 bg-white/5 hover:bg-white/20 rounded-lg text-gray-400 hover:text-white transition-all"
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