# FILE: backend/app/services/video_forensic_service.py
# PHOENIX PROTOCOL - AUDIO EXTRACTOR & VERBATIM TRANSCRIPTION ONLY (NO VISION / NO KEYFRAMES)

import os
import logging
import tempfile
import subprocess
import asyncio
from typing import Dict, Any

from app.services.transcription_service import transcription_service

logger = logging.getLogger(__name__)


def extract_audio_from_video(video_path: str) -> str:
    """
    Përdor FFmpeg për të nxjerrë VETËM zërin (MP3 me cilësi të optimizuar) nga videoja.
    Heq komplet videon dhe kthen shtegun e skedarit audio.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Skedari video nuk ekziston: {video_path}")

    temp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_audio_path = temp_audio_file.name
    temp_audio_file.close()

    try:
        # Nxjerr vetëm audio në format MP3 64k mono (ideale për zë dhe shumë e lehtë)
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",                  # Heq komplet figurën (No Video)
            "-acodec", "libmp3lame",
            "-ac", "1",             # Mono (zë)
            "-ar", "16000",         # 16kHz (perfekte për AI transkriptim)
            "-b:a", "64k",          # Madhësi minimale skedari
            temp_audio_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        if result.returncode != 0:
            logger.error(f"FFmpeg audio extraction failed: {result.stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError("Dështoi nxjerrja e audios nga videoja.")

        logger.info(f"✅ Audio u nxorr me sukses nga videoja: {temp_audio_path}")
        return temp_audio_path

    except Exception as e:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        raise e


class VideoForensicService:
    """
    Shërbim i thjeshtuar: Nxjerr vetëm zërin dhe kthen Transkriptimin Verbatim.
    """

    async def analyze_video_evidence_async(self, video_path: str, file_name: str) -> Dict[str, Any]:
        if not os.path.exists(video_path):
            return {"error": "Skedari video nuk ekziston."}

        temp_audio_path = ""
        try:
            logger.info(f"🎙️ [Video -> Audio] Duke nxjerrë zërin nga: {file_name}")
            temp_audio_path = await asyncio.to_thread(extract_audio_from_video, video_path)

            # Thërret shërbimin e transkriptimit fjalë për fjalë (Verbatim)
            logger.info("📝 Duke filluar transkriptimin e zërit...")
            transcript_result = await transcription_service.transcribe_audio_async(temp_audio_path)

            return {
                "status": "success",
                "transcription": transcript_result.get("text", ""),
                "language": transcript_result.get("language", "sq"),
                "duration_seconds": transcript_result.get("duration", 0),
                "summary": transcript_result.get("summary", "Transkriptim fjalë për fjalë i nxjerrë nga video-prova.")
            }

        except Exception as e:
            logger.error(f"❌ Gabim gjatë transkriptimit të videos: {e}")
            return {
                "status": "error",
                "error": str(e),
                "transcription": ""
            }
        finally:
            # Fshin gjithmonë skedarin audio të përkohshëm nga disku
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass


video_forensic_service = VideoForensicService()