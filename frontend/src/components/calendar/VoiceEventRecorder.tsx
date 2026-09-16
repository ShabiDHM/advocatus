// FILE: src/components/calendar/VoiceEventRecorder.tsx
// PHOENIX PROTOCOL - VOICE EVENT RECORDER V1.0.1 (RECORD → TRANSCRIBE → PARSE → PREFILL)
// ZERO TS WARNINGS • MOBILE + DESKTOP READY • AUTO-PARSE TO CALENDAR EVENT

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Loader2, X, AlertTriangle, Sparkles, Activity } from 'lucide-react';
import { apiService } from '../../services/api';
import { useLockBodyScroll } from '../../hooks/useLockBodyScroll';

export interface ParsedVoiceEvent {
  category?: 'AGENDA' | 'FACT';
  title?: string;
  description?: string;
  event_type?: string;
  priority?: string;
  start_date?: string;
  location?: string;
}

interface VoiceEventRecorderProps {
  isOpen: boolean;
  onClose: () => void;
  onParsed: (parsed: ParsedVoiceEvent, transcription: string) => void;
}

// Konstante — paritet me MediaEvidencePanel
const MAX_RECORDING_SECONDS = 120; // 2 min limit

function pickSupportedMimeType(): string {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/mp4;codecs=mp4a.40.2',
    'audio/mp4',
    'audio/mpeg',
  ];
  for (const m of candidates) {
    try {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(m)) {
        return m;
      }
    } catch {
      /* ignore */
    }
  }
  return '';
}

export const VoiceEventRecorder: React.FC<VoiceEventRecorderProps> = ({
  isOpen,
  onClose,
  onParsed,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chosenMimeRef = useRef<string>('');

  useLockBodyScroll(isOpen);

  // Pastrimi i resurseve gjatë unmount
  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          /* ignore */
        }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  // Pastrimi kur mbyllet modali
  useEffect(() => {
    if (!isOpen) {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          /* ignore */
        }
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      setIsRecording(false);
      setRecordingTime(0);
      setIsProcessing(false);
      setError(null);
      audioChunksRef.current = [];
    }
  }, [isOpen]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        if (mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.requestData();
        }
      } catch {
        /* ignore */
      }
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const audioConstraints: MediaTrackConstraints = {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: true,
        sampleRate: 48000,
        channelCount: 1,
      };

      const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
      streamRef.current = stream;

      const chosenMime = pickSupportedMimeType();
      chosenMimeRef.current = chosenMime;

      const options: MediaRecorderOptions = { audioBitsPerSecond: 128000 };
      if (chosenMime) options.mimeType = chosenMime;

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Prit chunk-un final (iOS Safari fix)
        await new Promise((resolve) => setTimeout(resolve, 200));

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        const blobType = mediaRecorder.mimeType || chosenMime || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: blobType });

        if (audioBlob.size === 0) {
          setError('Regjistrimi dështoi — nuk u kap asnjë audio. Provoni përsëri.');
          return;
        }

        // Extension sipas mimeType
        let ext = 'webm';
        if (blobType.includes('mp4') || blobType.includes('m4a')) ext = 'm4a';
        else if (blobType.includes('ogg')) ext = 'ogg';
        else if (blobType.includes('mpeg') || blobType.includes('mp3')) ext = 'mp3';

        const fileName = `Voice_${new Date().toISOString().replace(/[:.]/g, '-')}.${ext}`;
        const file = new File([audioBlob], fileName, { type: blobType });

        // Dërgo në backend për transkriptim + parsing
        setIsProcessing(true);
        try {
          const result = await apiService.transcribeVoiceAndParse(file);
          if (result && result.success) {
            onParsed(result.parsed || {}, result.transcription || '');
            onClose();
          } else {
            setError('Nuk mund të nxirreshin detajet. Provoni me fjalë më të qarta.');
          }
        } catch (err: any) {
          const detail =
            err?.response?.data?.detail ||
            err?.message ||
            'Dështoi analiza e regjistrimit. Provoni përsëri.';
          setError(String(detail));
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = window.setInterval(() => {
        setRecordingTime((prev) => {
          const next = prev + 1;
          if (next >= MAX_RECORDING_SECONDS) {
            stopRecording();
            return MAX_RECORDING_SECONDS;
          }
          return next;
        });
      }, 1000);
    } catch (err: any) {
      const errName = err?.name || '';
      if (errName === 'NotAllowedError' || errName === 'PermissionDeniedError') {
        setError('Jepni leje për mikrofonin në shfletues për të regjistruar.');
      } else if (errName === 'NotFoundError' || errName === 'DevicesNotFoundError') {
        setError('Nuk u gjet asnjë mikrofon në pajisje.');
      } else {
        setError(`Dështoi regjistrimi: ${err?.message || 'Gabim i panjohur'}`);
      }
    }
  }, [onParsed, onClose, stopRecording]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-3 z-[3000]"
        onClick={() => {
          if (!isRecording && !isProcessing) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.96 }}
          className="w-full max-w-md p-6 sm:p-8 rounded-[2.5rem] shadow-2xl border border-main bg-card flex flex-col items-center gap-6"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-center w-full shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-primary-start/15 text-primary-start flex items-center justify-center border border-primary-start/30">
                <Sparkles size={18} />
              </div>
              <div>
                <h2 className="text-sm font-black text-text-primary uppercase tracking-wider">
                  Regjistrim Zanor
                </h2>
                <p className="text-[10px] text-text-muted mt-0.5">
                  Fol dhe AI do të krijojë event-in
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={isRecording || isProcessing}
              className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Mbyll"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body — Mic Button dhe Statusi */}
          <div className="flex flex-col items-center gap-4 py-2 w-full">
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              className={`w-28 h-28 sm:w-32 sm:h-32 rounded-full flex items-center justify-center transition-all shadow-xl cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed ${
                isRecording
                  ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-rose-500/40 animate-pulse'
                  : 'bg-primary-start hover:bg-primary-start/90 text-white shadow-primary-start/40 hover:scale-105 active:scale-95'
              }`}
              aria-label={isRecording ? 'Ndalo regjistrimin' : 'Fillo regjistrimin'}
            >
              {isProcessing ? (
                <Loader2 size={44} className="animate-spin" />
              ) : isRecording ? (
                <Square size={44} className="fill-current" />
              ) : (
                <Mic size={52} />
              )}
            </button>

            {isRecording && (
              <div className="flex items-center gap-2 text-sm font-mono font-bold text-rose-500">
                <Activity size={14} className="animate-pulse" />
                <span className="tabular-nums">{formatTime(recordingTime)}</span>
                <span className="text-text-muted text-xs">/ {formatTime(MAX_RECORDING_SECONDS)}</span>
              </div>
            )}
            {isProcessing && (
              <p className="text-xs font-bold text-primary-start uppercase tracking-wider text-center">
                Duke transkriptuar dhe analizuar...
              </p>
            )}
            {!isRecording && !isProcessing && !error && (
              <p className="text-xs text-text-muted text-center max-w-xs leading-relaxed">
                Kliko mikrofonin dhe thuaj për shembull:<br />
                <span className="italic">"Takim me klientin nesër në orën 14:00 në gjykatë"</span>
              </p>
            )}
          </div>

          {error && (
            <div className="w-full bg-danger-start/10 border border-danger-start/30 rounded-xl p-3 flex items-start gap-3">
              <AlertTriangle size={16} className="text-danger-start shrink-0 mt-0.5" />
              <p className="text-[11px] text-danger-start font-medium leading-snug">{error}</p>
            </div>
          )}

          {!isRecording && !isProcessing && (
            <button
              type="button"
              onClick={onClose}
              className="w-full h-11 rounded-xl text-xs font-bold text-text-secondary hover:text-text-primary hover:bg-hover border border-main uppercase tracking-wider transition-colors cursor-pointer"
            >
              Anulo
            </button>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default VoiceEventRecorder;