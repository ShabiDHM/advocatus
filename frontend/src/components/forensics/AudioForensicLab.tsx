// FILE: frontend/src/components/forensics/AudioForensicLab.tsx
// PHOENIX PROTOCOL - FORENSIC AUDIO LAB V2.0 (ASSEMBLYAI DIARIZATION • STRESS ANALYSIS • CLAUDE SONNET 4.6)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS

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
  FileText,
  Activity,
  Flame,
  Scale
} from 'lucide-react';
import { forensicService, MediaEvidenceItem } from '../../services/forensicService';
import { forensicDeskService, AudioAnalysisResponse } from '../../services/forensicDeskService';

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

  // Gjendjet e Analizës Forenzike (AssemblyAI + Claude Sonnet 4.6)
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [forensicAnalysis, setForensicAnalysis] = useState<AudioAnalysisResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedTranscript, setCopiedTranscript] = useState<boolean>(false);

  // Cache lokal i skedarëve të sapongarkuar për analizë të menjëhershme
  const localAudioFilesRef = useRef<Map<string, File>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const authToken = localStorage.getItem('token') || localStorage.getItem('access_token') || '';

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
      const mediaItems = await forensicService.getCaseMedia(caseId);
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
        setUploadProgressText(`Duke ngarkuar në laboratorin forenzik: ${file.name}...`);
        const uploaded = await forensicService.uploadCaseMedia(caseId, file);
        if (uploaded?.id) {
          localAudioFilesRef.current.set(uploaded.id, file);
        }
      }
      setUploadProgressText("Regjistrimet u ngarkuan. Gati për ekspertizë.");
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
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të fshini audion "${fileName}"?`);
    if (!confirmDelete) return;

    setDeletingAudioId(audioId);
    try {
      await forensicService.deleteCaseMedia(caseId, audioId);
      setAudioList(prev => prev.filter(a => a.id !== audioId));
      localAudioFilesRef.current.delete(audioId);
      if (selectedAudioId === audioId) {
        setSelectedAudioId(null);
        setForensicAnalysis(null);
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e audios:", err);
      alert("Dështoi fshirja e regjistrimit nga serveri.");
    } finally {
      setDeletingAudioId(null);
    }
  };

  // EKSPERTIZA FORENZIKE ME ASSEMBLYAI (DIARIZIM + STRES) DHE CLAUDE SONNET 4.6
  const handleRunAudioForensics = async () => {
    const activeAudio = audioList.find(a => a.id === selectedAudioId);
    if (!activeAudio || !caseId || isAnalyzing) return;

    let targetFile = localAudioFilesRef.current.get(activeAudio.id);

    // Nëse skedari nuk është në cache lokal, e marrim përmes stream URL
    if (!targetFile) {
      try {
        setIsAnalyzing(true);
        setUploadProgressText("Duke shkarkuar audio për laboratorin e AssemblyAI...");
        const streamUrl = forensicService.getMediaStreamUrl(caseId, activeAudio.id, authToken);
        const res = await fetch(streamUrl);
        const blob = await res.blob();
        targetFile = new File([blob], activeAudio.file_name, { type: activeAudio.mime_type || 'audio/mpeg' });
      } catch (e) {
        console.error("Nuk mund të lexohej skedari nga storage:", e);
      }
    }

    if (!targetFile) {
      alert("Skedari audio nuk u gjet për procesim të drejtpërdrejtë. Ju lutem ngarkoni sërish audion.");
      setIsAnalyzing(false);
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await forensicDeskService.analyzeAudioLab(
        caseId,
        targetFile,
        `Ekspertizë mbi incizimin ${activeAudio.file_name}`
      );
      setForensicAnalysis(result);
    } catch (err: any) {
      console.error("Audio analysis error:", err);
      alert(err?.response?.data?.detail || "Dështoi analiza e thellë forenzike me AssemblyAI.");
    } finally {
      setIsAnalyzing(false);
      setUploadProgressText('');
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

  const activeTranscript = forensicAnalysis?.formatted_transcript || activeAudio?.transcript || '';

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
            <span className="text-[10px] font-mono text-primary-start font-bold">AssemblyAI + Sonnet 4.6</span>
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
                  <p className="text-[10px] text-text-muted">Përgjime telefonike, voice notes & biseda dëshmuese</p>
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

      {/* KOLONA E DJATHTË: AUDIO PLAYER, DIARIZIMI DHE EKSPERTIZA E STRESIT */}
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

        {/* TRANSKRIPTI I DIARIZUAR DHE ANALIZA E STRESIT */}
        <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <FileText size={18} className="text-primary-start" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary">
                  Diarizimi & Analiza e Stresit
                </h3>
                {forensicAnalysis?.forensic_intelligence?.threat_level && (
                  <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                    forensicAnalysis.forensic_intelligence.threat_level === 'KRITIKE' || forensicAnalysis.forensic_intelligence.threat_level === 'E LARTË'
                      ? 'bg-rose-500/15 text-rose-500 border border-rose-500/30'
                      : 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                  }`}>
                    Kërcënimi: {forensicAnalysis.forensic_intelligence.threat_level}
                  </span>
                )}
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                AssemblyAI Speaker Diarization + Ekspertizë me Claude Sonnet 4.6
              </p>
            </div>

            <div className="flex items-center gap-2">
              {activeTranscript && (
                <button
                  type="button"
                  onClick={() => handleCopyTranscript(activeTranscript)}
                  className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedTranscript ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedTranscript ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={handleRunAudioForensics}
                disabled={!selectedAudioId || isAnalyzing}
                className="h-9 px-4 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all disabled:opacity-40 cursor-pointer"
              >
                {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                <span>{forensicAnalysis ? 'Ri-Eksperto Zërin' : 'Ekspertiza e Zërit'}</span>
              </button>
            </div>
          </div>

          {/* Dritarja e Tekstit të Diarizuar dhe Raportit */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Majtas: Transkripti me Folës dhe Minuta */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                <User size={12} /> Biseda me Folës (AssemblyAI):
              </span>
              <div className="h-[380px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-mono select-text space-y-2">
                {forensicAnalysis?.segments && forensicAnalysis.segments.length > 0 ? (
                  forensicAnalysis.segments.map((seg, idx) => (
                    <div key={idx} className="p-2 rounded-xl bg-card border border-main/40 space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-text-muted font-bold">
                        <span className="text-primary-start">{seg.speaker}</span>
                        <span>{seg.timestamp_label}</span>
                      </div>
                      <p className="text-xs text-text-primary">{seg.text}</p>
                    </div>
                  ))
                ) : activeTranscript ? (
                  <p>{activeTranscript}</p>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2">
                    <Mic size={32} className="opacity-30" />
                    <p className="text-xs">
                      {activeAudio ? 'Shtypni "Ekspertiza e Zërit" për të nisur Diarizimin.' : 'Zgjidhni një audio në të majtë.'}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Djathtas: Raporti Ligjor i Stresit dhe Kanosjes */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                <ShieldAlert size={12} className="text-rose-500" /> Analiza Kriminalistike (Claude Sonnet 4.6):
              </span>
              <div className="h-[380px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-sans select-text space-y-3">
                {forensicAnalysis?.forensic_intelligence ? (
                  <div className="space-y-3">
                    <div className="p-3 bg-surface rounded-xl border border-main space-y-1">
                      <h4 className="font-bold text-text-primary flex items-center gap-1.5">
                        <Activity size={13} className="text-primary-start" /> Përmbledhja:
                      </h4>
                      <p className="text-text-muted">{forensicAnalysis.forensic_intelligence.summary}</p>
                    </div>

                    {forensicAnalysis.forensic_intelligence.criminal_elements_detected?.length > 0 && (
                      <div className="p-3 bg-rose-500/10 rounded-xl border border-rose-500/20 space-y-1">
                        <h4 className="font-bold text-rose-500 flex items-center gap-1.5">
                          <Flame size={13} /> Elementet Penale të Detektuara:
                        </h4>
                        <ul className="list-disc list-inside text-text-primary">
                          {forensicAnalysis.forensic_intelligence.criminal_elements_detected.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="p-3 bg-surface rounded-xl border border-main space-y-1">
                      <h4 className="font-bold text-text-primary flex items-center gap-1.5">
                        <Scale size={13} className="text-primary-start" /> Pranueshmëria në Gjykatë:
                      </h4>
                      <p className="text-text-muted">{forensicAnalysis.forensic_intelligence.court_admissibility_recommendation}</p>
                    </div>

                    {forensicAnalysis.stress_flags?.length > 0 && (
                      <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 space-y-1">
                        <h4 className="font-bold text-amber-500 text-[11px] uppercase">
                          Momente me Tension/Stres të Lartë ({forensicAnalysis.stress_flags.length}):
                        </h4>
                        <div className="space-y-1 mt-1">
                          {forensicAnalysis.stress_flags.map((flag, idx) => (
                            <p key={idx} className="text-[11px] text-text-primary">
                              <span className="font-bold font-mono">[{formatSeconds(flag.start)}]:</span> "{flag.text}"
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2">
                    <AlertCircle size={32} className="opacity-30 text-primary-start" />
                    <p className="text-xs max-w-xs">
                      Shtypni "Ekspertiza e Zërit" për të nxjerrë nivelin e kanosjes, neneve penale dhe stresit nga Claude Sonnet 4.6.
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