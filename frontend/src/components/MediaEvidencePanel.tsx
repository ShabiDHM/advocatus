// FILE: frontend/src/components/MediaEvidencePanel.tsx
// PHOENIX PROTOCOL - MEDIA PANEL V17.0 (NATIVE BROWSER PROMPT)
// V17.0: Hequr modal i lejes — kthehemi në thirrje direkte të getUserMedia().
//        Shfletuesi shfaq popup-in e vetëm natyror (Allow/Block).
//        Alert i thjeshtë nëse leja u refuzua më parë.
// V15.0: Shfaqja e folësve (FOLËSI_A/B/C) me badge me ngjyra + backward compat.

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { apiService, API_V1_URL } from '../services/api';
import { 
    Mic, Upload, Trash2, FileText, 
    Loader2, Download, Save, CheckCircle2,
    Video, Film, Copy, Square, Activity, X, Users
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

interface MediaSegment {
    speaker: string;
    start: number;
    end: number;
    timestamp_label: string;
    text: string;
}

interface MediaItem {
    id: string;
    file_name: string;
    media_type: 'audio' | 'video';
    mime_type?: string;
    status: 'PROCESSING' | 'READY' | 'FAILED';
    transcript: string;
    segments?: MediaSegment[];
    created_at: string;
}

interface MediaEvidencePanelProps {
    caseId: string;
    caseTitle?: string;
    t?: any;
}

// ═══════════════════════════════════════════════════════════════════════
// SPEAKER COLOR MAPPING
// ═══════════════════════════════════════════════════════════════════════
const SPEAKER_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
    'FOLËSI_A': {
        bg: 'bg-blue-500/5',
        border: 'border-blue-500/20',
        text: 'text-blue-600 dark:text-blue-400',
        badge: 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400',
    },
    'FOLËSI_B': {
        bg: 'bg-emerald-500/5',
        border: 'border-emerald-500/20',
        text: 'text-emerald-600 dark:text-emerald-400',
        badge: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400',
    },
    'FOLËSI_C': {
        bg: 'bg-purple-500/5',
        border: 'border-purple-500/20',
        text: 'text-purple-600 dark:text-purple-400',
        badge: 'bg-purple-500/10 border-purple-500/30 text-purple-600 dark:text-purple-400',
    },
    'FOLËSI_D': {
        bg: 'bg-amber-500/5',
        border: 'border-amber-500/20',
        text: 'text-amber-600 dark:text-amber-400',
        badge: 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400',
    },
};

const DEFAULT_SPEAKER_COLOR = {
    bg: 'bg-surface',
    border: 'border-main',
    text: 'text-text-secondary',
    badge: 'bg-surface border-main text-text-secondary',
};

const getSpeakerColor = (speaker: string) => SPEAKER_COLORS[speaker] || DEFAULT_SPEAKER_COLOR;

const formatSpeakerLabel = (speaker: string): string => {
    return speaker
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase());
};

export default function MediaEvidencePanel({ caseId }: MediaEvidencePanelProps) {
    const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null);
    const [isArchiving, setIsArchiving] = useState(false);
    const [archiveSuccess, setArchiveSuccess] = useState(false);
    const [copied, setCopied] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Voice recorder state
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<number | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const loadMedia = useCallback(async () => {
        try {
            const res = await apiService.axiosInstance.get(`/cases/${caseId}/media`);
            setMediaItems(res.data || []);
        } catch (err) {
            console.error("Failed to load media items:", err);
        } finally {
            setIsLoading(false);
        }
    }, [caseId]);

    const isProcessing = useMemo(() => mediaItems.some(item => item.status === 'PROCESSING'), [mediaItems]);

    useEffect(() => {
        loadMedia();
    }, [loadMedia]);

    useEffect(() => {
        if (!isProcessing) return;
        const interval = setInterval(() => {
            loadMedia();
        }, 3000);
        return () => clearInterval(interval);
    }, [isProcessing, loadMedia]);

    useEffect(() => {
        return () => {
            if (timerRef.current !== null) clearInterval(timerRef.current);
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                mediaRecorderRef.current.stop();
            }
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    const uploadFileToServer = async (file: File) => {
        setIsUploading(true);
        setUploadProgress(20);
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
            alert(err.response?.data?.detail || "Dështoi ngarkimi i skedarit.");
        } finally {
            setIsUploading(false);
            setUploadProgress(0);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (file.size > MAX_FILE_SIZE_BYTES) {
            alert(`Skedari është shumë i madh (${(file.size / (1024 * 1024)).toFixed(1)} MB). Madhësia maksimale e lejuar është ${MAX_FILE_SIZE_MB} MB.`);
            if (fileInputRef.current) fileInputRef.current.value = '';
            return;
        }

        const validExtensions = /\.(mp3|wav|m4a|ogg|aac|mp4|mov|avi|mkv|webm)$/i;
        if (!validExtensions.test(file.name)) {
            alert("Formati i skedarit nuk mbështetet. Ju lutem përdorni MP3, WAV, M4A, AAC, MP4, MOV, ose AVI.");
            if (fileInputRef.current) fileInputRef.current.value = '';
            return;
        }

        await uploadFileToServer(file);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const pickSupportedMimeType = (): string => {
        const candidates = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/ogg',
            'audio/mp4;codecs=mp4a.40.2',
            'audio/mp4',
            'audio/mpeg'
        ];
        for (const m of candidates) {
            try {
                if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(m)) {
                    return m;
                }
            } catch { /* ignore */ }
        }
        return '';
    };

    // ═══════════════════════════════════════════════════════════════════
    // V17.0: Thirrje direkte e getUserMedia() — browser shfaq popup-in natyror
    // ═══════════════════════════════════════════════════════════════════
    const startRecording = async () => {
        try {
            const audioConstraints: MediaTrackConstraints = {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: true,
                sampleRate: 48000,
                channelCount: 1
            };

            // Shfletuesi shfaq popup-in natyror "Allow / Block" nëse është hera e parë
            const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
            streamRef.current = stream;

            const chosenMime = pickSupportedMimeType();

            const options: MediaRecorderOptions = {
                audioBitsPerSecond: 128000
            };
            if (chosenMime) {
                options.mimeType = chosenMime;
            }

            const mediaRecorder = new MediaRecorder(stream, options);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                await new Promise(resolve => setTimeout(resolve, 200));

                if (streamRef.current) {
                    streamRef.current.getTracks().forEach(track => track.stop());
                    streamRef.current = null;
                }

                const blobType = mediaRecorder.mimeType || chosenMime || 'audio/webm';
                const audioBlob = new Blob(audioChunksRef.current, { type: blobType });

                console.log(`🎙️ [Recorder] Blob: size=${audioBlob.size} bytes, type=${blobType}, chunks=${audioChunksRef.current.length}`);

                if (audioBlob.size > 0) {
                    let ext = 'webm';
                    if (blobType.includes('mp4') || blobType.includes('m4a')) ext = 'm4a';
                    else if (blobType.includes('ogg')) ext = 'ogg';
                    else if (blobType.includes('mpeg') || blobType.includes('mp3')) ext = 'mp3';

                    const fileName = `Deshmia_Zanore_${new Date().toISOString().replace(/[:.]/g, '-')}.${ext}`;
                    const file = new File([audioBlob], fileName, { type: blobType });
                    await uploadFileToServer(file);
                } else {
                    alert("Regjistrimi dështoi — skedari është bosh. Provoni përsëri.");
                }
            };

            mediaRecorder.start(1000);
            setIsRecording(true);
            setRecordingTime(0);

            timerRef.current = window.setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (err: any) {
            console.error("Microphone access error:", err);
            const errName = err?.name || '';

            if (errName === 'NotAllowedError' || errName === 'PermissionDeniedError') {
                alert(
                    "Qasja në mikrofon u refuzua.\n\n" +
                    "Për ta riaktivizuar:\n" +
                    "1. Kliko ikonën 🔒 në shiritin e URL-së\n" +
                    "2. Zgjidh \"Site settings\" / \"Cilësimet e faqes\"\n" +
                    "3. Gjej \"Microphone\" → ndryshoje në \"Allow\"\n" +
                    "4. Rifresko faqen"
                );
            } else if (errName === 'NotFoundError' || errName === 'DevicesNotFoundError') {
                alert("Nuk u gjet asnjë mikrofon në pajisjen tuaj.");
            } else if (errName === 'NotReadableError' || errName === 'TrackStartError') {
                alert("Mikrofoni është duke u përdorur nga një aplikacion tjetër. Mbyllni aplikacionet e tjera dhe provoni përsëri.");
            } else {
                alert(`Dështoi regjistrimi: ${err?.message || 'Gabim i panjohur'}`);
            }
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            try {
                if (mediaRecorderRef.current.state === 'recording') {
                    mediaRecorderRef.current.requestData();
                }
            } catch { /* ignore */ }
            mediaRecorderRef.current.stop();
        }
        if (timerRef.current !== null) {
            window.clearInterval(timerRef.current);
            timerRef.current = null;
        }
        setIsRecording(false);
        setRecordingTime(0);
    };

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    };

    const handleDelete = async (mediaId: string) => {
        if (!window.confirm("A jeni të sigurt që dëshironi ta fshini këtë provë materiale?")) return;
        try {
            await apiService.axiosInstance.delete(`/cases/${caseId}/media/${mediaId}`);
            setMediaItems(prev => prev.filter(m => m.id !== mediaId));
            if (selectedMedia?.id === mediaId) setSelectedMedia(null);
        } catch (err) {
            alert("Dështoi fshirja.");
        }
    };

    const handleDownloadTranscript = (item: MediaItem) => {
        const element = document.createElement("a");
        const content = `PROVA MATERIALE AUDIO/VIDEO: ${item.file_name}\nSTATUSI: Transkript Zyrtar Verbatim (Fjalë për Fjalë)\nDATA: ${new Date(item.created_at).toLocaleString()}\n\n----------------------------------------\n\n${item.transcript}\n`;
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
            const blob = new Blob([item.transcript], { type: 'text/plain;charset=utf-8' });
            const transcriptFile = new File([blob], `Transkript_${item.file_name.replace(/\.[^/.]+$/, "")}.txt`, { type: 'text/plain' });
            
            await apiService.uploadArchiveItem(
                transcriptFile,
                `Transkript: ${item.file_name}`,
                'media_transcript',
                caseId
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

    const uniqueSpeakers = useMemo(() => {
        if (!selectedMedia?.segments || selectedMedia.segments.length === 0) return [];
        const set = new Set<string>();
        selectedMedia.segments.forEach(s => s.speaker && set.add(s.speaker));
        return Array.from(set).sort();
    }, [selectedMedia]);

    return (
        <div className="space-y-4 font-sans">
            {/* KOKA E PANELIT DHE BUTONAT */}
            <div className="flex items-center justify-between gap-3 border-b border-main pb-3">
                <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 sm:w-9 sm:h-9 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20 shrink-0">
                        <Mic size={16} className="sm:w-[18px] sm:h-[18px]" />
                    </div>
                    <div className="min-w-0">
                        <h2 className="text-[11px] sm:text-xs font-black text-text-primary uppercase tracking-wider truncate">Provat Audio/Video</h2>
                        <p className="text-[9px] sm:text-[10px] text-text-muted font-medium truncate">Zbardhje Zëri & Regjistrim</p>
                    </div>
                </div>

                <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
                    {isRecording ? (
                        <button
                            type="button"
                            onClick={stopRecording}
                            className="h-8 sm:h-9 w-auto px-3 rounded-lg sm:rounded-xl bg-rose-500 hover:bg-rose-600 text-white font-bold text-[11px] uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-md shadow-rose-500/20 transition-all focus:outline-none cursor-pointer animate-pulse"
                        >
                            <Square size={12} className="fill-current shrink-0" /> 
                            <span className="whitespace-nowrap">{formatTime(recordingTime)} - Ndalo</span>
                            <Activity size={14} className="ml-0.5 shrink-0 hidden sm:inline" />
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={startRecording}
                            disabled={isUploading}
                            className="h-8 w-8 sm:h-9 sm:w-auto sm:px-3 rounded-lg sm:rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 font-bold text-[11px] uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all focus:outline-none cursor-pointer disabled:opacity-50 shrink-0"
                            title="Regjistro Zërin"
                        >
                            <Mic size={15} className="shrink-0" />
                            <span className="hidden sm:inline whitespace-nowrap">Regjistro Zërin</span>
                        </button>
                    )}

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
                        disabled={isUploading || isRecording}
                        className="h-8 w-8 sm:h-9 sm:w-auto sm:px-3 rounded-lg sm:rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] uppercase tracking-wider flex items-center justify-center gap-1.5 shadow-sm transition-all focus:outline-none disabled:opacity-50 cursor-pointer shrink-0"
                        title="Ngarko Audio / Video"
                    >
                        {isUploading ? (
                            <Loader2 size={14} className="animate-spin text-white shrink-0" />
                        ) : (
                            <Upload size={14} className="text-white shrink-0" />
                        )}
                        <span className="hidden sm:inline whitespace-nowrap text-white font-bold">
                            {isUploading ? `${uploadProgress}%` : 'Ngarko Skedar'}
                        </span>
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div className="flex justify-center py-8"><Loader2 className="animate-spin h-6 w-6 text-primary-start" /></div>
            ) : mediaItems.length === 0 ? (
                <div className="text-center py-10 border border-dashed border-main rounded-2xl p-4 bg-surface/30">
                    <div className="flex justify-center gap-3 mb-3">
                        <Mic size={32} className="text-text-muted opacity-70" />
                        <Film size={32} className="text-text-muted opacity-70" />
                    </div>
                    <p className="text-text-primary text-xs font-bold">Nuk ka ende prova audio apo video.</p>
                    <p className="text-[11px] text-text-muted mt-1 font-medium max-w-sm mx-auto">
                        Ngarkoni një skedar nga pajisja juaj ose shtypni butonin me mikrofon për të dhënë një dëshmi zanore drejtpërdrejt.
                    </p>
                    <p className="text-[10px] text-primary-start mt-2 font-bold bg-primary-start/10 px-2 py-1 rounded-md inline-block">Limiti maksimal: {MAX_FILE_SIZE_MB} MB</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-3">
                    {mediaItems.map(item => {
                        const streamUrl = `${API_V1_URL}/cases/${caseId}/media/${item.id}/stream${authToken ? `?token=${authToken}` : ''}`;
                        const isVideo = item.media_type === 'video' || /\.(mp4|mov|avi|mkv)$/i.test(item.file_name);
                        const speakerCount = item.segments?.length
                            ? new Set(item.segments.map(s => s.speaker)).size
                            : 0;

                        return (
                            <div key={item.id} className="p-4 rounded-xl border border-main bg-card flex flex-col justify-between gap-3 shadow-sm">
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
                                            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                                                <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-md ${
                                                    item.status === 'READY' ? 'bg-status-success/15 text-status-success border border-status-success/30' :
                                                    item.status === 'PROCESSING' ? 'bg-warning-start/15 text-warning-start border border-warning-start/30 animate-pulse' :
                                                    'bg-danger-start/15 text-danger-start border border-danger-start/30'
                                                }`}>
                                                    {item.status === 'READY' ? 'Transkriptuar' : item.status === 'PROCESSING' ? 'Duke transkriptuar...' : 'Dështoi'}
                                                </span>
                                                {speakerCount > 0 && (
                                                    <span className="text-[9px] font-bold text-primary-start bg-primary-start/10 border border-primary-start/20 px-2 py-0.5 rounded-md inline-flex items-center gap-1">
                                                        <Users size={9} />
                                                        {speakerCount} {speakerCount === 1 ? 'folës' : 'folës'}
                                                    </span>
                                                )}
                                                <span className="text-[9px] text-text-muted font-mono">
                                                    {new Date(item.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={() => handleDelete(item.id)}
                                        className="p-1.5 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-lg transition-colors shrink-0"
                                        title="Fshij"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>

                                <div className="w-full bg-surface/50 p-2 rounded-lg border border-main">
                                    {isVideo ? (
                                        <video 
                                            controls 
                                            className="w-full h-44 rounded-lg bg-black object-contain"
                                            src={streamUrl}
                                        />
                                    ) : (
                                        <audio 
                                            controls 
                                            className="w-full h-8"
                                            src={streamUrl}
                                        />
                                    )}
                                </div>

                                {item.status === 'READY' && (
                                    <button
                                        type="button"
                                        onClick={() => setSelectedMedia(item)}
                                        className="w-full py-2 bg-surface hover:bg-hover border border-main rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider text-primary-start flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                                    >
                                        <FileText size={13} /> Shiko Transkriptin
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* MODAL - TRANSKRIPTI VERBATIM */}
            {selectedMedia && createPortal(
                <AnimatePresence>
                    <div
                        className="fixed inset-0 bg-black/85 flex items-center justify-center p-3 sm:p-6 lg:p-8"
                        style={{ zIndex: 2147483647 }}
                        onClick={() => setSelectedMedia(null)}
                    >
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.96, y: 12 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.96, y: 12 }}
                            className="w-full max-w-4xl h-[88vh] sm:h-[85vh] max-h-[800px] p-4 sm:p-6 lg:p-8 rounded-2xl sm:rounded-3xl shadow-2xl border border-main flex flex-col bg-card"
                            style={{ backgroundColor: 'var(--bg-card)' }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Modal Header */}
                            <div className="flex justify-between items-center mb-4 border-b border-main pb-4 shrink-0">
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className="w-9 h-9 sm:w-10 sm:h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20 shrink-0">
                                        <FileText size={18} />
                                    </div>
                                    <div className="min-w-0">
                                        <h3 className="text-sm sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">
                                            Transkripti Zyrtar Verbatim
                                        </h3>
                                        <p className="text-[11px] sm:text-xs text-text-muted font-medium truncate mt-0.5">{selectedMedia.file_name}</p>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedMedia(null)} className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer shrink-0">
                                    <X size={18} />
                                </button>
                            </div>

                            {/* Bar info për folësit */}
                            {uniqueSpeakers.length > 0 && (
                                <div className="flex items-center gap-2 pb-3 shrink-0 overflow-x-auto">
                                    <div className="flex items-center gap-1.5 text-[10px] sm:text-xs font-bold text-text-muted uppercase tracking-wider shrink-0">
                                        <Users size={12} />
                                        Folësit:
                                    </div>
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                        {uniqueSpeakers.map(speaker => {
                                            const color = getSpeakerColor(speaker);
                                            return (
                                                <span
                                                    key={speaker}
                                                    className={`text-[10px] sm:text-xs font-bold px-2 py-1 rounded-lg border ${color.badge}`}
                                                >
                                                    {formatSpeakerLabel(speaker)}
                                                </span>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Modal Body */}
                            <div className="flex-1 overflow-y-auto custom-finance-scroll p-3 sm:p-5 rounded-xl sm:rounded-2xl border border-main text-text-primary shadow-inner bg-canvas">
                                <div className="space-y-2.5 text-sm leading-relaxed">
                                    {selectedMedia.segments && selectedMedia.segments.length > 0 ? (
                                        selectedMedia.segments.map((seg, idx) => {
                                            const color = getSpeakerColor(seg.speaker);
                                            return (
                                                <div
                                                    key={idx}
                                                    className={`p-2.5 sm:p-3 rounded-xl border flex items-start gap-2 sm:gap-3 shadow-xs ${color.bg} ${color.border}`}
                                                >
                                                    <div className="flex flex-col items-start gap-1 shrink-0">
                                                        <span className={`text-[10px] sm:text-xs font-mono font-bold px-1.5 sm:px-2 py-0.5 rounded-md border bg-white/40 dark:bg-black/20 ${color.badge}`}>
                                                            {seg.timestamp_label}
                                                        </span>
                                                        <span className={`text-[9px] sm:text-[10px] font-black uppercase tracking-wider ${color.text}`}>
                                                            {formatSpeakerLabel(seg.speaker)}
                                                        </span>
                                                    </div>
                                                    <p className="text-[11px] sm:text-sm font-medium text-text-primary pt-0.5 leading-normal flex-1">
                                                        {seg.text}
                                                    </p>
                                                </div>
                                            );
                                        })
                                    ) : (
                                        selectedMedia.transcript ? (
                                            selectedMedia.transcript.split('\n').filter(Boolean).map((line, idx) => {
                                                const timeMatch = line.match(/^\[(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})\]/);
                                                if (timeMatch) {
                                                    const timeStr = timeMatch[0];
                                                    const textStr = line.replace(timeStr, '').trim();
                                                    return (
                                                        <div key={idx} className="p-2.5 sm:p-3 bg-card rounded-xl border border-main flex items-start gap-2 sm:gap-3 shadow-xs">
                                                            <span className="text-[10px] sm:text-xs font-mono font-bold text-primary-start bg-primary-start/10 px-1.5 sm:px-2 py-1 rounded-md shrink-0 border border-primary-start/20">
                                                                {timeStr}
                                                            </span>
                                                            <p className="text-[11px] sm:text-sm font-medium text-text-primary pt-0.5 leading-normal">
                                                                {textStr}
                                                            </p>
                                                        </div>
                                                    );
                                                }
                                                return <p key={idx} className="text-[11px] sm:text-sm text-text-secondary leading-normal p-1">{line}</p>;
                                            })
                                        ) : (
                                            <p className="text-text-muted text-xs italic">Nuk u gjend transkript audio për këtë provë.</p>
                                        )
                                    )}
                                </div>
                            </div>

                            {/* Modal Footer */}
                            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between pt-4 mt-4 border-t border-main gap-3 shrink-0">
                                <div className="flex items-center gap-2">
                                    <button 
                                        type="button"
                                        onClick={() => handleDownloadTranscript(selectedMedia)}
                                        className="flex-1 sm:flex-none h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider text-text-primary flex items-center justify-center gap-1.5 transition-all shadow-sm cursor-pointer"
                                    >
                                        <Download size={14} /> <span className="hidden xs:inline">Shkarko TXT</span>
                                    </button>

                                    <button 
                                        type="button"
                                        onClick={() => handleArchiveTranscript(selectedMedia)}
                                        disabled={isArchiving}
                                        className="flex-1 sm:flex-none h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider text-primary-start flex items-center justify-center gap-1.5 transition-all shadow-sm disabled:opacity-50 cursor-pointer"
                                    >
                                        {isArchiving ? <Loader2 size={14} className="animate-spin" /> : archiveSuccess ? <CheckCircle2 size={14} className="text-status-success" /> : <Save size={14} />}
                                        <span className="hidden xs:inline">{archiveSuccess ? 'U ruajt!' : 'Ruaj në Arkiv'}</span>
                                    </button>
                                </div>

                                <button 
                                    type="button"
                                    onClick={() => {
                                        navigator.clipboard.writeText(selectedMedia.transcript);
                                        setCopied(true);
                                        setTimeout(() => setCopied(false), 2500);
                                    }}
                                    className="h-9 px-4 sm:px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[10px] sm:text-xs uppercase tracking-wider shadow-md transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                                >
                                    <Copy size={13} /> {copied ? 'U kopjua!' : 'Kopjo Transkriptin'}
                                </button>
                            </div>
                        </motion.div>
                    </div>
                </AnimatePresence>,
                document.body
            )}
        </div>
    );
}