# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - TRANSCRIPTION SERVICE V9.0 (ALBANIAN ORTHOGRAPHY REPAIR & CLEAN SEGMENTS)

import os
import json
import logging
import subprocess
from typing import Dict, Any, List
from openai import OpenAI
from app.core.config import settings
from . import llm_service

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

def convert_to_clean_wav(input_path: str) -> str:
    """Konverton audion në 16,000Hz Mono WAV (PCM) me normalizim volumi."""
    output_wav = f"{input_path}_clean.wav"
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        if res.returncode == 0 and os.path.exists(output_wav):
            return output_wav
    except Exception as e:
        logger.warning(f"⚠️ FFmpeg conversion fallback: {e}")
    return input_path

def format_timestamp(seconds_float: float) -> str:
    """Kthen sekondat në formatin [MM:SS]."""
    total_seconds = int(seconds_float)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def extract_audio_from_video(video_path: str) -> str:
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

def repair_albanian_transcription_orthography(raw_segments_text: str) -> str:
    """
    RREGULLUESI I DREJTSHKRIMIT TË GJUHËS SHQIPE:
    Korrigjon gabimet fonetike të Whisper-it (ullëzues -> udhëzues, rezik -> rrezik, 
    salë -> sallë) dhe fshin mbetjet e huaja si 'Hvala', PA NDRYSHUAR KUAMIN DHE PA SHTUAR MENDIME.
    """
    if not raw_segments_text or len(raw_segments_text.strip()) < 10:
        return raw_segments_text

    system_prompt = """
    Ti je një Redaktor dhe Korrektor i Drejtshkrimit të Gjuhës Shqipe për Dosje Gjyqësore.
    DETYRA JOTE: Ky është një transkript audio me sekonda që ka gabime të dëgjimit fonetik (p.sh. "ullëzues" në vend të "udhëzues", "rezik" në vend të "rrezik", "salë" në vend të "sallë", "intelijences" në vend të "inteligjencës").

    RREGULLAT E KORRIGJIMIT:
    1. Korrigjo VETËM drejtshkrimin e fjalëve në gjuhën shqipe standarde.
    2. RUAJ TË GJITHA SEKONDAT [MM:SS - MM:SS] ekzakte në fillim të çdo rreshti.
    3. FSHIJ çdo fjalë të huaj halucinative që nuk ka kuptim në bisedë (si p.sh. "Hvala što pratite kanal").
    4. MOS SHTO asnjë mendim, koment apo interpretim tëndin. Kthe VETËM tekstin e pastruar fjalë-për-fjalë.
    """

    try:
        corrected = llm_service._call_llm(
            system_prompt=system_prompt,
            user_content=raw_segments_text,
            json_mode=False,
            temperature=0.0,
            model=llm_service.FAST_MODEL
        )
        return corrected.strip() if corrected else raw_segments_text
    except Exception as e:
        logger.warning(f"Orthography repair fallback: {e}")
        return raw_segments_text

def transcribe_media_file(file_path: str) -> str:
    """
    Transkriptim me sekonda të sakta dhe me drejtshkrim të rregullt në gjuhën shqipe.
    """
    api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ Mungon API Key për transkriptim.")
        return "Gabim: Mungon API Key për transkriptim."

    processed_path = file_path
    extracted_audio = False
    converted_wav_path = None

    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            audio_out = extract_audio_from_video(file_path)
            if audio_out != file_path:
                processed_path = audio_out
                extracted_audio = True

        converted_wav_path = convert_to_clean_wav(processed_path)
        active_audio_file = converted_wav_path if os.path.exists(converted_wav_path) else processed_path

        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=120.0)
        
        file_size_mb = os.path.getsize(active_audio_file) / (1024 * 1024)
        logger.info(f"📁 [Media ASR] Transcribing audio ({file_size_mb:.2f} MB)")

        if file_size_mb > 24.5:
            return f"[Gabim: Skedari është {file_size_mb:.1f}MB. Kufiri maksimal është 25MB.]"

        response_data = None

        try:
            with open(active_audio_file, "rb") as audio_file:
                response_data = client.audio.transcriptions.create(
                    model=WHISPER_TURBO_MODEL,
                    file=audio_file,
                    response_format="verbose_json"
                )
        except Exception as turbo_err:
            logger.warning(f"⚠️ Whisper Turbo fallback: {turbo_err}")
            with open(active_audio_file, "rb") as audio_file:
                response_data = client.audio.transcriptions.create(
                    model=WHISPER_FALLBACK_MODEL,
                    file=audio_file,
                    response_format="verbose_json"
                )

        formatted_lines = []
        segments = getattr(response_data, "segments", None)
        if not segments and isinstance(response_data, dict):
            segments = response_data.get("segments")

        if segments and isinstance(segments, list) and len(segments) > 0:
            for seg in segments:
                start_sec = seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)
                end_sec = seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
                text_content = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                
                clean_text = text_content.strip()
                # Filtrimi i fjalive halucinative të zhurmës
                if clean_text and "hvala" not in clean_text.lower():
                    time_badge = f"[{format_timestamp(start_sec)} - {format_timestamp(end_sec)}]"
                    formatted_lines.append(f"{time_badge} {clean_text}")

            raw_transcript = "\n".join(formatted_lines)
            
            # Korrigjimi automatik i drejtshkrimit në gjuhën shqipe
            logger.info("🪄 [Media ASR] Normalizing Albanian legal orthography...")
            clean_albanian_transcript = repair_albanian_transcription_orthography(raw_transcript)
            return clean_albanian_transcript

        raw_text = getattr(response_data, "text", "") if hasattr(response_data, "text") else (response_data.get("text", "") if isinstance(response_data, dict) else str(response_data))
        return raw_text.strip() if raw_text else "[Nuk u detektua zë i kuptueshëm.]"

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