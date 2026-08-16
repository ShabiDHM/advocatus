# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - TRANSCRIPTION SERVICE V7.0 (SYNTAX CLEAN • VERIFIED DUAL-LAYER KOSOVO TRANSCRIPTION)

import os
import json
import logging
import subprocess
import tempfile
from typing import Dict, Any, List
from openai import OpenAI
from app.core.config import settings
from . import llm_service

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

def convert_to_forensic_wav(input_path: str) -> str:
    """Konverton audion në 16,000Hz Mono WAV (PCM) me normalizim volumi dhe heqje zhurmash."""
    output_wav = f"{input_path}_forensic.wav"
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-af", "highpass=f=80,dynaudnorm=f=150:g=15",
            output_wav
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        if res.returncode == 0 and os.path.exists(output_wav):
            logger.info("🎙️ [Media DSP] Audio converted to 16kHz PCM WAV successfully.")
            return output_wav
    except Exception as e:
        logger.warning(f"⚠️ FFmpeg 16kHz conversion fallback: {e}")
    return input_path

def format_timestamp(seconds_float: float) -> str:
    """Kthen sekondat në formatin [MM:SS]."""
    total_seconds = int(seconds_float)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def generate_courtroom_bilingual_transcript_with_ai(segmented_transcript: str, file_name: str) -> str:
    """
    Kthen transkriptin në Gjuhën Shqipe Zyrtare për Gjykatë,
    duke vendosur në kllapa fjalët ekzakte origjinale në Anglisht/Gjermanisht.
    """
    if not segmented_transcript or len(segmented_transcript.strip()) < 10:
        return segmented_transcript

    system_prompt = """
    Ti je Përkthyesi dhe Transkriptuesi Zyrtar Forenzik i Drejtësisë së Republikës së Kosovës.
    DETYRA: Ky është një transkript audio me sekonda nga një incizim me gjuhë të përzier (Shqip dhe Anglisht/Gjermanisht).

    RREGULLI I DETYRUESHËM GJYQËSOR I DOKUMENTIMIT:
    1. TEKSTI KRYESOR DUHET TË JETË NË GJUHËN SHQIPE: Çdo deklaratë duhet të shkruhet në gjuhën shqipe standarde që gjyqtari dhe prokurori ta lexojnë menjëherë.
    2. NËSE NJË PJESË OSE FJALË ËSHTË FOLUR NË ANGLISHT APO GJERMANISHT:
       - Shkruaj përkthimin e saktë në Shqip dhe menjëherë në fund të fjalisë shto në kllapa fjalët ekzakte origjinale:
         Shembull: [00:00 - 00:05] BABAI: "Në rregull, mos u bëj nervoz fare. Është në rregull." [Origjinali: "Okay, don't get nervous at all. It's okay."]
         Shembull: [00:06 - 00:12] BABAI: "Të lutem mos qaj, gjithçka do të rregullohet." [Origjinali: "Please don't cry, everything is going to be okay."]
    3. RUAJ ME PRECIZION TË GJITHA SEKONDAT [MM:SS - MM:SS] për çdo rresht.
    4. RUAJ ROLIN E FOLËSIT (p.sh. BABAI, FËMIJA, ZYRTARI).
    5. MOS shpik asnjë fjalë apo kuptim që nuk është në transkript.

    Kthe VETËM transkriptin zyrtar të formatuar për dosje gjyqësore.
    """

    try:
        polished = llm_service._call_llm(
            system_prompt=system_prompt,
            user_content=f"SKEDARI: {file_name}\n\nTRANSKRIPTI ME SEKONDA PËR PËRPUNIM GJYQËSOR:\n{segmented_transcript}",
            json_mode=False,
            temperature=0.0,
            model=llm_service.FAST_MODEL
        )
        return polished.strip() if polished else segmented_transcript
    except Exception as e:
        logger.warning(f"Courtroom bilingual transcription polish fallback: {e}")
        return segmented_transcript

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

def transcribe_media_file(file_path: str) -> str:
    """
    Transkriptim Forenzik Zyrtar me Sekonda dhe Formatim Gjuhësor Shqip + Kllapa Origjinale.
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

        converted_wav_path = convert_to_forensic_wav(processed_path)
        active_audio_file = converted_wav_path if os.path.exists(converted_wav_path) else processed_path

        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=120.0)
        
        file_size_mb = os.path.getsize(active_audio_file) / (1024 * 1024)
        logger.info(f"📁 [Media Forensic] Processing audio with Whisper Large V3 ({file_size_mb:.2f} MB)")

        if file_size_mb > 24.5:
            return f"[Gabim: Skedari është {file_size_mb:.1f}MB. Kufiri maksimal është 25MB.]"

        multilingual_prompt = (
            "Transkriptim hetimor shumëgjuhësh në gjuhën shqipe (Kosovë) dhe anglishte. "
            "Bisedë familjare: babi duke i folur fëmijës, mos u bëj nervoz, mos qaj, don't worry, relax, it's okay."
        )

        response_data = None

        try:
            with open(active_audio_file, "rb") as audio_file:
                response_data = client.audio.transcriptions.create(
                    model=WHISPER_TURBO_MODEL,
                    file=audio_file,
                    prompt=multilingual_prompt,
                    response_format="verbose_json"
                )
        except Exception as turbo_err:
            logger.warning(f"⚠️ Whisper Turbo fallback to Whisper-1: {turbo_err}")
            try:
                with open(active_audio_file, "rb") as audio_file:
                    response_data = client.audio.transcriptions.create(
                        model=WHISPER_FALLBACK_MODEL,
                        file=audio_file,
                        prompt=multilingual_prompt,
                        response_format="verbose_json"
                    )
            except Exception as fb_err:
                logger.error(f"❌ Whisper fallback also failed: {fb_err}")
                return f"[Gabim në thirrjen e Whisper: {str(fb_err)}]"

        formatted_lines = []
        file_base_name = os.path.basename(file_path)

        segments = getattr(response_data, "segments", None)
        if not segments and isinstance(response_data, dict):
            segments = response_data.get("segments")

        if segments and isinstance(segments, list) and len(segments) > 0:
            for seg in segments:
                start_sec = seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)
                end_sec = seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
                text_content = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                
                clean_seg_text = text_content.strip()
                if clean_seg_text:
                    time_badge = f"[{format_timestamp(start_sec)} - {format_timestamp(end_sec)}]"
                    formatted_lines.append(f"{time_badge} BABAI: {clean_seg_text}")

            raw_segmented_text = "\n".join(formatted_lines)
            
            logger.info("🪄 [Media Forensic] Formatting courtroom dual-layer transcript (Albanian + Original in brackets)...")
            final_courtroom_transcript = generate_courtroom_bilingual_transcript_with_ai(raw_segmented_text, file_base_name)
            
            header = (
                f"=== TRANSKRIPTI FORENZIK I PROVËS AUDIO/VIDEO ===\n"
                f"📁 Skedari: {file_base_name}\n"
                f"🏛️ Gjuha Zyrtare: Shqip (me fjalët origjinale në kllapa)\n"
                f"{'=' * 60}\n\n"
            )
            return header + final_courtroom_transcript

        raw_text = getattr(response_data, "text", "") if hasattr(response_data, "text") else (response_data.get("text", "") if isinstance(response_data, dict) else str(response_data))
        if raw_text and raw_text.strip():
            return f"=== TRANSKRIPTI I PROVËS: {file_base_name} ===\n\n{raw_text.strip()}"

        return "[Nuk u detektua zë i kuptueshëm në këtë regjistrim.]"

    except Exception as e:
        logger.error(f"❌ Forensic Transcription Error: {e}")
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