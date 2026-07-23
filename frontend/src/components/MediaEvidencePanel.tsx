// FILE: src/components/MediaEvidencePanel.tsx
// PHOENIX PROTOCOL - MEDIA EVIDENCE PANEL V1.8 (AUDIO-ONLY FOCUS)

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { apiService, API_V1_URL } from '../services/api';
import { 
    Mic, Upload, Trash2, FileText, 
    Loader2, Headphones, Radio, Download, Save, CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface MediaItem {
    id: string;
    file_name: string;
    media_type: 'audio';
    status: 'PROCESSING' | 'READY' | 'FAILED';
    transcript: string;
    created_at: string;
}

interface MediaEvidencePanelProps {
    caseId: string;
    t: any;
}

export default function MediaEvidencePanel({ caseId }: MediaEvidencePanelProps) {
    const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [selectedTranscript, setSelectedTranscript] = useState<MediaItem | null>(null);
    const [isArchiving, setIsArchiving] = useState(false);
    const [archiveSuccess, setArchiveSuccess] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadMedia = async () => {
        try {
            const res = await apiService.axiosInstance.get(`/cases/${caseId}/media`);
            setMediaItems(res.data || []);
        } catch (err) {
            console.error("Failed to load media evidence:", err);
        } finally {
            setIsLoading(false);
        }
    };

    const isProcessing = useMemo(() => mediaItems.some(item => item.status === 'PROCESSING'), [mediaItems]);

    useEffect(() => {
        loadMedia();
    }, [caseId]);

    useEffect(() => {
        if (!isProcessing) return;
        const interval = setInterval(() => {
            loadMedia();
        }, 5000);
        return () => clearInterval(interval);
    }, [isProcessing]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setUploadProgress(10);
        try {
            const formData = new FormData();
            formData.append('file', file);

            setUploadProgress(50);
            await apiService.axiosInstance.post(`/cases/${caseId}/media/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setUploadProgress(100);
            await loadMedia();
        } catch (err: any) {
            alert(err.response?.data?.detail || "Dështoi ngarkimi i skedarit audio.");
        } finally {
            setIsUploading(false);
            setUploadProgress(0);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDelete = async (mediaId: string) => {
        if (!window.confirm("A jeni të sigurt që dëshironi ta fshini këtë provë audio?")) return;
        try {
            await apiService.axiosInstance.delete(`/cases/${caseId}/media/${mediaId}`);
            setMediaItems(prev => prev.filter(m => m.id !== mediaId));
            if (selectedTranscript?.id === mediaId) setSelectedTranscript(null);
        } catch (err) {
            alert("Dështoi fshirja e provës.");
        }
    };

    const handleDownloadTranscript = (item: MediaItem) => {
        const element = document.createElement("a");
        const file = new Blob([item.transcript], { type: 'text/plain;charset=utf-8' });
        element.href = URL.createObjectURL(file);
        element.download = `Transkript_${item.file_name.replace(/\.[^/.]+$/, "")}.txt`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    };

    const handleArchiveTranscript = async (item: MediaItem) => {
        setIsArchiving(true);
        setArchiveSuccess(false);
        try {
            await apiService.archiveForensicReport(
                caseId, 
                `Transkript Audio: ${item.file_name}`, 
                item.transcript
            );
            setArchiveSuccess(true);
            setTimeout(() => setArchiveSuccess(false), 3000);
        } catch (err: any) {
            alert(err.response?.data?.detail || "Dështoi ruajtja në arkiv.");
        } finally {
            setIsArchiving(false);
        }
    };

    const authToken = apiService.getToken();

    return (
        <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-main bg-canvas space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-main pb-5">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary-start/10 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/20">
                        <Headphones size={24} />
                    </div>
                    <div>
                        <h2 className="text-lg font-black text-text-primary uppercase tracking-tight">Provat Audio</h2>
                        <p className="text-xs text-text-muted font-medium">Ngarkoni incizime audio (MP3, WAV, M4A) për transkriptim me AI</p>
                    </div>
                </div>

                <div>
                    <input 
                        type="file" 
                        ref={fileInputRef} 
                        onChange={handleFileUpload} 
                        accept="audio/mp3,audio/wav,audio/m4a,audio/*" 
                        className="hidden" 
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        className="btn-primary h-11 px-5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-primary-start/15 focus:outline-none disabled:opacity-50"
                    >
                        {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                        {isUploading ? `Duke ngarkuar... ${uploadProgress}%` : 'Ngarko Audio (MP3/WAV)'}
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>
            ) : mediaItems.length === 0 ? (
                <div className="text-center py-16 opacity-50 border border-dashed border-main rounded-2xl p-6">
                    <Radio size={40} className="mx-auto mb-3 text-text-disabled animate-pulse" />
                    <p className="text-text-secondary text-sm font-bold">Nuk ka ende prova audio në këtë rast.</p>
                    <p className="text-xs text-text-muted mt-1">Mbështet formate si MP3, WAV, M4A.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {mediaItems.map(item => {
                        const streamUrl = `${API_V1_URL}/cases/${caseId}/media/${item.id}/stream${authToken ? `?token=${authToken}` : ''}`;
                        return (
                            <div key={item.id} className="glass-panel p-5 rounded-2xl border border-main bg-surface flex flex-col justify-between gap-4 shadow-sm">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center shrink-0 border border-primary-start/20">
                                            <Mic size={18} />
                                        </div>
                                        <div className="min-w-0">
                                            <h4 className="text-sm font-bold text-text-primary truncate">{item.file_name}</h4>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-md ${
                                                    item.status === 'READY' ? 'bg-status-success/15 text-status-success border border-status-success/30' :
                                                    item.status === 'PROCESSING' ? 'bg-warning-start/15 text-warning-start border border-warning-start/30 animate-pulse' :
                                                    'bg-danger-start/15 text-danger-start border border-danger-start/30'
                                                }`}>
                                                    {item.status === 'READY' ? 'Transkriptuar' : item.status === 'PROCESSING' ? 'Duke transkriptuar...' : 'Dështoi'}
                                                </span>
                                                <span className="text-[10px] text-text-muted font-mono">
                                                    {new Date(item.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={() => handleDelete(item.id)}
                                        className="p-2 text-text-muted hover:text-danger-start hover:bg-hover rounded-xl transition-colors"
                                        title="Fshi provën"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>

                                <div className="w-full bg-canvas p-2.5 rounded-xl border border-main">
                                    <audio 
                                        controls 
                                        className="w-full h-8"
                                        src={streamUrl}
                                    />
                                </div>

                                {item.status === 'READY' && (
                                    <button
                                        type="button"
                                        onClick={() => setSelectedTranscript(item)}
                                        className="w-full py-2.5 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-primary-start flex items-center justify-center gap-2 transition-colors"
                                    >
                                        <FileText size={15} /> Shiko Transkriptin e Plotë
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <AnimatePresence>
                {selectedTranscript && (
                    <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-4 sm:p-6 lg:p-8">
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95, y: 15 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 15 }}
                            className="glass-panel w-full max-w-4xl h-[85vh] max-h-[850px] p-6 sm:p-8 md:p-10 rounded-3xl shadow-2xl border border-main bg-canvas flex flex-col"
                        >
                            <div className="flex justify-between items-center mb-6 border-b border-main pb-5 shrink-0">
                                <div className="flex items-center gap-4 min-w-0">
                                    <div className="w-12 h-12 bg-primary-start/10 text-primary-start rounded-2xl flex items-center justify-center border border-primary-start/20 shrink-0">
                                        <FileText size={24} />
                                    </div>
                                    <div className="min-w-0">
                                        <h3 className="text-lg sm:text-xl font-black text-text-primary uppercase tracking-tight truncate">Transkripti AI</h3>
                                        <p className="text-xs text-text-muted font-medium truncate mt-0.5">{selectedTranscript.file_name}</p>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedTranscript(null)} className="p-2.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors">
                                    ✕
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto custom-finance-scroll p-6 sm:p-8 bg-surface/55 rounded-2xl border border-main text-text-primary text-base sm:text-lg leading-relaxed whitespace-pre-wrap font-medium shadow-inner">
                                {selectedTranscript.transcript || "Nuk u gjend transkript."}
                            </div>

                            <div className="flex flex-wrap items-center justify-between pt-6 mt-6 border-t border-main gap-4 shrink-0">
                                <div className="flex items-center gap-3">
                                    <button 
                                        type="button"
                                        onClick={() => handleDownloadTranscript(selectedTranscript)}
                                        className="h-11 px-4 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2 transition-all hover-lift shadow-sm"
                                        title="Shkarko si TXT"
                                    >
                                        <Download size={16} /> Shkarko TXT
                                    </button>

                                    <button 
                                        type="button"
                                        onClick={async () => {
                                            try {
                                                await apiService.downloadForensicReport(caseId, {
                                                    title: `Transkript Audio: ${selectedTranscript.file_name}`,
                                                    content: selectedTranscript.transcript
                                                });
                                            } catch (err) {
                                                alert("Dështoi shkarkimi i PDF.");
                                            }
                                        }}
                                        className="h-11 px-4 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2 transition-all hover-lift shadow-sm"
                                        title="Shkarko si PDF Zyrtar"
                                    >
                                        <FileText size={16} className="text-primary-start" /> Shkarko PDF
                                    </button>

                                    <button 
                                        type="button"
                                        onClick={() => handleArchiveTranscript(selectedTranscript)}
                                        disabled={isArchiving}
                                        className="h-11 px-4 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-primary-start flex items-center gap-2 transition-all hover-lift shadow-sm disabled:opacity-50"
                                    >
                                        {isArchiving ? <Loader2 size={16} className="animate-spin" /> : archiveSuccess ? <CheckCircle2 size={16} className="text-status-success" /> : <Save size={16} />}
                                        {archiveSuccess ? 'U ruajt!' : 'Ruaj në Arkiv'}
                                    </button>
                                </div>

                                <button 
                                    type="button"
                                    onClick={() => {
                                        navigator.clipboard.writeText(selectedTranscript.transcript);
                                        alert("Transkripti u kopjua në memorien e kompjuterit!");
                                    }}
                                    className="btn-primary h-11 px-8 rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-primary-start/15 hover:scale-[1.02] active:scale-95 transition-all"
                                >
                                    Kopjo Transkriptin
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}