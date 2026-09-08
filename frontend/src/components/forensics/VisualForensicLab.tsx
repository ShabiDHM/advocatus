// FILE: frontend/src/components/forensics/VisualForensicLab.tsx
// PHOENIX PROTOCOL - FORENSIC VISUAL LAB V2.0 (EXIF/GPS • ELA TAMPER DETECTION • GOOGLE VISION • CLAUDE SONNET 4.6)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS

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
  FileCheck
} from 'lucide-react';
import { forensicService, MediaEvidenceItem } from '../../services/forensicService';
import { forensicDeskService, VisualAnalysisResponse } from '../../services/forensicDeskService';

interface VisualForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

export const VisualForensicLab: React.FC<VisualForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  const [visualList, setVisualList] = useState<MediaEvidenceItem[]>([]);
  const [selectedVisualId, setSelectedVisualId] = useState<string | null>(null);
  const [loadingMedia, setLoadingMedia] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [deletingMediaId, setDeletingMediaId] = useState<string | null>(null);

  // Gjendja e Video Player
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Gjendjet e Analizës Forenzike Vizuale
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [forensicResult, setForensicResult] = useState<VisualAnalysisResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedReport, setCopiedReport] = useState<boolean>(false);

  // Cache lokal i skedarëve të sapongarkuar
  const localFilesRef = useRef<Map<string, File>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const authToken = localStorage.getItem('token') || localStorage.getItem('access_token') || '';

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
      const mediaItems = await forensicService.getCaseMedia(caseId);
      const visuals = (mediaItems || []).filter(item =>
        item.media_type === 'video' ||
        item.mime_type.startsWith('video/') ||
        item.mime_type.startsWith('image/')
      );
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
    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgressText(`Duke ngarkuar në laborator: ${file.name}...`);
        const uploaded = await forensicService.uploadCaseMedia(caseId, file);
        if (uploaded?.id) {
          localFilesRef.current.set(uploaded.id, file);
        }
      }
      setUploadProgressText("Skedarët u ngarkuan me sukses.");
      await loadVisualEvidence();
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi ngarkimi i provës vizuale:", err);
      alert("Dështoi ngarkimi i skedarit vizual.");
    } finally {
      setIsUploading(false);
      setUploadProgressText('');
    }
  };

  const handleDeleteVisual = async (mediaId: string, fileName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të hiqni provën vizuale "${fileName}"?`);
    if (!confirmDelete) return;

    setDeletingMediaId(mediaId);
    try {
      await forensicService.deleteCaseMedia(caseId, mediaId);
      setVisualList(prev => prev.filter(v => v.id !== mediaId));
      localFilesRef.current.delete(mediaId);
      if (selectedVisualId === mediaId) {
        setSelectedVisualId(null);
        setForensicResult(null);
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e videos/fotos:", err);
      alert("Dështoi fshirja e provës nga serveri.");
    } finally {
      setDeletingMediaId(null);
    }
  };

  // EKSPERTIZA E THELLË FORENZIKE (EXIF, ELA DHE CLAUDE SONNET 4.6)
  const handleRunVisualForensics = async () => {
    const activeVisual = visualList.find(v => v.id === selectedVisualId);
    if (!activeVisual || !caseId || isAnalyzing) return;

    let targetFile = localFilesRef.current.get(activeVisual.id);

    if (!targetFile) {
      try {
        setIsAnalyzing(true);
        setUploadProgressText("Duke shkarkuar skedarin për ekspertizë të thellë...");
        const streamUrl = forensicService.getMediaStreamUrl(caseId, activeVisual.id, authToken);
        const res = await fetch(streamUrl);
        const blob = await res.blob();
        targetFile = new File([blob], activeVisual.file_name, { type: activeVisual.mime_type || 'image/jpeg' });
      } catch (e) {
        console.error("Nuk mund të shkarkohej prova nga storage:", e);
      }
    }

    if (!targetFile) {
      alert("Skedari vizual nuk u gjet për procesim direkt. Ju lutem ngarkojeni përsëri.");
      setIsAnalyzing(false);
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await forensicDeskService.analyzeVisualLab(
        caseId,
        targetFile,
        `Ekspertizë forenzike mbi provën ${activeVisual.file_name}`
      );
      setForensicResult(result);
    } catch (err: any) {
      console.error("Visual analysis error:", err);
      alert(err?.response?.data?.detail || "Dështoi analiza forenzike e provës vizuale.");
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

  const handleCopyReport = () => {
    if (!forensicResult?.forensic_opinion?.expert_statement) return;
    navigator.clipboard.writeText(forensicResult.forensic_opinion.expert_statement);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2500);
  };

  const activeVisual = visualList.find(v => v.id === selectedVisualId);
  const filteredVisuals = visualList.filter(v =>
    v.file_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const streamUrl = (activeVisual && caseId && authToken)
    ? forensicService.getMediaStreamUrl(caseId, activeVisual.id, authToken)
    : '';

  const exifData = forensicResult?.exif_metadata;
  const elaData = forensicResult?.tamper_analysis;
  const visionData = forensicResult?.vision_detection;
  const opinion = forensicResult?.forensic_opinion;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* KOLONA E MAJTË: NGARKIMI & REGJISTRI I VIDEOS/FOTOVE */}
      <div className="lg:col-span-5 space-y-4">
        {/* Dropzone për Skedarë Vizualë */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Video size={15} className="text-primary-start" /> Pamjet CCTV & Foto me EXIF
            </h3>
            <span className="text-[10px] font-mono text-primary-start font-bold">ELA & Google Vision</span>
          </div>

          <div
            onClick={() => !isUploading && fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!isUploading) handleUploadVisualFiles(e.dataTransfer.files);
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
                  <p className="text-xs font-bold text-text-primary">Kliko ose tërhiq video / foto (MP4, MOV, JPG, PNG)</p>
                  <p className="text-[10px] text-text-muted">Nxjerrje e GPS, orës origjinale dhe zbulim i montazhit</p>
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
        </div>

        {/* Paneli i Kërkimit dhe Përzgjedhjes së Provës Vizuale */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="relative flex-1 mr-2">
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
              title="Rifresko provat vizuale"
              className="p-2 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer"
            >
              <RefreshCw size={13} className={loadingMedia ? 'animate-spin' : ''} />
            </button>
          </div>

          <div className="space-y-2 max-h-[380px] overflow-y-auto custom-finance-scroll pr-1">
            {filteredVisuals.length === 0 ? (
              <div className="text-center py-8 text-xs text-text-muted">
                {loadingMedia ? 'Duke lexuar arkivën vizuale...' : 'Nuk ka asnjë provë vizuale të regjistruar.'}
              </div>
            ) : (
              filteredVisuals.map((visual) => {
                const isSelected = visual.id === selectedVisualId;
                const isDeleting = visual.id === deletingMediaId;
                const isVideo = visual.media_type === 'video' || visual.mime_type.startsWith('video/');

                return (
                  <div
                    key={visual.id}
                    onClick={() => setSelectedVisualId(visual.id)}
                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                        : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <div className={`p-2 rounded-xl ${isSelected ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                        {isVideo ? <Video size={16} /> : <Camera size={16} />}
                      </div>
                      <div className="truncate text-xs">
                        <p className="font-bold truncate text-text-primary">{visual.file_name}</p>
                        <p className="text-[10px] font-mono text-text-muted flex items-center gap-1">
                          <Clock size={10} />
                          {visual.created_at ? new Date(visual.created_at).toLocaleTimeString('sq-AL', { hour: '2-digit', minute: '2-digit' }) : '00:00'}
                          <span>• Statusi: {visual.status}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {visual.status === 'PROCESSING' && (
                        <span title="Analiza në progres">
                          <Loader2 size={13} className="animate-spin text-primary-start" />
                        </span>
                      )}
                      {isSelected && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
                      <button
                        type="button"
                        onClick={(e) => handleDeleteVisual(visual.id, visual.file_name, e)}
                        disabled={isDeleting}
                        title="Fshij provën vizuale"
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

      {/* KOLONA E DJATHTË: PLAYER, EXIF/GPS, ELA TAMPER & EKSPERTIZA E THELLË */}
      <div className="lg:col-span-7 space-y-4">
        {/* PLAYER I PROVËS VIZUALE */}
        {activeVisual && streamUrl && (
          <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Eye size={16} className="text-primary-start" />
                <span className="text-xs font-bold truncate max-w-xs text-text-primary">{activeVisual.file_name}</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface border border-main text-text-muted">
                {activeVisual.mime_type}
              </span>
            </div>

            <div className="relative rounded-2xl overflow-hidden bg-black flex items-center justify-center max-h-[280px]">
              {activeVisual.mime_type.startsWith('video/') || activeVisual.media_type === 'video' ? (
                <video
                  ref={videoRef}
                  src={streamUrl}
                  controls
                  className="w-full h-auto max-h-[280px] object-contain"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
              ) : (
                <img
                  src={streamUrl}
                  alt={activeVisual.file_name}
                  className="w-full h-auto max-h-[280px] object-contain"
                />
              )}
            </div>

            {(activeVisual.mime_type.startsWith('video/') || activeVisual.media_type === 'video') && (
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={togglePlayVideo}
                  className="px-4 py-1.5 rounded-xl bg-primary-start text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                  <span>{isPlaying ? 'Pauzë' : 'Luaj Videon'}</span>
                </button>
                <span className="text-[10px] font-mono text-text-muted flex items-center gap-1">
                  <Clock size={11} /> Korniza me Vlerë Gjyqësore
                </span>
              </div>
            )}
          </div>
        )}

        {/* METADATA EXIF & GPS + RREZIKU ELA */}
        {activeVisual && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Paneli i Vendndodhjes GPS */}
            <div className="glass-panel p-4 rounded-2xl border border-main bg-card text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-text-muted flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                  <MapPin size={13} className="text-emerald-500" /> Koordinatat GPS:
                </span>
                {exifData?.google_maps_url && (
                  <a
                    href={exifData.google_maps_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] text-primary-start hover:underline flex items-center gap-0.5"
                  >
                    Hap në Maps <ExternalLink size={10} />
                  </a>
                )}
              </div>
              {exifData?.has_gps ? (
                <div className="font-mono text-text-primary text-[11px] space-y-0.5">
                  <p>Gjerësi (Lat): {exifData.latitude}</p>
                  <p>Gjatësi (Lon): {exifData.longitude}</p>
                  <p className="text-text-muted">Data: {exifData.original_date || 'E regjistruar'}</p>
                </div>
              ) : (
                <p className="text-[11px] text-text-muted italic">Koordinatat GPS do të zbulohen pas shtypjes së Ekspertizës.</p>
              )}
            </div>

            {/* Paneli i Integritetit EXIF & ELA Tamper */}
            <div className="glass-panel p-4 rounded-2xl border border-main bg-card text-xs space-y-1.5">
              <span className="font-bold text-text-muted flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                <Camera size={13} className="text-primary-start" /> Integriteti i Pikselave (ELA):
              </span>
              {elaData ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span>Rreziku i Manipulimit:</span>
                    <span className={`font-bold font-mono ${elaData.is_suspicious ? 'text-rose-500' : 'text-emerald-500'}`}>
                      {elaData.manipulation_risk_score}%
                    </span>
                  </div>
                  <p className={`text-[10px] font-bold ${elaData.is_suspicious ? 'text-rose-500' : 'text-emerald-500'}`}>
                    {elaData.verdict}
                  </p>
                  {exifData?.software_used && (
                    <p className="text-[10px] text-amber-500 truncate">Softueri: {exifData.software_used}</p>
                  )}
                </div>
              ) : (
                <p className="text-[11px] text-text-muted italic">Kamera & Verifikimi ELA do të llogariten nga serveri.</p>
              )}
            </div>
          </div>
        )}

        {/* EKSPERTIZA E THELLË FORENZIKE ME CLAUDE SONNET 4.6 */}
        <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert size={18} className="text-primary-start" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary">
                  Autopsia Forenzike Vizuale
                </h3>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Vlerësimi i vlefshmërisë së provës, alibisë dhe objekteve me Claude Sonnet 4.6
              </p>
            </div>

            <div className="flex items-center gap-2">
              {opinion?.expert_statement && (
                <button
                  type="button"
                  onClick={handleCopyReport}
                  className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedReport ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedReport ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={handleRunVisualForensics}
                disabled={!selectedVisualId || isAnalyzing}
                className="h-9 px-4 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all disabled:opacity-40 cursor-pointer"
              >
                {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                <span>{forensicResult ? 'Ri-Eksperto Pamjen' : 'Fillo Ekspertizën Vizuale'}</span>
              </button>
            </div>
          </div>

          {/* Hapësira e Raportit dhe Objekteve të Zbuluara */}
          <div className="min-h-[240px] max-h-[380px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary select-text space-y-3">
            {forensicResult ? (
              <div className="space-y-3">
                {/* Statusi i Besueshmërisë */}
                <div className="flex items-center justify-between p-3 bg-surface rounded-xl border border-main">
                  <span className="font-bold">Statusi i Autenticitetit:</span>
                  <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[11px] ${
                    opinion?.authenticity_assessment === 'E MANIPULUAR' || opinion?.authenticity_assessment === 'E DYSHUAR'
                      ? 'bg-rose-500/20 text-rose-500 border border-rose-500/30'
                      : 'bg-emerald-500/20 text-emerald-500 border border-emerald-500/30'
                  }`}>
                    {opinion?.authenticity_assessment || 'I VERIFIKUAR'}
                  </span>
                </div>

                {/* Objektet e Zbuluara nga Google Vision */}
                {visionData?.objects && visionData.objects.length > 0 && (
                  <div className="p-3 bg-surface rounded-xl border border-main space-y-1.5">
                    <h4 className="font-bold text-text-primary flex items-center gap-1.5 text-[11px] uppercase">
                      <Crosshair size={13} className="text-primary-start" /> Objektet e Zbuluara në Skenë:
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {visionData.objects.map((obj, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-md bg-card border border-main text-[11px] font-mono flex items-center gap-1">
                          <Tag size={10} className="text-primary-start" /> {obj.name} ({Math.round(obj.score * 100)}%)
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Këshilla Taktike për Gjykatën */}
                {opinion?.court_defense_strategy && (
                  <div className="p-3 bg-primary-start/10 rounded-xl border border-primary-start/20 space-y-1">
                    <h4 className="font-bold text-primary-start flex items-center gap-1.5 text-[11px] uppercase">
                      <FileCheck size={13} /> Strategjia e Përdorimit në Gjykatë:
                    </h4>
                    <p className="text-text-primary">{opinion.court_defense_strategy}</p>
                  </div>
                )}

                {/* Deklarata Zyrtare e Ekspertit */}
                <div className="p-3 bg-card rounded-xl border border-main space-y-1">
                  <h4 className="font-bold text-text-primary text-[11px] uppercase">
                    Konkluzioni i Ekspertit:
                  </h4>
                  <p className="text-text-muted whitespace-pre-wrap">{opinion?.expert_statement}</p>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2 py-8">
                <AlertTriangle size={32} className="opacity-30 text-primary-start" />
                <p className="text-xs max-w-sm">
                  Përzgjidhni një video ose foto dhe shtypni <span className="font-bold text-text-primary">"Fillo Ekspertizën Vizuale"</span> për të analizuar EXIF/GPS, rrezikun ELA të manipulimit dhe objektet me Claude Sonnet 4.6.
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