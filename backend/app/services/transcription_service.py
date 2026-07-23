# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - WHISPER TRANSCRIPTION SERVICE V2.0 (DEFENSIVE MOVIEPY IMPORT)

import os
import logging
from openai import OpenAI
from app.core.config import settings
from . import llm_service

logger = logging.getLogger(__name__)

def polish_transcript_with_ai(raw_text: str) -> str:
    if not raw_text or len(raw_text.strip()) < 10:
        return raw_text

    system_prompt = """
    Ti je një transkriptues ligjor dhe analist gjuhësor. 
    DETYRA: Ky është një transkript i papërpunuar audio i një bisede ose seance në gjuhë të përzier (shqip dhe anglisht). 
    Korrigjo gabimet fonetike të dëgjimit, rregullo strukturën e fjalive, ruaj shprehjet në anglisht aty ku janë përdorur, dhe bëje transkriptin të pastër, profesional dhe lehtësisht të lexueshëm për një dosje gjyqësore.
    MOS ndrysho kuptimin e bisedës. Kthe VETËM tekstin e pastruar dhe të formatuar.
    """
    try:
        polished = llm_service._call_llm(
            system_prompt, 
            f"TRANSKRIPTI I PAPËRPUNUAR:\n{raw_text}", 
            json_mode=False, 
            temperature=0.2, 
            model=llm_service.FAST_MODEL
        )
        return polished.strip() if polished else raw_text
    except Exception as e:
        logger.warning(f"Transcript AI polish failed: {e}")
        return raw_text

def extract_audio_from_video(video_path: str) -> str:
    """Extracts MP3 audio track from video files using moviepy if available."""
    audio_path = f"{video_path}.mp3"
    try:
        from moviepy.editor import VideoFileClip  # type: ignore
        logger.info(f"🎬 [Media] Extracting audio track from video via moviepy...")
        clip = VideoFileClip(video_path)
        if clip.audio is not None:
            clip.audio.write_audiofile(audio_path, codec='mp3', logger=None)
            clip.close()
            if os.path.exists(audio_path):
                return audio_path
        clip.close()
    except Exception as e:
        logger.warning(f"⚠️ Moviepy audio extraction unavailable or failed: {e}")
    return video_path

def transcribe_media_file(file_path: str) -> str:
    api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ API key missing for media transcription.")
        return "Gabim: Mungon API Key për transkriptim."

    processed_path = file_path
    extracted_audio = False

    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            audio_out = extract_audio_from_video(file_path)
            if audio_out != file_path:
                processed_path = audio_out
                extracted_audio = True

        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        
        file_size_mb = os.path.getsize(processed_path) / (1024 * 1024)
        logger.info(f"📁 [Media] Preparing file for Whisper transcription. Size: {file_size_mb:.2f} MB")

        if file_size_mb > 24:
            return f"[Gabim: Skedari është {file_size_mb:.1f}MB. Kufiri i API është 25MB. Ju lutemi ngarkoni një incizim audio më të shkurtër (mp3/wav) ose nën 25MB.]"

        with open(processed_path, "rb") as audio_file:
            res = client.audio.transcriptions.create(
                model="openai/whisper-1",
                file=audio_file,
                response_format="json"
            )
            raw_text = res.text if hasattr(res, "text") else res.get("text", "")

        logger.info("🪄 [Media] Polishing full transcript with AI...")
        clean_text = polish_transcript_with_ai(raw_text)
        return clean_text
    except Exception as e:
        logger.error(f"❌ Whisper Transcription Error: {e}")
        return f"[Gabim në transkriptim: {str(e)}]"
    finally:
        if extracted_audio and processed_path != file_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception:
                pass