# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - TRANSCRIPTION SERVICE V3.1 (ZERO WARNINGS • TRILINGUAL WHISPER)

import os
import logging
from openai import OpenAI
from app.core.config import settings
from . import llm_service

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

def polish_transcript_with_ai(raw_text: str) -> str:
    """
    Përpunon transkriptin e papërpunuar me saktësi forenzike,
    duke ruajtur 100% bisedat mikse (Shqip, Anglisht, Gjermanisht) pa i përkthyer me zor.
    """
    if not raw_text or len(raw_text.strip()) < 10:
        return raw_text

    system_prompt = """
    Ti je një Ekspert i Gjuhësisë Forenzike dhe Transkriptimit Gjyqësor për Drejtësinë e Kosovës.
    DETYRA: Ky është një transkript i papërpunuar audio nga një incizim/bisedë familjare ose zyrtare me gjuhë të përzier (Code-Switching: Shqip, English, Deutsch - p.sh. fëmijë apo persona që flasin 60% shqip dhe 40% anglisht/gjermanisht).

    RREGULLAT E HEKURTA TË VLEFSHMËRISË GJYQËSORE:
    1. RUAJ GJUHËN ORIGJINALE TË ÇDO FJALE: Nëse një fjalë apo fjali është folur në Anglisht apo Gjermanisht, LËRE NË ANGLISHT/GJERMANISHT! Mos e përkthe në shqip nëse folësi e ka thënë në gjuhë tjetër.
    2. Korrigjo vetëm gabimet e dëgjimit fonetik të mikrofonit (zhurma, eho, pëshpëritje) dhe rregullo pikësimin e fjalive.
    3. Strukturoje dialogun qartë me paragrafe të ndara sipas radhës natyrale të bisedës.
    4. MOS ndrysho kuptimin apo thelbin e asnjë deklarate. Kthe VETËM tekstin e pastruar të bisedës.
    """
    try:
        polished = llm_service._call_llm(
            system_prompt=system_prompt, 
            user_content=f"TRANSKRIPTI I PAPËRPUNUAR:\n{raw_text}", 
            json_mode=False, 
            temperature=0.1, 
            model=llm_service.FAST_MODEL
        )
        return polished.strip() if polished else raw_text
    except Exception as e:
        logger.warning(f"Transcript AI polish fallback: {e}")
        return raw_text

def extract_audio_from_video(video_path: str) -> str:
    """Nxjerr audion nga skedarët video përmes moviepy nëse është e disponueshme."""
    audio_path = f"{video_path}.mp3"
    try:
        from moviepy.editor import VideoFileClip  # type: ignore
        logger.info(f"🎬 [Media] Extracting audio track from video...")
        clip = VideoFileClip(video_path)
        if clip.audio is not None:
            clip.audio.write_audiofile(audio_path, codec='mp3', logger=None)
            clip.close()
            if os.path.exists(audio_path):
                return audio_path
        clip.close()
    except Exception as e:
        logger.warning(f"⚠️ Moviepy extraction fallback: {e}")
    return video_path

def transcribe_media_file(file_path: str) -> str:
    """
    Transkripton audion duke përdorur Whisper Large V3 Turbo në OpenRouter
    me mbështetje të plotë për biseda mikse (Shqip, English, Deutsch).
    """
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

        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=90.0)
        
        file_size_mb = os.path.getsize(processed_path) / (1024 * 1024)
        logger.info(f"📁 [Media] Preparing audio file for Whisper Large V3 Turbo. Size: {file_size_mb:.2f} MB")

        if file_size_mb > 24.5:
            return f"[Gabim: Skedari është {file_size_mb:.1f}MB. Kufiri maksimal është 25MB. Ngarkoni një pjesë më të shkurtër nën 25MB.]"

        multilingual_prompt = (
            "Transkriptim zyrtar ligjor dhe hetimor shumëgjuhësh. "
            "Bisedë mikse në Gjuhën Shqipe (Kosovë), English, dhe Deutsch. "
            "Ruaj fjalët ekzakte në gjuhën përkatëse ku flitet."
        )

        raw_text = ""
        try:
            with open(processed_path, "rb") as audio_file:
                res = client.audio.transcriptions.create(
                    model=WHISPER_TURBO_MODEL,
                    file=audio_file,
                    prompt=multilingual_prompt,
                    response_format="json"
                )
                raw_text = res.text if hasattr(res, "text") else (res.get("text", "") if isinstance(res, dict) else str(res))
        except Exception as turbo_err:
            logger.warning(f"⚠️ Whisper Large V3 Turbo error ({turbo_err}). Falling back to Whisper-1...")
            with open(processed_path, "rb") as audio_file:
                res = client.audio.transcriptions.create(
                    model=WHISPER_FALLBACK_MODEL,
                    file=audio_file,
                    prompt=multilingual_prompt,
                    response_format="json"
                )
                raw_text = res.text if hasattr(res, "text") else (res.get("text", "") if isinstance(res, dict) else str(res))

        if not raw_text or not raw_text.strip():
            return "[Nuk u detektua zë i qartë në këtë incizim audio.]"

        logger.info("🪄 [Media] Polishing trilingual transcript with AI...")
        clean_text = polish_transcript_with_ai(raw_text)
        return clean_text

    except Exception as e:
        logger.error(f"❌ Transcription Error: {e}")
        return f"[Gabim gjatë transkriptimit: {str(e)}]"
    finally:
        if extracted_audio and processed_path != file_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception:
                pass