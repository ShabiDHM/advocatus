// FILE: frontend/src/components/forensics/AudioForensicLab.tsx
// PHOENIX PROTOCOL - FORENSIC DEDICATED AUDIO LAB V4.0 (TRUE VERBATIM & COURT-ADMISSIBLE DIARIZATION)
// 100% COMPLETE CODE • ZERO TS WARNINGS • ASSEMBLYAI & CLAUDE SONNET 4.6 • MOBILE & TABLET READY

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
  Volume2,
  FileText,
  Scale,
  AlignLeft,
  ShieldCheck,
  Check
} from 'lucide-react';
import {
  forensicDeskService,
  ForensicMediaItem,
  AudioAnalysisResponse
} from '../../services/forensicDeskService';

interface AudioForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

const FONT_LEVELS = [
  { label: '90%',   base: 13,   line: 1.55 },
  { label: '100%',  base: 15,   line: 1.65 },
  { label: '115%',  base: 17,   line: 1.7 },
  { label: '130%',  base: 19,   line: 1.75 },
  { label: '150%',  base: 21,   line: 1.8 }
];

export const AudioForensicLab: React.FC<AudioForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  const [audioList, setAudioList] = useState<ForensicMediaItem[]>([]);
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

  // Gjendjet e Analizës
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isGettingPureTranscript, setIsGettingPureTranscript] = useState<boolean>(false);
  const [forensicAnalysis, setForensicAnalysis] = useState<AudioAnalysisResponse | null>(null);
  const [pureTranscript, setPureTranscript] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedTranscript, setCopiedTranscript] = useState<boolean>(false);

  const localAudioFilesRef = useRef<Map<string, File>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const authToken = localStorage.getItem('token') || localStorage.getItem('access_token') || '';

  // Kontrolli i zmadhimit të fontit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_audio_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });
  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleIncreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_audio_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleDecreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_audio_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_audio_forensic_font_size', '1'); } catch {}
  };

  useEffect(() => {
    if (caseId) {
      loadAudioEvidence();
    }
  }, [caseId]);

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
      const audios = await forensicDeskService.listForensicAudio(caseId);
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
        setUploadProgressText(`Duke ngarkuar me vulë të kujdestarisë: ${file.name}...`);
        const uploaded = await forensicDeskService.uploadForensicAudio(caseId, file);
        if (uploaded?.id) {
          localAudioFilesRef.current.set(uploaded.id, file);
        }
      }
      setUploadProgressText("Regjistrimet u ngarkuan dhe u vulosën.");
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
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të hiqni audion "${fileName}" nga fashikulli forenzik?`);
    if (!confirmDelete) return;

    setDeletingAudioId(audioId);
    try {
      await forensicDeskService.deleteForensicAudio(caseId, audioId);
      setAudioList(prev => prev.filter(a => a.id !== audioId));
      localAudioFilesRef.current.delete(audioId);
      if (selectedAudioId === audioId) {
        setSelectedAudioId(null);
        setForensicAnalysis(null);
        setPureTranscript('');
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e audios:", err);
      alert("Dështoi fshirja e regjistrimit nga serveri.");
    } finally {
      setDeletingAudioId(null);
    }
  };

  const _ensureAudioFileReady = async (activeAudio: ForensicMediaItem): Promise<File | null> => {
    let targetFile = localAudioFilesRef.current.get(activeAudio.id);
    if (!targetFile) {
      try {
        setUploadProgressText("Duke shkarkuar audio nga serveri...");
        const streamUrl = forensicDeskService.getForensicAudioStreamUrl(caseId, activeAudio.id, authToken);
        const res = await fetch(streamUrl);
        const blob = await res.blob();
        targetFile = new File([blob], activeAudio.file_name, { type: activeAudio.mime_type || 'audio/mpeg' });
      } catch (e) {
        console.error("Nuk mund të lexohej skedari nga storage:", e);
      }
    }
    return targetFile || null;
  };

  // 1. EKSPERTIZA E PLOTË (Diarizimi i Folësve + Analiza Procedurale)
  const handleRunAudioForensics = async () => {
    const activeAudio = audioList.find(a => a.id === selectedAudioId);
    if (!activeAudio || !caseId || isAnalyzing || isGettingPureTranscript) return;

    setIsAnalyzing(true);
    try {
      const targetFile = await _ensureAudioFileReady(activeAudio);
      if (!targetFile) {
        alert("Skedari audio nuk u gjet për procesim.");
        return;
      }
      const result = await forensicDeskService.analyzeAudioLab(
        caseId,
        targetFile,
        `Ekspertizë forenzike mbi incizimin: ${activeAudio.file_name}`
      );
      setForensicAnalysis(result);
      setPureTranscript('');
    } catch (err: any) {
      console.error("Audio analysis error:", err);
      alert(err?.response?.data?.detail || "Dështoi analiza e zërit.");
    } finally {
      setIsAnalyzing(false);
      setUploadProgressText('');
    }
  };

  // 2. VETËM TRANSKRIPTI I PASTËR (Verbatim pa interpretim)
  const handleGetPureTranscript = async () => {
    const activeAudio = audioList.find(a => a.id === selectedAudioId);
    if (!activeAudio || !caseId || isAnalyzing || isGettingPureTranscript) return;

    setIsGettingPureTranscript(true);
    try {
      const targetFile = await _ensureAudioFileReady(activeAudio);
      if (!targetFile) {
        alert("Skedari audio nuk u gjet për procesim.");
        return;
      }
      const rawText = await forensicDeskService.getPureAudioTranscript(caseId, targetFile);
      setPureTranscript(rawText);
      setForensicAnalysis(null);
    } catch (err: any) {
      console.error("Pure Transcript Error:", err);
      alert(err?.response?.data?.detail || "Dështoi zbardhja e transkriptit.");
    } finally {
      setIsGettingPureTranscript(false);
      setUploadProgressText('');
    }
  };

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

  // Klikimi i një kohe në transkript kërcen direkt në atë sekondë të audios
  const handleJumpToTime = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds;
      setCurrentTime(seconds);
      if (!isPlaying) {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const formatSeconds = (sec: number) => {
    if (isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleCopyText = (text: string) => {
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
    ? forensicDeskService.getForensicAudioStreamUrl(caseId, activeAudio.id, authToken)
    : '';

  const showForensicPanel = forensicAnalysis !== null;
  const showPureTranscriptPanel = pureTranscript !== '';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 select-none">
      
      {/* KOLONA E MAJTË: NGARKIMI I AUDIOVE & LISTA */}
      <div className="lg:col-span-5 space-y-4">
        
        {/* Dropzone për Skedarë Audio */}
        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2">
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Mic size={15} className="text-primary-start" /> Regjistrimet Audio Forenzike
            </h3>
            <span className="text-[10px] font-mono text-primary-start font-bold">AssemblyAI Engine</span>
          </div>

          <div
            onClick={() => !isUploading && fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!isUploading) handleUploadAudioFiles(e.dataTransfer.files);
            }}
            className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-xl sm:rounded-2xl p-4 sm:p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
          >
            {isUploading ? (
              <div className="flex flex-col items-center justify-center gap-2 py-2">
                <Loader2 size={22} className="animate-spin text-primary-start" />
                <span className="text-xs sm:text-sm font-bold text-primary-start">{uploadProgressText}</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <p className="text-xs sm:text-sm font-bold text-text-primary">Kliko ose tërhiq regjistrimin (MP3, WAV, M4A)</p>
                  <p className="text-[10px] text-text-muted mt-0.5">Vulosje e menjëhershme SHA-256 për vlefshmëri gjyqësore</p>
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

        {/* Lista e Regjistrimeve */}
        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="relative flex-1">
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
              title="Rifresko listën"
              className="p-2 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
            >
              <RefreshCw size={13} className={loadingMedia ? 'animate-spin' : ''} />
            </button>
          </div>

          <div className="space-y-2 max-h-[360px] sm:max-h-[420px] overflow-y-auto custom-finance-scroll pr-1">
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
                    className={`p-3 rounded-xl sm:rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-2.5 ${
                      isSelected
                        ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                        : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate min-w-0 flex-1">
                      <div className={`p-2 rounded-xl shrink-0 ${isSelected ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                        <Mic size={15} />
                      </div>
                      <div className="truncate text-xs">
                        <p className="font-bold truncate text-text-primary">{audio.file_name}</p>
                        <p className="text-[10px] font-mono text-text-muted flex items-center gap-1 mt-0.5">
                          <Clock size={10} />
                          {audio.created_at ? new Date(audio.created_at).toLocaleTimeString('sq-AL', { hour: '2-digit', minute: '2-digit' }) : '00:00'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {isSelected && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
                      <button
                        type="button"
                        onClick={(e) => handleDeleteAudio(audio.id, audio.file_name, e)}
                        disabled={isDeleting}
                        title="Hiq nga lënda"
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

      {/* KOLONA E DJATHTË: AUDIO PLAYER DHE TRANSKRIPTI I DIARIZUAR */}
      <div className="lg:col-span-7 space-y-4">
        
        {/* AUDIO PLAYER PROFESIONAL */}
        {activeAudio && streamUrl && (
          <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
            <audio
              ref={audioRef}
              src={streamUrl}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleTimeUpdate}
              onEnded={() => setIsPlaying(false)}
              className="hidden"
            />

            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 truncate">
                <Volume2 size={16} className="text-primary-start shrink-0" />
                <span className="text-xs font-bold truncate text-text-primary">{activeAudio.file_name}</span>
              </div>
              <span className="text-[11px] font-mono text-text-muted shrink-0">
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

        {/* PANELI KRYESOR I ZBARDHJES DHE EKSPERTIZËS */}
        <div className="glass-panel p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-4">
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-3.5">
            <div>
              <div className="flex items-center gap-2">
                {showForensicPanel ? <ShieldCheck size={17} className="text-primary-start" /> : <AlignLeft size={17} className="text-primary-start" />}
                <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary">
                  {showForensicPanel ? 'Transkripti Zyrtar me Diarizim' : 'Zbardhja Fjalë-për-Fjalë'}
                </h3>
              </div>
              <p className="text-[11px] text-text-muted mt-0.5">
                {showForensicPanel ? 'Ndarja e folësve sipas sekondave dhe analiza procedurale' : 'Zbardhje e plotë tekstuale me vulë provuese.'}
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
              {/* Kontrolli i Fontit */}
              <div className="flex items-center gap-0.5 rounded-xl border border-main bg-surface p-0.5" aria-label="Madhësia e shkrimit">
                <button
                  type="button"
                  onClick={handleDecreaseFont}
                  disabled={fontLevelIndex === 0}
                  className="h-6 w-6 rounded text-xs font-bold text-text-muted hover:bg-hover disabled:opacity-30 cursor-pointer"
                >
                  A−
                </button>
                <button
                  type="button"
                  onClick={handleResetFont}
                  className="min-w-7 text-[10px] font-bold text-text-muted hover:bg-hover rounded text-center cursor-pointer px-1"
                >
                  {activeFont.label}
                </button>
                <button
                  type="button"
                  onClick={handleIncreaseFont}
                  disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                  className="h-6 w-6 rounded text-xs font-bold text-text-muted hover:bg-hover disabled:opacity-30 cursor-pointer"
                >
                  A+
                </button>
              </div>

              {(showForensicPanel || showPureTranscriptPanel) && (
                <button
                  type="button"
                  onClick={() => handleCopyText(showPureTranscriptPanel ? pureTranscript : (forensicAnalysis?.formatted_transcript || ''))}
                  className="h-8 px-2.5 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer"
                >
                  {copiedTranscript ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedTranscript ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}

              {/* BUTONI 1: ZBARDHJA VERBATIM */}
              <button
                type="button"
                onClick={handleGetPureTranscript}
                disabled={!selectedAudioId || isAnalyzing || isGettingPureTranscript}
                className={`h-8 sm:h-9 px-3 rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-xs transition-all disabled:opacity-40 cursor-pointer ${
                  showPureTranscriptPanel ? 'bg-primary-start text-white' : 'bg-surface hover:bg-hover border border-main text-text-primary'
                }`}
              >
                {isGettingPureTranscript ? <Loader2 size={13} className="animate-spin" /> : <AlignLeft size={13} />}
                <span>Zbardhja</span>
              </button>

              {/* BUTONI 2: DIARIZIMI DHE ANALIZA PROCEDURALE */}
              <button
                type="button"
                onClick={handleRunAudioForensics}
                disabled={!selectedAudioId || isAnalyzing || isGettingPureTranscript}
                className="h-8 sm:h-9 px-3.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-xs transition-all disabled:opacity-40 cursor-pointer"
              >
                {isAnalyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                <span>Diarizimi i Folësve</span>
              </button>
            </div>
          </div>

          {/* DRITARJA E PËRMBAJTJES */}
          {showPureTranscriptPanel ? (
            /* PANELI I TRANSKRIPTIT TË PASTËR */
            <div className="space-y-2">
              <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                <FileText size={13} className="text-primary-start" /> Teksti i Plotë Verbatim:
              </span>
              <div 
                className="h-[380px] sm:h-[460px] overflow-y-auto custom-finance-scroll p-4 sm:p-5 bg-surface/50 rounded-2xl border border-main text-text-primary whitespace-pre-wrap font-mono select-text"
                style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
              >
                {pureTranscript}
              </div>
            </div>
          ) : showForensicPanel ? (
            /* PANELI I EKSPERTIZËS (Diarizim + Deklarata Procedurale) */
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              
              {/* Majtas: Segmentet e Folësve me Jump-to-Time */}
              <div className="md:col-span-7 space-y-2">
                <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                  <User size={13} className="text-primary-start" /> Diarizimi sipas Folësve (Kliko kohën për ta dëgjuar):
                </span>
                <div 
                  className="h-[380px] sm:h-[460px] overflow-y-auto custom-finance-scroll p-3 sm:p-4 bg-surface/50 rounded-2xl border border-main select-text space-y-2"
                  style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
                >
                  {forensicAnalysis?.segments && forensicAnalysis.segments.length > 0 ? (
                    forensicAnalysis.segments.map((seg, idx) => (
                      <div 
                        key={idx} 
                        className="p-3 rounded-xl bg-card border border-main/50 space-y-1 hover:border-primary-start/40 transition-colors"
                      >
                        <div className="flex items-center justify-between text-[10px] font-bold">
                          <span className="text-primary-start uppercase tracking-wider flex items-center gap-1">
                            <User size={10} /> {seg.speaker}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleJumpToTime(seg.start)}
                            className="font-mono text-text-muted hover:text-primary-start hover:underline cursor-pointer bg-surface px-1.5 py-0.5 rounded border border-main"
                            title="Kërce në këtë sekondë të audios"
                          >
                            ▶ {seg.timestamp_label}
                          </button>
                        </div>
                        <p className="text-text-primary leading-relaxed pt-0.5">{seg.text}</p>
                      </div>
                    ))
                  ) : (
                    <p className="font-mono text-xs">{forensicAnalysis?.formatted_transcript || 'Ska të dhëna'}</p>
                  )}
                </div>
              </div>

              {/* Djathtas: Raporti Procedural mbi Deklaratat */}
              <div className="md:col-span-5 space-y-2">
                <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                  <Scale size={13} className="text-primary-start" /> Vlerësimi Procedural (KPPRK):
                </span>
                <div 
                  className="h-[380px] sm:h-[460px] overflow-y-auto custom-finance-scroll p-3.5 sm:p-4 bg-surface/50 rounded-2xl border border-main select-text space-y-3 text-xs"
                  style={{ fontSize: `${activeFont.base - 1}px`, lineHeight: activeFont.line }}
                >
                  {/* Përmbledhja */}
                  <div className="p-3 bg-card rounded-xl border border-main space-y-1">
                    <h4 className="font-bold text-text-primary uppercase text-[11px]">
                      Konteksti i Incizimit:
                    </h4>
                    <p className="text-text-muted leading-relaxed">
                      {forensicAnalysis?.forensic_intelligence?.summary}
                    </p>
                  </div>

                  {/* Deklaratat relevante penale */}
                  {forensicAnalysis?.forensic_intelligence?.criminal_elements_detected && forensicAnalysis.forensic_intelligence.criminal_elements_detected.length > 0 && (
                    <div className="p-3 bg-rose-500/10 rounded-xl border border-rose-500/20 space-y-1">
                      <h4 className="font-bold text-rose-500 uppercase text-[11px]">
                        Deklaratat Relevante Penale:
                      </h4>
                      <ul className="list-disc list-inside text-text-primary space-y-0.5 pt-0.5">
                        {forensicAnalysis.forensic_intelligence.criminal_elements_detected.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Pranueshmëria në Gjykatë */}
                  <div className="p-3 bg-card rounded-xl border border-main space-y-1">
                    <h4 className="font-bold text-primary-start uppercase text-[11px]">
                      Pranueshmëria si Provë (KPPRK):
                    </h4>
                    <p className="text-text-muted leading-relaxed">
                      {forensicAnalysis?.forensic_intelligence?.court_admissibility_recommendation}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* PANELI FILLËSTAR BOSH */
            <div className="h-[340px] sm:h-[420px] flex flex-col items-center justify-center text-text-muted text-center gap-2 p-6">
              <div className="w-12 h-12 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                <Mic size={24} />
              </div>
              <div className="space-y-1 max-w-sm">
                <h4 className="font-bold text-text-primary text-xs sm:text-sm">
                  Përzgjidhni një incizim audio për zbardhje
                </h4>
                <p className="text-[11px] text-text-muted">
                  Përdorni <span className="font-bold text-text-primary">"Zbardhja"</span> për tekst verbatim, ose <span className="font-bold text-text-primary">"Diarizimi i Folësve"</span> për ndarjen e zërave me sekonda dhe vlerësim procedural.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AudioForensicLab;