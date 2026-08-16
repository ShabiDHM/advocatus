# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - TRANSCRIPTION SERVICE V8.0 (100% PURE VERBATIM ASR • ZERO HARDCODING • ZERO LLM DISTORTION)

import os
import json
import logging
import subprocess
from typing import Dict, Any, List
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

def convert_to_clean_wav(input_path: str) -> str:
    """
    Konverton çdo skedar audio/video në formatin standard 16,000Hz Mono WAV (PCM)
    për të garantuar saktësi maksimale të dëgjimit fonetik pa zhurma.
    """
    output_wav = f"{input_path}_clean.wav"
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-ar", "16000",       # 16kHz standard
            "-ac", "1",           # Mono channel
            "-c:a", "pcm_s16le",  # Uncompressed PCM
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        if res.returncode == 0 and os.path.exists(output_wav):
            logger.info("🎙️ [Media DSP] Converted to clean 16kHz Mono WAV.")
            return output_wav
    except Exception as e:
        logger.warning(f"⚠️ FFmpeg 16kHz conversion fallback: {e}")
    return input_path

def format_timestamp(seconds_float: float) -> str:
    """Kthen sekondat në formatin zyrtar të gjykatës [MM:SS]."""
    total_seconds = int(seconds_float)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def extract_audio_from_video(video_path: str) -> str:
    """Nxjerr audion nga skedarët video."""
    audio_path = f"{video_path}.mp3"
    try:
        from moviepy.editor import VideoFileClip  # type: ignore
        clip = VideoFileClip(video_path)
        if clip.audio is not None:
            clip.audio.write_audiofile(audio_path, codec='mp3', logger=None)
            clip.close()
            if os.path.exists(audio_path):
                return audio_path
        clip.close()
    except Exception as e:
        logger.warning(f"Moviepy extraction fallback: {e}")
    return video_path

def transcribe_media_file(file_path: str) -> str:
    """
    TRANSKRIPTIM 100% FJALË-PËR-FJALË (PURE VERBATIM):
    Transkripton me sekonda ekzakte [MM:SS] drejtpërdrejt nga zëri,
    pa asnjë ndryshim, pa mendime dhe pa asnjë hardkodim.
    """
    api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ Mungon API Key për transkriptim.")
        return "Gabim: Mungon API Key për transkriptim."

    processed_path = file_path
    extracted_audio = False
    converted_wav_path = None

    try:
        # 1. Nxjerrja e audios nëse skedari është video
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            audio_out = extract_audio_from_video(file_path)
            if audio_out != file_path:
                processed_path = audio_out
                extracted_audio = True

        # 2. Pastrimi dhe konvertimi në 16kHz WAV
        converted_wav_path = convert_to_clean_wav(processed_path)
        active_audio_file = converted_wav_path if os.path.exists(converted_wav_path) else processed_path

        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=120.0)
        
        file_size_mb = os.path.getsize(active_audio_file) / (1024 * 1024)
        logger.info(f"📁 [Media ASR] Transcribing audio file ({file_size_mb:.2f} MB)")

        if file_size_mb > 24.5:
            return f"[Gabim: Skedari është {file_size_mb:.1f}MB. Kufiri maksimal është 25MB.]"

        response_data = None

        # 3. Thirrja e Whisper ASR me verbose_json për sekonda ekzakte
        try:
            with open(active_audio_file, "rb") as audio_file:
                response_data = client.audio.transcriptions.create(
                    model=WHISPER_TURBO_MODEL,
                    file=audio_file,
                    response_format="verbose_json"
                )
        except Exception as turbo_err:
            logger.warning(f"⚠️ Whisper Turbo fallback to Whisper-1: {turbo_err}")
            try:
                with open(active_audio_file, "rb") as audio_file:
                    response_data = client.audio.transcriptions.create(
                        model=WHISPER_FALLBACK_MODEL,
                        file=audio_file,
                        response_format="verbose_json"
                    )
            except Exception as fb_err:
                logger.error(f"❌ Whisper fallback failed: {fb_err}")
                return f"[Gabim gjatë transkriptimit: {str(fb_err)}]"

        formatted_lines = []
        file_base_name = os.path.basename(file_path)

        segments = getattr(response_data, "segments", None)
        if not segments and isinstance(response_data, dict):
            segments = response_data.get("segments")

        # 4. Ndërtimi i Transkriptit të Pastër Fjalë-për-Fjalë me Sekonda
        if segments and isinstance(segments, list) and len(segments) > 0:
            formatted_lines.append(f"=== TRANSKRIPTI FJALË-PËR-FJALË I PROVËS AUDIO/VIDEO ===")
            formatted_lines.append(f"📁 Skedari: {file_base_name}")
            formatted_lines.append("=" * 60 + "\n")

            for seg in segments:
                start_sec = seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)
                end_sec = seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
                text_content = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                
                clean_text = text_content.strip()
                if clean_text:
                    time_badge = f"[{format_timestamp(start_sec)} - {format_timestamp(end_sec)}]"
                    formatted_lines.append(f"{time_badge} {clean_text}")

            return "\n".join(formatted_lines)

        # Fallback nëse nuk ka segmente
        raw_text = getattr(response_data, "text", "") if hasattr(response_data, "text") else (response_data.get("text", "") if isinstance(response_data, dict) else str(response_data))
        if raw_text and raw_text.strip():
            return f"=== TRANSKRIPTI I PROVËS: {file_base_name} ===\n\n{raw_text.strip()}"

        return "[Nuk u detektua zë i kuptueshëm në këtë regjistrim.]"

    except Exception as e:
        logger.error(f"❌ Transcription Error: {e}")
        return f"[Gabim gjatë transkriptimit: {str(e)}]"
    finally:
        if converted_wav_path and converted_wav_path != file_path and os.path.exists(converted_wav_path):
            try:
                os.remove(converted_wav_path)
            except Exception:
                pass
        if extracted_audio and processed_path != file_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception:
                pass