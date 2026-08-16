# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - TRANSCRIPTION SERVICE V4.0 (DSP ACOUSTIC FILTER & FORENSIC STATEMENT LEDGER)

import os
import json
import logging
import subprocess
import tempfile
from openai import OpenAI
from app.core.config import settings
from . import llm_service

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

def apply_acoustic_forensic_filter(input_audio_path: str) -> str:
    """
    DSP ACOUSTIC PRE-PROCESSOR (FFmpeg):
    1. highpass=f=80: Heq zhurmat e rënda të ambientit (era, shiu, zhurma e motorit).
    2. dynaudnorm: Normalizon volumin e zërit që pëshpëritjet të dëgjohen qartë.
    """
    filtered_path = f"{input_audio_path}_cleaned.mp3"
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_audio_path,
            "-af", "highpass=f=80,dynaudnorm=f=150:g=15",
            "-q:a", "2",
            filtered_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        if res.returncode == 0 and os.path.exists(filtered_path):
            logger.info("🎧 [Media DSP] Acoustic forensic noise filter applied successfully.")
            return filtered_path
    except Exception as e:
        logger.warning(f"⚠️ FFmpeg acoustic filter skipped: {e}")
    return input_audio_path

def analyze_forensic_statements_with_ai(raw_text: str, file_name: str) -> dict:
    """
    GJENERON DITARIN FORENZIK TË DEKLARATAVE AUDIO:
    Ndan folësit dhe klasifikon deklaratat me vlerë provuese penale/civile.
    """
    if not raw_text or len(raw_text.strip()) < 15:
        return {"speakers": [], "forensic_statements": [], "polished_transcript": raw_text}

    system_prompt = """
    Ti je Ekspert i Gjuhësisë Forenzike dhe Analizës së Deklaratave Audio për Gjykatat e Kosovës.
    DETYRA: Analizo këtë transkript audio (Shqip, Anglisht, Gjermanisht) dhe nxirr Ditarin e Fakteve Penale/Civile.

    KLASIFIKIMET PENALE QË DUHET TË ZBULOSH:
    - "KANOSJE_APO_SHANTAZH" (Neni 386 KPRK)
    - "PRANIM_I_FAJËSISË_APO_SHKELJES"
    - "KUNDËRTHËNIE_ME_PROCESVERBALIN"
    - "TJETËRSIM_PRINDËROR_APO_PRESION" (Neni 250 KPRK)
    - "DEKLARATË_E_RREGULLT"

    RREGULL: Ruaj fjalët ekzakte në gjuhën që janë folur. Mos përkthe me zor.

    KTHE JSON:
    {
      "polished_transcript": "Teksti i plotë i pastruar dhe i strukturuar me dialog...",
      "forensic_statements": [
        {
          "speaker": "FOLËSI A | FOLËSI B",
          "exact_quote": "Citati ekzakt i fjalëve të thëna",
          "legal_classification": "KANOSJE_APO_SHANTAZH | PRANIM_I_FAJËSISË | KUNDËRTHËNIE",
          "evidentiary_value": "Shpjegimi i vlerës provuese për gjykatë"
        }
      ]
    }
    """
    try:
        raw = llm_service._call_llm(
            system_prompt, 
            f"INCIZIMI AUDIO: {file_name}\n\nTRANSKRIPTI I PAPËRPUNUAR:\n{raw_text}", 
            json_mode=True, 
            temperature=0.0, 
            model=llm_service.FAST_MODEL
        )
        parsed = llm_service.clean_and_parse_json(raw)
        if isinstance(parsed, dict) and "polished_transcript" in parsed:
            return parsed
        return {"polished_transcript": raw_text, "forensic_statements": []}
    except Exception as e:
        logger.warning(f"Audio statement forensic analysis fallback: {e}")
        return {"polished_transcript": raw_text, "forensic_statements": []}

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
    Transkriptim Forenzik i Plotë me Filtrin Akustik FFmpeg dhe Whisper Large V3 Turbo.
    """
    api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ API key missing for media transcription.")
        return "Gabim: Mungon API Key për transkriptim."

    processed_path = file_path
    extracted_audio = False
    cleaned_audio_path = None

    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            audio_out = extract_audio_from_video(file_path)
            if audio_out != file_path:
                processed_path = audio_out
                extracted_audio = True

        # 1. Pastrimi Akustik i Zhurmave me FFmpeg
        cleaned_audio_path = apply_acoustic_forensic_filter(processed_path)
        active_audio_file = cleaned_audio_path if os.path.exists(cleaned_audio_path) else processed_path

        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=90.0)
        
        file_size_mb = os.path.getsize(active_audio_file) / (1024 * 1024)
        logger.info(f"📁 [Media Forensic] Processing audio with Whisper Large V3 Turbo ({file_size_mb:.2f} MB)")

        if file_size_mb > 24.5:
            return f"[Gabim: Skedari është {file_size_mb:.1f}MB. Kufiri maksimal është 25MB. Ngarkoni një pjesë më të shkurtër nën 25MB.]"

        multilingual_prompt = (
            "Transkriptim zyrtar ligjor dhe hetimor shumëgjuhësh. "
            "Bisedë mikse në Gjuhën Shqipe (Kosovë), English, dhe Deutsch. "
            "Ruaj fjalët ekzakte në gjuhën përkatëse ku flitet."
        )

        raw_text = ""
        try:
            with open(active_audio_file, "rb") as audio_file:
                res = client.audio.transcriptions.create(
                    model=WHISPER_TURBO_MODEL,
                    file=audio_file,
                    prompt=multilingual_prompt,
                    response_format="json"
                )
                raw_text = res.text if hasattr(res, "text") else (res.get("text", "") if isinstance(res, dict) else str(res))
        except Exception as turbo_err:
            logger.warning(f"⚠️ Whisper Turbo fallback to Whisper-1: {turbo_err}")
            with open(active_audio_file, "rb") as audio_file:
                res = client.audio.transcriptions.create(
                    model=WHISPER_FALLBACK_MODEL,
                    file=audio_file,
                    prompt=multilingual_prompt,
                    response_format="json"
                )
                raw_text = res.text if hasattr(res, "text") else (res.get("text", "") if isinstance(res, dict) else str(res))

        if not raw_text or not raw_text.strip():
            return "[Nuk u detektua zë i qartë në këtë incizim audio.]"

        logger.info("🪄 [Media Forensic] Polishing transcript & extracting forensic statement ledger...")
        forensic_res = analyze_forensic_statements_with_ai(raw_text, os.path.basename(file_path))
        
        return forensic_res.get("polished_transcript") or raw_text

    except Exception as e:
        logger.error(f"❌ Forensic Transcription Error: {e}")
        return f"[Gabim gjatë transkriptimit: {str(e)}]"
    finally:
        if cleaned_audio_path and cleaned_audio_path != processed_path and os.path.exists(cleaned_audio_path):
            try:
                os.remove(cleaned_audio_path)
            except Exception:
                pass
        if extracted_audio and processed_path != file_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception:
                pass