// FILE: frontend/src/components/forensics/VisualForensicLab.tsx
// PHOENIX PROTOCOL - FORENSIC DEDICATED VISUAL & CCTV LAB V4.0 (MOBILE READY & STORAGE SAFE)
// 100% COMPLETE CODE • ZERO CLIENT INTERFERENCE • KEYFRAMES & CLAUDE SONNET 4.6

import React, { useState, useEffect, useRef } from 'react';
import {
  Video,
  UploadCloud,
  Play,
  Pause,
  Clock,
  MapPin,
  Camera,
  CheckCircle2,
  Trash2,
  Loader2,
  Sparkles,
  RefreshCw,
  Search,
  ShieldAlert,
  Eye,
  Copy,
  AlertTriangle,
  ExternalLink,
  Tag,
  Crosshair,
  FileCheck,
  Film,
  HardDrive
} from 'lucide-react';
import {
  forensicDeskService,
  ForensicMediaItem,
  VisualAnalysisResponse,
  CCTVVideoAnalysisResponse
} from '../../services/forensicDeskService';

interface VisualForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

const MAX_FILE_SIZE_MB = 50; // Mbrojtja e Backblaze B2 Free Tier
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

const FONT_LEVELS = [
  { label: '90%',   base: 13,   line: 1.55 },
  { label: '100%',  base: 15,   line: 1.65 },
  { label: '115%',  base: 17,   line: 1.7 },
  { label: '130%',  base: 19,   line: 1.75 },
  { label: '150%',  base: 21,   line: 1.8 }
];

export const VisualForensicLab: React.FC<VisualForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  const [visualList, setVisualList] = useState<ForensicMediaItem[]>([]);
  const [selectedVisualId, setSelectedVisualId] = useState<string | null>(null);
  const [loadingMedia, setLoadingMedia] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [deletingMediaId, setDeletingMediaId] = useState<string | null>(null);

  // Gjendja e Video Player
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Gjendjet e Ekspertizës Forenzike (Foto ose Video CCTV)
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [imageAnalysis, setImageAnalysis] = useState<VisualAnalysisResponse | null>(null);
  const [cctvAnalysis, setCctvAnalysis] = useState<CCTVVideoAnalysisResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedReport, setCopiedReport] = useState<boolean>(false);

  const localFilesRef = useRef<Map<string, File>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const authToken = localStorage.getItem('token') || localStorage.getItem('access_token') || '';

  // Kontrolli i zmadhimit të fontit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_visual_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });
  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleIncreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_visual_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleDecreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_visual_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_visual_forensic_font_size', '1'); } catch {}
  };

  useEffect(() => {
    if (caseId) {
      loadVisualEvidence();
    }
  }, [caseId]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, [selectedVisualId]);

  const loadVisualEvidence = async () => {
    if (!caseId) return;
    setLoadingMedia(true);
    try {
      const visuals = await forensicDeskService.listForensicVisual(caseId);
      setVisualList(visuals);

      if (visuals.length > 0 && !selectedVisualId) {
        setSelectedVisualId(visuals[0].id);
      }
    } catch (err) {
      console.error("Dështoi ngarkimi i provave vizuale:", err);
    } finally {
      setLoadingMedia(false);
    }
  };

  const handleUploadVisualFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    
    // Mbrojtja e Storage: Kontrollojmë madhësinë e të gjithë skedarëve të zgjedhur
    for (let i = 0; i < files.length; i++) {
        if (files[i].size > MAX_FILE_SIZE_BYTES) {
            alert(`Skedari "${files[i].name}" tejkalon kufirin maksimal prej ${MAX_FILE_SIZE_MB}MB për ruajtje efikase. Ju lutem zvogëloni videon ose ndani në pjesë.`);
            return;
        }
    }

    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgressText(`Duke kompresuar & vulosur: ${file.name}...`);
        
        // Dërgimi në server ku ndodh kompresimi FFmpeg në sfond
        const uploaded = await forensicDeskService.uploadForensicVisual(caseId, file);
        if (uploaded?.id) {
          localFilesRef.current.set(uploaded.id, file);
        }
      }
      setUploadProgressText("Provat vizuale u kompresuan dhe u vulosën.");
      await loadVisualEvidence();
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi ngarkimi i provës vizuale:", err);
      alert("Dështoi ngarkimi i skedarit vizual.");
    } finally {
      setIsUploading(false);
      setUploadProgressText('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteVisual = async (mediaId: string, fileName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të hiqni provën vizuale "${fileName}" nga MongoDB dhe Backblaze?`);
    if (!confirmDelete) return;

    setDeletingMediaId(mediaId);
    try {
      await forensicDeskService.deleteForensicVisual(caseId, mediaId);
      setVisualList(prev => prev.filter(v => v.id !== mediaId));
      localFilesRef.current.delete(mediaId);
      if (selectedVisualId === mediaId) {
        setSelectedVisualId(null);
        setImageAnalysis(null);
        setCctvAnalysis(null);
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e videos/fotos:", err);
      alert("Dështoi fshirja e provës nga serveri.");
    } finally {
      setDeletingMediaId(null);
    }
  };

  const activeVisual = visualList.find(v => v.id === selectedVisualId);
  const isVideo = activeVisual?.media_type === 'video' || (activeVisual?.mime_type || '').startsWith('video/');

  const handleRunVisualForensics = async () => {
    if (!activeVisual || !caseId || isAnalyzing) return;

    let targetFile = localFilesRef.current.get(activeVisual.id);

    if (!targetFile) {
      try {
        setIsAnalyzing(true);
        setUploadProgressText("Duke shkarkuar provën nga storage...");
        const streamUrl = forensicDeskService.getForensicVisualStreamUrl(caseId, activeVisual.id, authToken);
        const res = await fetch(streamUrl);
        const blob = await res.blob();
        targetFile = new File([blob], activeVisual.file_name, { type: activeVisual.mime_type || 'image/jpeg' });
      } catch (e) {
        console.error("Nuk mund të lexohej skedari nga storage:", e);
      }
    }

    if (!targetFile) {
      alert("Skedari nuk u gjet për procesim direkt.");
      setIsAnalyzing(false);
      return;
    }

    setIsAnalyzing(true);
    try {
      if (isVideo) {
        const cctvRes = await forensicDeskService.analyzeForensicVideo(
          caseId,
          targetFile,
          `Ekspertizë CCTV mbi regjistrimin ${activeVisual.file_name}`
        );
        setCctvAnalysis(cctvRes);
        setImageAnalysis(null);
      } else {
        const imgRes = await forensicDeskService.analyzeVisualLab(
          caseId,
          targetFile,
          `Ekspertizë forenzike mbi fotografinë ${activeVisual.file_name}`
        );
        setImageAnalysis(imgRes);
        setCctvAnalysis(null);
      }
    } catch (err: any) {
      console.error("Visual analysis error:", err);
      alert(err?.response?.data?.detail || "Dështoi analiza e thellë forenzike.");
    } finally {
      setIsAnalyzing(false);
      setUploadProgressText('');
    }
  };

  const togglePlayVideo = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleCopyReport = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2500);
  };

  const filteredVisuals = visualList.filter(v =>
    v.file_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const streamUrl = (activeVisual && caseId && authToken)
    ? forensicDeskService.getForensicVisualStreamUrl(caseId, activeVisual.id, authToken)
    : '';

  const exifData = imageAnalysis?.exif_metadata;
  const elaData = imageAnalysis?.tamper_analysis;
  const visionData = imageAnalysis?.vision_detection;
  const imageOpinion = imageAnalysis?.forensic_opinion;
  const cctvReport = cctvAnalysis?.forensic_report;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 select-none">
      {/* KOLONA E MAJTË */}
      <div className="lg:col-span-5 space-y-4">
        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2">
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Video size={15} className="text-primary-start" /> Pamjet CCTV & Foto EXIF
            </h3>
            <span className="text-[10px] font-mono text-primary-start font-bold hidden sm:inline">FFmpeg + ELA</span>
          </div>

          <div
            onClick={() => !isUploading && fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!isUploading) handleUploadVisualFiles(e.dataTransfer.files);
            }}
            className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-xl sm:rounded-2xl p-4 sm:p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
          >
            {isUploading ? (
              <div className="flex flex-col items-center justify-center gap-2 py-2">
                <Loader2 size={22} className="animate-spin text-primary-start" />
                <span className="text-[11px] sm:text-xs font-bold text-primary-start">{uploadProgressText}</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <p className="text-xs sm:text-sm font-bold text-text-primary">Kliko ose tërhiq videon/foton</p>
                  <p className="text-[10px] sm:text-[11px] text-text-muted mt-0.5">MP4, MOV, JPG, PNG (Max {MAX_FILE_SIZE_MB}MB)</p>
                </div>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,image/*"
            multiple
            className="hidden"
            onChange={(e) => handleUploadVisualFiles(e.target.files)}
          />

          <div className="flex items-center justify-between pt-1 border-t border-main mt-2">
            <span className="text-[10px] text-text-muted font-bold flex items-center gap-1.5 uppercase">
                <HardDrive size={12} className="text-primary-start" /> Storage Protection Active
            </span>
          </div>
        </div>

        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="relative flex-1">
              <Search size={13} className="absolute left-3 top-2.5 text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filtro regjistrimet CCTV..."
                className="w-full bg-surface border border-main rounded-xl pl-8 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-primary-start"
              />
            </div>
            <button
              onClick={loadVisualEvidence}
              title="Rifresko listën"
              className="p-2 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
            >
              <RefreshCw size={13} className={loadingMedia ? 'animate-spin' : ''} />
            </button>
          </div>

          <div className="space-y-2 max-h-[340px] sm:max-h-[380px] overflow-y-auto custom-finance-scroll pr-1">
            {filteredVisuals.length === 0 ? (
              <div className="text-center py-8 text-xs text-text-muted">
                {loadingMedia ? 'Duke lexuar arkivën...' : 'Nuk ka asnjë provë vizuale.'}
              </div>
            ) : (
              filteredVisuals.map((visual) => {
                const isSelected = visual.id === selectedVisualId;
                const isDeleting = visual.id === deletingMediaId;
                const itemIsVideo = visual.media_type === 'video' || (visual.mime_type || '').startsWith('video/');

                return (
                  <div
                    key={visual.id}
                    onClick={() => setSelectedVisualId(visual.id)}
                    className={`p-2.5 sm:p-3 rounded-xl sm:rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-2 ${
                      isSelected
                        ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                        : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
                      <div className={`p-1.5 sm:p-2 rounded-xl shrink-0 ${isSelected ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                        {itemIsVideo ? <Video size={14} className="sm:w-4 sm:h-4" /> : <Camera size={14} className="sm:w-4 sm:h-4" />}
                      </div>
                      <div className="truncate text-xs min-w-0 flex-1">
                        <p className="font-bold truncate text-text-primary text-xs sm:text-sm">{visual.file_name}</p>
                        <p className="text-[9px] sm:text-[10px] font-mono text-text-muted flex items-center gap-1 mt-0.5">
                          <Clock size={10} />
                          {visual.created_at ? new Date(visual.created_at).toLocaleTimeString('sq-AL', { hour: '2-digit', minute: '2-digit' }) : '00:00'}
                          <span className="hidden sm:inline">• {itemIsVideo ? 'CCTV Video' : 'Foto EXIF'}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {isSelected && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
                      <button
                        type="button"
                        onClick={(e) => handleDeleteVisual(visual.id, visual.file_name, e)}
                        disabled={isDeleting}
                        title="Fshij provën"
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

      {/* KOLONA E DJATHTË */}
      <div className="lg:col-span-7 space-y-4">
        {activeVisual && streamUrl && (
          <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 truncate">
                <Eye size={15} className="text-primary-start shrink-0" />
                <span className="text-xs font-bold truncate max-w-[200px] sm:max-w-xs text-text-primary">{activeVisual.file_name}</span>
              </div>
              <span className="text-[9px] sm:text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface border border-main text-text-muted shrink-0">
                {isVideo ? 'Video' : 'Foto'}
              </span>
            </div>

            <div className="relative rounded-xl sm:rounded-2xl overflow-hidden bg-black flex items-center justify-center max-h-[200px] sm:max-h-[280px]">
              {isVideo ? (
                <video
                  ref={videoRef}
                  src={streamUrl}
                  controls
                  className="w-full h-auto max-h-[200px] sm:max-h-[280px] object-contain"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
              ) : (
                <img
                  src={streamUrl}
                  alt={activeVisual.file_name}
                  className="w-full h-auto max-h-[200px] sm:max-h-[280px] object-contain"
                />
              )}
            </div>

            {isVideo && (
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={togglePlayVideo}
                  className="px-3 sm:px-4 py-1.5 rounded-xl bg-primary-start text-white text-[10px] sm:text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  {isPlaying ? <Pause size={13} /> : <Play size={13} />}
                  <span>{isPlaying ? 'Pauzë' : 'Luaj Videon'}</span>
                </button>
                <div className="text-right">
                    <span className="text-[9px] sm:text-[10px] font-mono text-primary-start font-bold flex items-center justify-end gap-1">
                    <Film size={11} /> Nxjerrje Kyçe
                    </span>
                    <p className="text-[9px] text-text-muted mt-0.5">Për transkriptim zëri, ngarkoni këtë video te "Laboratori i Audios".</p>
                </div>
              </div>
            )}
          </div>
        )}

        {!isVideo && activeVisual && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="glass-panel p-3.5 sm:p-4 rounded-xl sm:rounded-2xl border border-main bg-card text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-text-muted flex items-center gap-1.5 uppercase text-[9px] sm:text-[10px] tracking-wider">
                  <MapPin size={12} className="text-emerald-500" /> Koordinatat GPS:
                </span>
                {exifData?.google_maps_url && (
                  <a
                    href={exifData.google_maps_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] text-primary-start hover:underline flex items-center gap-0.5"
                  >
                    Hap <ExternalLink size={10} />
                  </a>
                )}
              </div>
              {exifData?.has_gps ? (
                <div className="font-mono text-text-primary text-[10px] sm:text-[11px] space-y-0.5">
                  <p>Lat: {exifData.latitude}</p>
                  <p>Lon: {exifData.longitude}</p>
                  <p className="text-text-muted">Data: {exifData.original_date || 'E regjistruar'}</p>
                </div>
              ) : (
                <p className="text-[10px] sm:text-[11px] text-text-muted italic">Koordinatat GPS do të zbulohen pas shtypjes së Ekspertizës.</p>
              )}
            </div>

            <div className="glass-panel p-3.5 sm:p-4 rounded-xl sm:rounded-2xl border border-main bg-card text-xs space-y-1.5">
              <span className="font-bold text-text-muted flex items-center gap-1.5 uppercase text-[9px] sm:text-[10px] tracking-wider">
                <Camera size={12} className="text-primary-start" /> Integriteti i Pikselave (ELA):
              </span>
              {elaData ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] sm:text-[11px]">
                    <span>Rreziku:</span>
                    <span className={`font-bold font-mono ${elaData.is_suspicious ? 'text-rose-500' : 'text-emerald-500'}`}>
                      {elaData.manipulation_risk_score}%
                    </span>
                  </div>
                  <p className={`text-[9px] sm:text-[10px] font-bold ${elaData.is_suspicious ? 'text-rose-500' : 'text-emerald-500'}`}>
                    {elaData.verdict}
                  </p>
                </div>
              ) : (
                <p className="text-[10px] sm:text-[11px] text-text-muted italic">Verifikimi ELA do të llogaritet gjatë Ekspertizës.</p>
              )}
            </div>
          </div>
        )}

        {/* HAPËSIRA E RAPORTIT */}
        <div className="glass-panel p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-3.5">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert size={16} className="text-primary-start" />
                <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary">
                  {isVideo ? 'Autopsia e Videos CCTV' : 'Autopsia e Fotografisë'}
                </h3>
              </div>
              <p className="text-[10px] sm:text-xs text-text-muted mt-0.5">
                {isVideo
                  ? 'Kornizat kyçe, montazhi vizual (Transkripti në skedën Audio)'
                  : 'Vlerësimi i pikselave, EXIF/GPS dhe autenticitetit ligjor'}
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

              {(cctvAnalysis || imageAnalysis) && (
                <button
                  type="button"
                  onClick={() => handleCopyReport(
                    cctvReport?.expert_summary || imageOpinion?.expert_statement || ''
                  )}
                  className="h-8 sm:h-9 px-2.5 sm:px-3 bg-surface hover:bg-hover border border-main rounded-xl text-[10px] sm:text-xs font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedReport ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span className="hidden sm:inline">{copiedReport ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={handleRunVisualForensics}
                disabled={!selectedVisualId || isAnalyzing}
                className="h-8 sm:h-9 px-3.5 sm:px-4 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 shadow-sm transition-all disabled:opacity-40 cursor-pointer"
              >
                {isAnalyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                <span>{cctvAnalysis || imageAnalysis ? 'Ri-Eksperto' : 'Fillo Ekspertizën'}</span>
              </button>
            </div>
          </div>

          <div 
            className="min-h-[260px] max-h-[380px] sm:max-h-[420px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-text-primary select-text space-y-3"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {cctvAnalysis ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-surface rounded-xl border border-main">
                  <span className="font-bold text-xs sm:text-sm">Integriteti i Vizual CCTV:</span>
                  <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] sm:text-[11px] ${
                    cctvAnalysis.is_manipulated ? 'bg-rose-500/20 text-rose-500' : 'bg-emerald-500/20 text-emerald-500'
                  }`}>
                    {cctvReport?.tamper_verdict || (cctvAnalysis.is_manipulated ? 'I DYSHUAR' : 'E PACËNUAR')}
                  </span>
                </div>

                {cctvReport?.cctv_chronology && cctvReport.cctv_chronology.length > 0 && (
                  <div className="p-3 bg-surface rounded-xl border border-main space-y-2">
                    <h4 className="font-bold text-text-primary flex items-center gap-1.5 uppercase text-[10px] sm:text-[11px]">
                      <Clock size={13} className="text-primary-start" /> Kronologjia Skenë-pas-Skene:
                    </h4>
                    <div className="space-y-1.5 font-mono text-[10px] sm:text-[11px]">
                      {cctvReport.cctv_chronology.map((sc, i) => (
                        <div key={i} className="p-2 bg-card rounded-lg border border-main/40 flex items-start gap-2">
                          <span className="font-bold text-primary-start shrink-0">{sc.timestamp}</span>
                          <span className="text-text-primary">{sc.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {cctvReport?.court_admissibility_statement && (
                  <div className="p-3 bg-primary-start/10 rounded-xl border border-primary-start/20 space-y-1">
                    <h4 className="font-bold text-primary-start flex items-center gap-1.5 text-[10px] sm:text-[11px] uppercase">
                      <FileCheck size={13} /> Vlefshmëria si Provë (Pamje) në Gjyq:
                    </h4>
                    <p className="text-text-primary text-xs sm:text-sm">{cctvReport.court_admissibility_statement}</p>
                  </div>
                )}

                <div className="p-3 bg-card rounded-xl border border-main space-y-1">
                  <h4 className="font-bold text-text-primary text-[10px] sm:text-[11px] uppercase">Përmbledhja e Ekspertit (Vetëm Pamje):</h4>
                  <p className="text-text-muted whitespace-pre-wrap text-xs sm:text-sm">{cctvReport?.expert_summary}</p>
                </div>
              </div>
            ) : imageAnalysis ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-surface rounded-xl border border-main">
                  <span className="font-bold text-xs sm:text-sm">Autenticiteti i Fotos:</span>
                  <span className="px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] sm:text-[11px] bg-emerald-500/20 text-emerald-500">
                    {imageOpinion?.authenticity_assessment || 'I VERIFIKUAR'}
                  </span>
                </div>

                {visionData?.objects && visionData.objects.length > 0 && (
                  <div className="p-3 bg-surface rounded-xl border border-main space-y-1.5">
                    <h4 className="font-bold text-text-primary flex items-center gap-1.5 text-[10px] sm:text-[11px] uppercase">
                      <Crosshair size={13} className="text-primary-start" /> Objektet e Zbuluara:
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {visionData.objects.map((obj, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-md bg-card border border-main text-[10px] sm:text-[11px] font-mono flex items-center gap-1">
                          <Tag size={10} className="text-primary-start" /> {obj.name} ({Math.round(obj.score * 100)}%)
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="p-3 bg-card rounded-xl border border-main space-y-1">
                  <h4 className="font-bold text-text-primary text-[10px] sm:text-[11px] uppercase">Konkluzioni Formal:</h4>
                  <p className="text-text-muted whitespace-pre-wrap text-xs sm:text-sm">{imageOpinion?.expert_statement}</p>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2 py-8">
                <AlertTriangle size={32} className="opacity-30 text-primary-start" />
                <p className="text-xs sm:text-sm max-w-xs sm:max-w-sm">
                  Përzgjidhni një provë vizuale majtas dhe shtypni <span className="font-bold text-text-primary">"Fillo Ekspertizën"</span> për autopsinë me Claude Sonnet 4.6.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VisualForensicLab;