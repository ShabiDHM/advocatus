// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V6.4 (DATA INTEGRITY SYNC)
// 1. FIX: Synchronized with aggregate API payload to resolve "undefined" title.
// 2. STABILITY: Multi-layer nullish coalescing on all metadata fields.
// 3. UI: Updated tab title logic to use backend organization data.

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
    title: string; date: string; type: string; description: string;
}

interface SharedDocument {
    id: string; file_name: string; created_at: string; file_type: string; source: 'ACTIVE' | 'ARCHIVE';
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

                // Synchronize Document Title
                if (portalData) {
                    const pageTitle = `${portalData.title ?? 'Portal'} | ${portalData.organization_name ?? 'Zyra Ligjore'}`;
                    document.title = pageTitle;
                }
            } catch (err) {
                console.error('Portal Error:', err);
                setError(t('portal.error_not_found', "Dosja nuk u gjet ose nuk keni qasje."));
                document.title = `Error | ${t('branding.fallback', 'Zyra Ligjore')}`;
            } finally {
                setLoading(false);
            }
        };
        if (caseId) fetchPublicData();
    }, [caseId, t]);

    const getLogoUrl = () => {
        if (!data?.logo) return null;
        if (data.logo.startsWith('http')) return data.logo;
        const baseUrl = API_V1_URL.replace(/\/$/, '');
        return `${baseUrl}${data.logo.startsWith('/') ? data.logo : `/${data.logo}`}`;
    };

    const getDownloadUrl = (docId: string, source: 'ACTIVE' | 'ARCHIVE') => `${API_V1_URL}/cases/public/${caseId}/documents/${docId}/download?source=${source}`;

    const handleDownload = (docId: string, source: 'ACTIVE' | 'ARCHIVE') => window.open(getDownloadUrl(docId, source), '_blank');

    const handleView = (docId: string, source: 'ACTIVE' | 'ARCHIVE', filename: string, mimeType: string) => {
        const url = getDownloadUrl(docId, source);
        setViewingUrl(url);
        setViewingDoc({ id: docId, file_name: filename, mime_type: mimeType, status: 'READY' } as Document);
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
            <p className="text-gray-500 text-sm font-medium tracking-widest uppercase animate-pulse">{t('portal.loading', 'Duke ngarkuar të dhënat...')}</p>
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
    const timeline = data.timeline || [];
    const documents = data.documents || [];

    return (
        <div className="min-h-screen bg-background-dark font-sans text-gray-100 selection:bg-primary-start/30 pb-20 relative overflow-hidden">
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary-start/10 rounded-full blur-[120px] opacity-40"></div>
                <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-secondary-start/10 rounded-full blur-[100px] opacity-30"></div>
            </div>

            <header className="sticky top-0 z-50 bg-background-dark/80 backdrop-blur-xl border-b border-white/5 transition-all">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {logoSrc && !imgError ? (
                            <img src={logoSrc} alt="Firm" className="w-8 h-8 rounded-lg object-contain bg-white/5 border border-white/10" onError={() => setImgError(true)} />
                        ) : (
                            <div className="w-8 h-8 bg-gradient-to-br from-primary-start to-primary-end rounded-lg flex items-center justify-center"><Building2 className="text-white w-4 h-4" /></div>
                        )}
                        <span className="font-bold text-sm tracking-wide text-white">{data.organization_name ?? t('branding.fallback', 'Zyra Ligjore')}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] sm:text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
                        <ShieldCheck size={12} /> {t('portal.secure_connection', 'Lidhje e Sigurt')}
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-8 relative z-10">
                <div className="relative mb-10">
                    <div className="glass-panel p-6 sm:p-8 rounded-3xl shadow-2xl relative overflow-hidden border border-white/5 bg-gradient-to-br from-white/5 to-transparent">
                        <div className="mb-8">
                            <h1 className="text-3xl sm:text-4xl font-bold text-blue-400 leading-tight mb-2">{data.title}</h1>
                            {data.created_at && (
                                <div className="text-gray-400 text-sm font-medium flex items-center gap-2">
                                    <span>{t('portal.created_at', 'Krijuar më')}:</span>
                                    <span className="text-gray-300">{new Date(data.created_at).toLocaleDateString(t('locale.date', 'sq-AL'))}</span>
                                </div>
                            )}
                        </div>
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 text-primary-400 mb-3"><User size={16} /><h3 className="text-xs font-bold tracking-widest uppercase text-primary-300 opacity-80">{t('portal.client_info', 'Informacioni i Klientit')}</h3></div>
                            <div className="space-y-3">
                                <div className="text-xl font-bold text-white pl-1">{data.client_name}</div>
                                <div className="flex flex-col gap-2">
                                    {data.client_email && <div className="flex items-center gap-3 text-gray-400 group"><div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center border border-blue-500/20"><Mail size={14} className="text-blue-400" /></div><span className="text-sm">{data.client_email}</span></div>}
                                    {data.client_phone && <div className="flex items-center gap-3 text-gray-400 group"><div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center border border-blue-500/20"><Phone size={14} className="text-blue-400" /></div><span className="text-sm">{data.client_phone}</span></div>}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex justify-center mb-8">
                    <div className="glass-panel p-1.5 rounded-full flex gap-1">
                        <button onClick={() => setActiveTab('timeline')} className={`px-6 py-2.5 rounded-full text-sm font-bold transition-all ${activeTab === 'timeline' ? 'bg-white text-black' : 'text-gray-400 hover:text-white'}`}>{t('portal.timeline', 'Terminet')}</button>
                        <button onClick={() => setActiveTab('documents')} className={`px-6 py-2.5 rounded-full text-sm font-bold transition-all flex items-center gap-2 ${activeTab === 'documents' ? 'bg-white text-black' : 'text-gray-400 hover:text-white'}`}>{t('portal.documents', 'Dokumentet')} {documents.length > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary-start/20 text-primary-start">{documents.length}</span>}</button>
                    </div>
                </div>

                <AnimatePresence mode="wait">
                    {activeTab === 'timeline' ? (
                        <motion.div key="timeline" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
                            {timeline.length === 0 ? (
                                <div className="glass-panel text-center py-20 rounded-3xl border-dashed"><Calendar className="text-gray-500 mx-auto mb-4" size={32} /><p className="text-gray-500 text-sm">{t('portal.empty_timeline', 'Nuk ka termine.')}</p></div>
                            ) : (
                                timeline.map((ev, i) => (
                                    <div key={i} className="group relative pl-8 pb-8 last:pb-0">
                                        <div className="absolute left-[15px] top-[24px] bottom-0 w-px bg-gradient-to-b from-white/20 to-transparent last:hidden" />
                                        <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-background-dark border border-white/20 flex items-center justify-center z-10 group-hover:border-primary-start transition-all"><div className="scale-75 text-gray-400 group-hover:text-primary-start">{getEventIcon(ev.type)}</div></div>
                                        <div className="glass-panel rounded-2xl p-6 hover:bg-white/5 transition-all ml-4 group-hover:-translate-y-1">
                                            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-2">
                                                <h3 className="text-base font-bold text-white">{ev.title}</h3>
                                                <span className="text-xs font-mono font-bold text-primary-300 bg-primary-500/10 px-2 py-1 rounded-lg border border-primary-500/20">{new Date(ev.date).toLocaleDateString(t('locale.date', 'sq-AL'))}</span>
                                            </div>
                                            <p className="text-gray-300 text-sm leading-relaxed">{ev.description}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </motion.div>
                    ) : (
                        <motion.div key="documents" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid gap-4">
                            {documents.length === 0 ? (
                                <div className="glass-panel text-center py-20 rounded-3xl border-dashed"><FileText className="text-gray-500 mx-auto mb-4" size={32} /><p className="text-gray-500 text-sm">{t('portal.empty_documents', 'Nuk ka dokumente.')}</p></div>
                            ) : (
                                documents.map((doc, i) => (
                                    <div key={i} className="glass-panel rounded-2xl p-4 hover:bg-white/5 transition-all flex items-center justify-between group">
                                        <div className="flex items-center gap-4 min-w-0">
                                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 flex-shrink-0 group-hover:shadow-[0_0_15px_rgba(59,130,246,0.2)]"><FileText size={20} /></div>
                                            <div className="min-w-0"><h4 className="text-sm font-bold text-white truncate pr-4">{doc.file_name}</h4><span className="text-[10px] text-gray-400 font-mono">{new Date(doc.created_at).toLocaleDateString()}</span></div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button onClick={() => handleView(doc.id, doc.source, doc.file_name, doc.file_type)} className="p-2.5 bg-white/5 hover:bg-white/20 rounded-xl text-gray-400 transition-all"><Eye size={18} /></button>
                                            <button onClick={() => handleDownload(doc.id, doc.source)} className="p-2.5 bg-white/5 hover:bg-white/20 rounded-xl text-gray-400 transition-all"><Download size={18} /></button>
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