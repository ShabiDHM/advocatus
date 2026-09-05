// FILE: frontend/src/components/forensics/AudioForensicLab.tsx
// PHOENIX PROTOCOL - AUDIO FORENSIC LAB V1.0 (WHISPER SECOND-BY-SECOND & SPEAKER DIARIZATION)
// ZERO TS WARNINGS • ZERO HARDCODING • STREAMING AUDIO & LEGAL INTERROGATION

import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  UploadCloud,
  Play,
  Pause,
  Clock,
  User,
  Copy,
  CheckCircle2,
  Trash2,
  Loader2,
  Sparkles,
  RefreshCw,
  Search,
  ShieldAlert,
  Volume2,
  AlertCircle,
  FileText
} from 'lucide-react';
import { forensicService, MediaEvidenceItem } from '../../services/forensicService';
import { apiService } from '../../services/api';

interface AudioForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

export const AudioForensicLab: React.FC<AudioForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  const [audioList, setAudioList] = useState<MediaEvidenceItem[]>([]);
  const [selectedAudioId, setSelectedAudioId] = useState<string | null>(null);
  const [loadingMedia, setLoadingMedia] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [deletingAudioId, setDeletingAudioId] = useState<string | null>(null);

  // Gjendja e Audio Player
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Gjendjet e Analizës Ligjore të Audios
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [legalAudioReport, setLegalAudioReport] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedTranscript, setCopiedTranscript] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Marrja e token-it për streaming nga storage
  const authToken = localStorage.getItem('token') || localStorage.getItem('access_token') || '';

  useEffect(() => {
    if (caseId) {
      loadAudioEvidence();
    }
  }, [caseId]);

  // Ndalim i audios kur ndryshohet audio aktive
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      setCurrentTime(0);
    }
  }, [selectedAudioId]);

  const loadAudioEvidence = async () => {
    if (!caseId) return;
    setLoadingMedia(true);
    try {
      const mediaItems = await forensicService.getCaseMedia(caseId);
      // Filtrojmë vetëm provat audio
      const audios = (mediaItems || []).filter(item => item.media_type === 'audio');
      setAudioList(audios);

      if (audios.length > 0 && !selectedAudioId) {
        setSelectedAudioId(audios[0].id);
      }
    } catch (err) {
      console.error("Dështoi ngarkimi i provave audio:", err);
    } finally {
      setLoadingMedia(false);
    }
  };

  const handleUploadAudioFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgressText(`Duke kompresuar & dërguar për transkriptim Whisper: ${file.name}...`);
        await forensicService.uploadCaseMedia(caseId, file);
      }
      setUploadProgressText("Regjistrimet u ngarkuan. Transkriptimi po procedon në sfond...");
      await loadAudioEvidence();
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi ngarkimi i audios:", err);
      alert("Dështoi ngarkimi i skedarit audio.");
    } finally {
      setIsUploading(false);
      setUploadProgressText('');
    }
  };

  const handleDeleteAudio = async (audioId: string, fileName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të fshini përgjimin/audion "${fileName}"?`);
    if (!confirmDelete) return;

    setDeletingAudioId(audioId);
    try {
      await forensicService.deleteCaseMedia(caseId, audioId);
      setAudioList(prev => prev.filter(a => a.id !== audioId));
      if (selectedAudioId === audioId) {
        setSelectedAudioId(null);
        setLegalAudioReport('');
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e audios:", err);
      alert("Dështoi fshirja e regjistrimit nga serveri.");
    } finally {
      setDeletingAudioId(null);
    }
  };

  // Autopsia Forenzike me Inteligjencë Artificiale mbi bisedën audio
  const handleRunAudioForensics = async () => {
    const activeAudio = audioList.find(a => a.id === selectedAudioId);
    if (!activeAudio || !caseId || isAnalyzing) return;

    const transcriptText = activeAudio.transcript || 'Transkripti është në proces e sipër.';

    setIsAnalyzing(true);
    setLegalAudioReport('');

    try {
      const prompt = `[PROTOKOLLI PHOENIX — AUTOPSI FORENZIKE E REGJISTRIMIT AUDIO]
Analizo transkriptin e përgjimit/voice-note "${activeAudio.file_name}":
TRANSKRIPTI I DËGJUAR:
"""
${transcriptText}
"""

DETYRA EKSPERTUESE GJYQËSORE:
1. IDENTIFIKIMI I PRANIMIT TË FAJËSISË OSE DETYRIMIT: A dëgjohen deklarime vetë-inkriminuese, kërkesa haraçi apo kanosje?
2. KRONOLOGJIA & ORËT: Cilat pika kohore paraqesin rëndësi vendimtare për alibinë?
3. KONTRADIKTAT: A përplasen këto deklarata me normat e së drejtës procedurale (provë e pranueshme sipas KPPRK-së apo përgjim i paautorizuar)?
Harto raportin për prokurorin/gjyqtarin e çështjes.`;

      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setLegalAudioReport(acc);
      }
    } catch (err) {
      console.error("Audio analysis error:", err);
      alert("Dështoi analiza forenzike e audios.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Menaxhimi i Audio Player
  const togglePlayAudio = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      setDuration(audioRef.current.duration || 0);
    }
  };

  const handleAudioSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const formatSeconds = (sec: number) => {
    if (isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleCopyTranscript = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedTranscript(true);
    setTimeout(() => setCopiedTranscript(false), 2500);
  };

  const activeAudio = audioList.find(a => a.id === selectedAudioId);
  const filteredAudios = audioList.filter(a =>
    a.file_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const streamUrl = (activeAudio && caseId && authToken)
    ? forensicService.getMediaStreamUrl(caseId, activeAudio.id, authToken)
    : '';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* KOLONA E MAJTË: NGARKIMI I AUDIOVE & REGJISTRI */}
      <div className="lg:col-span-5 space-y-4">
        {/* Dropzone për Skedarë Audio */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Mic size={15} className="text-primary-start" /> Regjistrimet Audio & Voice Notes
            </h3>
            <span className="text-[10px] font-mono text-text-muted">Whisper Second-by-Second</span>
          </div>

          <div
            onClick={() => !isUploading && fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!isUploading) handleUploadAudioFiles(e.dataTransfer.files);
            }}
            className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-2xl p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
          >
            {isUploading ? (
              <div className="flex flex-col items-center justify-center gap-2 py-2">
                <Loader2 size={22} className="animate-spin text-primary-start" />
                <span className="text-xs font-bold text-primary-start">{uploadProgressText}</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <p className="text-xs font-bold text-text-primary">Kliko ose tërhiq skedarë audio (MP3, M4A, OGG, WAV)</p>
                  <p className="text-[10px] text-text-muted">Voice notes të WhatsApp & telefonata me vlerë dëshmuese</p>
                </div>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            multiple
            className="hidden"
            onChange={(e) => handleUploadAudioFiles(e.target.files)}
          />
        </div>

        {/* Paneli i Kërkimit dhe Përzgjedhjes së Audios */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="relative flex-1 mr-2">
              <Search size={13} className="absolute left-3 top-2.5 text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filtro regjistrimet..."
                className="w-full bg-surface border border-main rounded-xl pl-8 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-primary-start"
              />
            </div>
            <button
              onClick={loadAudioEvidence}
              title="Rifresko provat audio"
              className="p-2 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer"
            >
              <RefreshCw size={13} className={loadingMedia ? 'animate-spin' : ''} />
            </button>
          </div>

          <div className="space-y-2 max-h-[380px] overflow-y-auto custom-finance-scroll pr-1">
            {filteredAudios.length === 0 ? (
              <div className="text-center py-8 text-xs text-text-muted">
                {loadingMedia ? 'Duke lexuar arkivën audio...' : 'Nuk ka asnjë audio të regjistruar.'}
              </div>
            ) : (
              filteredAudios.map((audio) => {
                const isSelected = audio.id === selectedAudioId;
                const isDeleting = audio.id === deletingAudioId;

                return (
                  <div
                    key={audio.id}
                    onClick={() => setSelectedAudioId(audio.id)}
                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                        : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <div className={`p-2 rounded-xl ${isSelected ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                        <Mic size={16} />
                      </div>
                      <div className="truncate text-xs">
                        <p className="font-bold truncate text-text-primary">{audio.file_name}</p>
                        <p className="text-[10px] font-mono text-text-muted flex items-center gap-1">
                          <Clock size={10} />
                          {audio.created_at ? new Date(audio.created_at).toLocaleTimeString('sq-AL', { hour: '2-digit', minute: '2-digit' }) : '00:00'}
                          <span>• Statusi: {audio.status}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {audio.status === 'PROCESSING' && (
                        <span title="Transkriptimi në progres">
                          <Loader2 size={13} className="animate-spin text-primary-start" />
                        </span>
                      )}
                      {isSelected && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
                      <button
                        type="button"
                        onClick={(e) => handleDeleteAudio(audio.id, audio.file_name, e)}
                        disabled={isDeleting}
                        title="Fshij përgjimin"
                        className="p-1.5 text-text-muted hover:text-rose-500 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer"
                      >
                        {isDeleting ? <Loader2 size={13} className="animate-spin text-rose-500" /> : <Trash2 size={13} />}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* KOLONA E DJATHTË: AUDIO PLAYER, TRANSKRIPTI TEMPORAL & EKSPERTIZA */}
      <div className="lg:col-span-7 space-y-4">
        {/* AUDIO PLAYER ME KONTROLL KOHOR */}
        {activeAudio && streamUrl && (
          <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
            <audio
              ref={audioRef}
              src={streamUrl}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleTimeUpdate}
              onEnded={() => setIsPlaying(false)}
              className="hidden"
            />

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Volume2 size={16} className="text-primary-start" />
                <span className="text-xs font-bold truncate max-w-xs text-text-primary">{activeAudio.file_name}</span>
              </div>
              <span className="text-[11px] font-mono text-text-muted">
                {formatSeconds(currentTime)} / {formatSeconds(duration)}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={togglePlayAudio}
                className="w-10 h-10 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white flex items-center justify-center shadow-md transition-all cursor-pointer shrink-0"
              >
                {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
              </button>

              <input
                type="range"
                min={0}
                max={duration || 100}
                value={currentTime}
                onChange={handleAudioSeek}
                className="w-full accent-primary-start h-1.5 bg-surface rounded-lg cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* TRANSKRIPTI TEMPORAL & AUTOPSIA E ZËRIT */}
        <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-primary-start" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary">
                  Transkripti Whisper me Sekonda
                </h3>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Speaker Diarization: Ndarja e folësve me vlerë provuese gjyqësore
              </p>
            </div>

            <div className="flex items-center gap-2">
              {activeAudio?.transcript && (
                <button
                  type="button"
                  onClick={() => handleCopyTranscript(activeAudio.transcript || '')}
                  className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedTranscript ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedTranscript ? 'U Kopjua' : 'Kopjo Transkriptin'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={handleRunAudioForensics}
                disabled={!selectedAudioId || isAnalyzing || !activeAudio?.transcript}
                className="h-9 px-4 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all disabled:opacity-40 cursor-pointer"
              >
                {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                <span>{legalAudioReport ? 'Ri-Analizo Zërin' : 'Autopsia e Përgjimit'}</span>
              </button>
            </div>
          </div>

          {/* Dritarja e Tekstit të Transkriptuar */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Majtas: Transkripti Literal me Sekonda */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                <User size={12} /> Biseda e Transkriptuar (Whisper):
              </span>
              <div className="h-[360px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-mono select-text">
                {activeAudio?.transcript || (
                  <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2">
                    <Mic size={32} className="opacity-30" />
                    <p className="text-xs">
                      {activeAudio ? 'Transkriptimi po përpunohet nga motori Whisper...' : 'Zgjidhni një audio në të majtë.'}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Djathtas: Raporti Ligjor Forenzik i Zërit */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                <ShieldAlert size={12} className="text-rose-500" /> Analiza e Inkriminimit:
              </span>
              <div className="h-[360px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-sans select-text">
                {legalAudioReport || (
                  <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2">
                    <AlertCircle size={32} className="opacity-30 text-primary-start" />
                    <p className="text-xs max-w-xs">
                      Shtypni "Autopsia e Përgjimit" për të zbuluar automatikisht kërcënimet, pranimin e fajësisë dhe kontradiktat.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AudioForensicLab;