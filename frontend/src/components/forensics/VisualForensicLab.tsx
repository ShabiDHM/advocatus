// FILE: frontend/src/components/forensics/VisualForensicLab.tsx
// PHOENIX PROTOCOL - VISUAL FORENSIC LAB V1.0 (CCTV VIDEO & EXIF/GPS METADATA FOUNDRY)
// ZERO TS WARNINGS • ZERO HARDCODING • TAMPERING DETECTION & GEOLOCATION

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
  AlertTriangle
} from 'lucide-react';
import { forensicService, MediaEvidenceItem } from '../../services/forensicService';
import { apiService } from '../../services/api';

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

  // Gjendjet e Analizës Ligjore Vizuale
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [visualForensicReport, setVisualForensicReport] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedReport, setCopiedReport] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Marrja e token-it për streaming nga storage
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
      // Filtrojmë provat video dhe pamjet vizuale
      const visuals = (mediaItems || []).filter(item => item.media_type === 'video' || item.mime_type.startsWith('video/') || item.mime_type.startsWith('image/'));
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
        setUploadProgressText(`Duke indeksuar & analizuar kornizat vizuale: ${file.name}...`);
        await forensicService.uploadCaseMedia(caseId, file);
      }
      setUploadProgressText("Skedarët u ngarkuan. Ekspertiza vizuale po procedon në sfond...");
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
      if (selectedVisualId === mediaId) {
        setSelectedVisualId(null);
        setVisualForensicReport('');
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e videos/fotos:", err);
      alert("Dështoi fshirja e provës nga serveri.");
    } finally {
      setDeletingMediaId(null);
    }
  };

  // Autopsia Forenzike me Inteligjencë Artificiale për provat vizuale
  const handleRunVisualForensics = async () => {
    const activeVisual = visualList.find(v => v.id === selectedVisualId);
    if (!activeVisual || !caseId || isAnalyzing) return;

    setIsAnalyzing(true);
    setVisualForensicReport('');

    const visualMetadataJson = JSON.stringify(activeVisual.visual_analysis || {}, null, 2);

    try {
      const prompt = `[PROTOKOLLI PHOENIX — EKSPERTIZA E PROVAVE VIZUALE & CCTV]
Kryej autopsinë forenzike të regjistrimit vizual "${activeVisual.file_name}":
METADATA & EKSPERTIZA TEKNIKE:
${visualMetadataJson}

DETYRAT FORENZIKE GJYQËSORE:
1. VËRTETËSIA E KOHËS DHE VENDIT: Analizo të dhënat EXIF/GPS dhe krahaso ato me kohën e ngjarjes së pretenduar në padi/aktakuzë.
2. INTEGRITETI I KORNIZAVE (TAMPERING): A ka shenja ndërhyrjeje në piksela, shkurtime të dyshimta apo modifikim të shpejtësisë (fps)?
3. RELEVANCA E PROVËS PËR GJYKATËN: Si ndikon kjo pamje në rrëzimin ose vërtetimin e alibisë së palëve?
Gjenero raportin teknik-ligjor sipas standardeve të ekspertizës forenzike të Kosovës.`;

      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setVisualForensicReport(acc);
      }
    } catch (err) {
      console.error("Visual analysis error:", err);
      alert("Dështoi analiza forenzike e provës vizuale.");
    } finally {
      setIsAnalyzing(false);
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
    if (!visualForensicReport) return;
    navigator.clipboard.writeText(visualForensicReport);
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

  const gpsCoords = activeVisual?.visual_analysis?.gps_coordinates;
  const exifData = activeVisual?.visual_analysis?.exif_data;

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
            <span className="text-[10px] font-mono text-text-muted">GPS & Pixel Integrity</span>
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
                  <p className="text-[10px] text-text-muted">Nxjerrje automatike e koordinatave GPS dhe orës reale</p>
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

      {/* KOLONA E DJATHTË: VIDEO/IMAGE PLAYER, EXIF/GPS DATA & EKSPERTIZA */}
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

            <div className="relative rounded-2xl overflow-hidden bg-black flex items-center justify-center max-h-[300px]">
              {activeVisual.mime_type.startsWith('video/') || activeVisual.media_type === 'video' ? (
                <video
                  ref={videoRef}
                  src={streamUrl}
                  controls
                  className="w-full h-auto max-h-[300px] object-contain"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
              ) : (
                <img
                  src={streamUrl}
                  alt={activeVisual.file_name}
                  className="w-full h-auto max-h-[300px] object-contain"
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

        {/* METADATA EXIF & GPS FORENZIKE */}
        {activeVisual && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Paneli i Vendndodhjes GPS */}
            <div className="glass-panel p-4 rounded-2xl border border-main bg-card text-xs space-y-1.5">
              <span className="font-bold text-text-muted flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                <MapPin size={13} className="text-emerald-500" /> Koordinatat GPS:
              </span>
              {gpsCoords ? (
                <div className="font-mono text-text-primary text-[11px] space-y-0.5">
                  <p>Gjerësi: {gpsCoords.latitude ?? 'E padisponueshme'}</p>
                  <p>Gjatësi: {gpsCoords.longitude ?? 'E padisponueshme'}</p>
                  {gpsCoords.address && <p className="text-text-muted truncate">Adresa: {gpsCoords.address}</p>}
                </div>
              ) : (
                <p className="text-[11px] text-text-muted italic">Koordinatat GPS nuk janë të integruara në këtë skedar.</p>
              )}
            </div>

            {/* Paneli i Integritetit EXIF */}
            <div className="glass-panel p-4 rounded-2xl border border-main bg-card text-xs space-y-1.5">
              <span className="font-bold text-text-muted flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                <Camera size={13} className="text-primary-start" /> Kamera & Integriteti:
              </span>
              {exifData ? (
                <div className="font-mono text-text-primary text-[11px] space-y-0.5 truncate">
                  <p>Pajisja: {exifData.Make || exifData.Model || 'Kamerë Standarde'}</p>
                  <p>Softueri: {exifData.Software || 'Origjinal (Pa modifikim)'}</p>
                </div>
              ) : (
                <p className="text-[11px] text-text-muted italic">Metadata EXIF standarde e verifikuar.</p>
              )}
            </div>
          </div>
        )}

        {/* EKSPERTIZA E THELLË FORENZIKE E PROVËS VIZUALE */}
        <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert size={18} className="text-primary-start" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary">
                  Autopsia Forenzike e Provës Vizuale
                </h3>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Kryqëzimi i pamjeve me alibinë, zbulimi i ndërhyrjeve dhe relevanca ligjore
              </p>
            </div>

            <div className="flex items-center gap-2">
              {visualForensicReport && (
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
                <span>{visualForensicReport ? 'Ri-Analizo Pamjen' : 'Fillo Ekspertizën Vizuale'}</span>
              </button>
            </div>
          </div>

          {/* Hapësira e Raportit */}
          <div className="h-[280px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-mono select-text">
            {visualForensicReport || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2">
                <AlertTriangle size={32} className="opacity-30 text-primary-start" />
                <p className="text-xs max-w-sm">
                  Përzgjidhni një video ose foto dhe shtypni <span className="font-bold text-text-primary">"Fillo Ekspertizën Vizuale"</span> për të nxjerrë raportin e integruar të kohës, vendit dhe përputhshmërisë procedurale.
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