// FILE: src/components/MediaEvidencePanel.tsx
// PHOENIX PROTOCOL - MEDIA EVIDENCE PANEL V5.0 (CLEAN COURTROOM TRANSCRIPT UI • ZERO NOISE HEADERS)

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { apiService, API_V1_URL } from '../services/api';
import { 
    Mic, Upload, Trash2, FileText, 
    Loader2, Download, Save, CheckCircle2,
    Video, Film, Car, Clock, Eye, Copy
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ForensicLogItem {
    timestamp_video: string;
    cctv_clock?: string;
    event_type: string;
    visual_evidence: string;
    evidentiary_value: string;
}

interface LicensePlateItem {
    timestamp: string;
    plate_number: string;
    vehicle_description: string;
}

interface MediaItem {
    id: string;
    file_name: string;
    media_type: 'audio' | 'video';
    mime_type?: string;
    status: 'PROCESSING' | 'READY' | 'FAILED';
    transcript: string;
    visual_analysis?: {
        visual_summary?: string;
        detected_license_plates?: LicensePlateItem[];
        video_forensic_log?: ForensicLogItem[];
    };
    created_at: string;
}

interface MediaEvidencePanelProps {
    caseId: string;
    caseTitle?: string;
    t?: any;
}

export default function MediaEvidencePanel({ caseId }: MediaEvidencePanelProps) {
    const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null);
    const [modalTab, setModalTab] = useState<'transcript' | 'visual'>('transcript');
    const [isArchiving, setIsArchiving] = useState(false);
    const [archiveSuccess, setArchiveSuccess] = useState(false);
    const [copied, setCopied] = useState(false);
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
        }, 4000);
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

            setUploadProgress(40);
            await apiService.axiosInstance.post(`/cases/${caseId}/media/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setUploadProgress(100);
            await loadMedia();
        } catch (err: any) {
            alert(err.response?.data?.detail || "Dështoi ngarkimi i skedarit media.");
        } finally {
            setIsUploading(false);
            setUploadProgress(0);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDelete = async (mediaId: string) => {
        if (!window.confirm("A jeni të sigurt që dëshironi ta fshini këtë provë audio/video?")) return;
        try {
            await apiService.axiosInstance.delete(`/cases/${caseId}/media/${mediaId}`);
            setMediaItems(prev => prev.filter(m => m.id !== mediaId));
            if (selectedMedia?.id === mediaId) setSelectedMedia(null);
        } catch (err) {
            alert("Dështoi fshirja e provës.");
        }
    };

    const handleDownloadTranscript = (item: MediaItem) => {
        const element = document.createElement("a");
        let content = `TRANSKRIPTI ZYRTAR I PROVËS: ${item.file_name}\n\n${item.transcript}\n`;
        const file = new Blob([content], { type: 'text/plain;charset=utf-8' });
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
                `Transkript Zyrtar: ${item.file_name}`, 
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
        <div className="space-y-4 font-sans">
            {/* HEADER ME BUTON PËR AUDIO DHE VIDEO */}
            <div className="flex items-center justify-between gap-3 border-b border-main pb-3">
                <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 bg-primary-start/10 text-primary-start rounded-lg flex items-center justify-center border border-primary-start/20 shrink-0">
                        <Film size={16} />
                    </div>
                    <div className="min-w-0">
                        <h2 className="text-xs font-black text-text-primary uppercase tracking-wider truncate">Provat Audio & Video</h2>
                        <p className="text-[10px] text-text-muted font-medium truncate">Transkriptim me Sekonda</p>
                    </div>
                </div>

                <div className="shrink-0">
                    <input 
                        type="file" 
                        ref={fileInputRef} 
                        onChange={handleFileUpload} 
                        accept="audio/*,video/*,.mp3,.wav,.m4a,.ogg,.aac,.mp4,.mov,.avi,.mkv,.webm" 
                        className="hidden" 
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        className="h-8 px-3 rounded-lg bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-sm transition-all whitespace-nowrap focus:outline-none disabled:opacity-50 cursor-pointer"
                    >
                        {isUploading ? (
                            <Loader2 size={13} className="animate-spin text-white shrink-0" />
                        ) : (
                            <Upload size={13} className="text-white shrink-0" />
                        )}
                        <span className="text-white font-bold whitespace-nowrap">
                            {isUploading ? `${uploadProgress}%` : 'Ngarko Audio / Video'}
                        </span>
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div className="flex justify-center py-8"><Loader2 className="animate-spin h-6 w-6 text-primary-start" /></div>
            ) : mediaItems.length === 0 ? (
                <div className="text-center py-10 border border-dashed border-main rounded-2xl p-4 bg-surface/30">
                    <Film size={32} className="mx-auto mb-2 text-text-muted animate-pulse" />
                    <p className="text-text-primary text-xs font-bold">Nuk ka ende prova audio apo video në këtë lëndë.</p>
                    <p className="text-[11px] text-text-muted mt-0.5">Mbështet MP3, WAV, M4A, MP4, MOV, AVI.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-3">
                    {mediaItems.map(item => {
                        const streamUrl = `${API_V1_URL}/cases/${caseId}/media/${item.id}/stream${authToken ? `?token=${authToken}` : ''}`;
                        const isVideo = item.media_type === 'video' || /\.(mp4|mov|avi|mkv|webm)$/i.test(item.file_name);

                        return (
                            <div key={item.id} className="p-4 rounded-xl border border-main bg-surface flex flex-col justify-between gap-3 shadow-sm">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex items-center gap-2.5 min-w-0">
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                                            isVideo 
                                                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' 
                                                : 'bg-primary-start/10 text-primary-start border-primary-start/20'
                                        }`}>
                                            {isVideo ? <Video size={16} /> : <Mic size={16} />}
                                        </div>
                                        <div className="min-w-0">
                                            <h4 className="text-xs font-bold text-text-primary truncate">{item.file_name}</h4>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-md ${
                                                    item.status === 'READY' ? 'bg-status-success/15 text-status-success border border-status-success/30' :
                                                    item.status === 'PROCESSING' ? 'bg-warning-start/15 text-warning-start border border-warning-start/30 animate-pulse' :
                                                    'bg-danger-start/15 text-danger-start border border-danger-start/30'
                                                }`}>
                                                    {item.status === 'READY' ? (isVideo ? 'Video e Analizuar' : 'Transkriptuar') : item.status === 'PROCESSING' ? 'Duke transkriptuar...' : 'Dështoi'}
                                                </span>
                                                <span className="text-[9px] text-text-muted font-mono">
                                                    {new Date(item.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={() => handleDelete(item.id)}
                                        className="p-1.5 text-text-muted hover:text-danger-start hover:bg-hover rounded-lg transition-colors"
                                        title="Fshi provën"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>

                                <div className="w-full bg-canvas p-2 rounded-lg border border-main">
                                    {isVideo ? (
                                        <video 
                                            controls 
                                            className="w-full h-44 rounded-lg bg-black object-contain"
                                            src={streamUrl}
                                        />
                                    ) : (
                                        <audio 
                                            controls 
                                            className="w-full h-7"
                                            src={streamUrl}
                                        />
                                    )}
                                </div>

                                {item.status === 'READY' && (
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setSelectedMedia(item);
                                            setModalTab(isVideo && item.visual_analysis?.video_forensic_log?.length ? 'visual' : 'transcript');
                                        }}
                                        className="w-full py-2 bg-canvas hover:bg-hover border border-main rounded-lg text-xs font-bold uppercase tracking-wider text-primary-start flex items-center justify-center gap-1.5 transition-colors"
                                    >
                                        <FileText size={14} /> Shiko Transkriptin me Sekonda
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* MODAL I TRANSKRIPTIT TË PASTËR ME SEKONDA */}
            <AnimatePresence>
                {selectedMedia && (
                    <div className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-[200] p-4 sm:p-6 lg:p-8">
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.96, y: 12 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.96, y: 12 }}
                            className="glass-panel w-full max-w-4xl h-[88vh] max-h-[850px] p-6 sm:p-8 rounded-3xl shadow-2xl border border-main bg-canvas flex flex-col"
                        >
                            {/* Modal Header */}
                            <div className="flex justify-between items-center mb-4 border-b border-main pb-4 shrink-0">
                                <div className="flex items-center gap-3.5 min-w-0">
                                    <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20 shrink-0">
                                        <FileText size={20} />
                                    </div>
                                    <div className="min-w-0">
                                        <h3 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">
                                            Transkripti Zyrtar i Provës
                                        </h3>
                                        <p className="text-xs text-text-muted font-medium truncate mt-0.5">{selectedMedia.file_name}</p>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedMedia(null)} className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors">
                                    ✕
                                </button>
                            </div>

                            {/* Tab Switcher nëse ka të dhëna vizuale videoje */}
                            {selectedMedia.visual_analysis?.video_forensic_log?.length ? (
                                <div className="flex gap-2 mb-3 shrink-0">
                                    <button
                                        type="button"
                                        onClick={() => setModalTab('transcript')}
                                        className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase transition-all flex items-center gap-1.5 ${
                                            modalTab === 'transcript'
                                                ? 'bg-primary-start text-white shadow-sm'
                                                : 'bg-surface border border-main text-text-muted hover:text-text-primary'
                                        }`}
                                    >
                                        <Mic size={13} /> Transkripti i Zërit me Sekonda
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setModalTab('visual')}
                                        className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase transition-all flex items-center gap-1.5 ${
                                            modalTab === 'visual'
                                                ? 'bg-primary-start text-white shadow-sm'
                                                : 'bg-surface border border-main text-text-muted hover:text-text-primary'
                                        }`}
                                    >
                                        <Eye size={13} /> Ditari Vizual Forenzik ({selectedMedia.visual_analysis.video_forensic_log.length})
                                    </button>
                                </div>
                            ) : null}

                            {/* Modal Body - Transkripti me Tipografi të Pastër Gjyqësore */}
                            <div className="flex-1 overflow-y-auto custom-finance-scroll p-4 sm:p-6 bg-surface/50 rounded-2xl border border-main text-text-primary shadow-inner">
                                {modalTab === 'visual' && selectedMedia.visual_analysis?.video_forensic_log ? (
                                    <div className="space-y-3">
                                        {selectedMedia.visual_analysis.visual_summary && (
                                            <div className="p-3 bg-canvas rounded-xl border border-main text-xs">
                                                <span className="text-[10px] font-black uppercase text-primary-start block mb-1">Përmbledhja Vizuale:</span>
                                                <p className="text-text-secondary font-medium">{selectedMedia.visual_analysis.visual_summary}</p>
                                            </div>
                                        )}

                                        <div className="space-y-2">
                                            {selectedMedia.visual_analysis.video_forensic_log.map((item, idx) => (
                                                <div key={idx} className="p-3 bg-canvas rounded-xl border border-main text-xs space-y-1">
                                                    <div className="flex items-center justify-between font-bold">
                                                        <span className="text-primary-start font-mono">[{item.timestamp_video}]</span>
                                                        <span className="text-[10px] uppercase text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded font-bold">
                                                            {item.event_type}
                                                        </span>
                                                    </div>
                                                    <p className="text-text-primary font-medium">{item.visual_evidence}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-2 text-sm sm:text-base font-normal leading-relaxed">
                                        {selectedMedia.transcript ? (
                                            selectedMedia.transcript.split('\n').filter(Boolean).map((line, idx) => {
                                                const timeMatch = line.match(/^\[(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\]/);
                                                if (timeMatch) {
                                                    const timeStr = timeMatch[0];
                                                    const textStr = line.replace(timeStr, '').trim();
                                                    return (
                                                        <div key={idx} className="p-2.5 bg-canvas/60 rounded-xl border border-main/50 flex items-start gap-3">
                                                            <span className="text-xs font-mono font-bold text-primary-start bg-primary-start/10 px-2 py-1 rounded-md shrink-0 border border-primary-start/20">
                                                                {timeStr}
                                                            </span>
                                                            <p className="text-xs sm:text-sm font-medium text-text-primary pt-0.5 leading-normal">
                                                                {textStr}
                                                            </p>
                                                        </div>
                                                    );
                                                }
                                                return <p key={idx} className="text-xs sm:text-sm text-text-secondary leading-normal">{line}</p>;
                                            })
                                        ) : (
                                            <p className="text-text-muted text-xs">Nuk u gjend transkript audio për këtë skedar.</p>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Modal Footer */}
                            <div className="flex flex-wrap items-center justify-between pt-4 mt-4 border-t border-main gap-3 shrink-0">
                                <div className="flex items-center gap-2">
                                    <button 
                                        type="button"
                                        onClick={() => handleDownloadTranscript(selectedMedia)}
                                        className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-1.5 transition-all shadow-sm"
                                    >
                                        <Download size={14} /> Shkarko TXT
                                    </button>

                                    <button 
                                        type="button"
                                        onClick={() => handleArchiveTranscript(selectedMedia)}
                                        disabled={isArchiving}
                                        className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold uppercase tracking-wider text-primary-start flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                                    >
                                        {isArchiving ? <Loader2 size={14} className="animate-spin" /> : archiveSuccess ? <CheckCircle2 size={14} className="text-status-success" /> : <Save size={14} />}
                                        {archiveSuccess ? 'U ruajt!' : 'Ruaj në Arkiv'}
                                    </button>
                                </div>

                                <button 
                                    type="button"
                                    onClick={() => {
                                        navigator.clipboard.writeText(selectedMedia.transcript);
                                        setCopied(true);
                                        setTimeout(() => setCopied(false), 2500);
                                    }}
                                    className="h-9 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-md transition-all flex items-center gap-1.5"
                                >
                                    <Copy size={13} /> {copied ? 'U Kopjua!' : 'Kopjo Transkriptin'}
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}