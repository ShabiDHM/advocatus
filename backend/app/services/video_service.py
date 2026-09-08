# FILE: backend/app/services/video_service.py
# PHOENIX PROTOCOL - GENERIC VIDEO SERVICE V2.0 (FFMPEG COMPRESSION & AUDIO EXTRACTION)
# PROTECTS BACKBLAZE B2 FREE TIER • NO FORENSIC MISNOMERS

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
    Përdor FFmpeg për të nxjerrë VETËM zërin (MP3 64k mono) nga videoja për transkriptim.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Skedari video nuk ekziston: {video_path}")

    temp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_audio_path = temp_audio_file.name
    temp_audio_file.close()

    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn",                  # Heq figurën
            "-acodec", "libmp3lame", "-ac", "1", "-ar", "16000", "-b:a", "64k",
            temp_audio_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        if result.returncode != 0:
            logger.error(f"FFmpeg audio extraction failed: {result.stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError("Dështoi nxjerrja e audios nga videoja.")

        return temp_audio_path
    except Exception as e:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        raise e


async def compress_video_for_storage(input_path: str, output_path: str) -> bool:
    """
    Kompreson videon duke përdorur FFmpeg (H.264, CRF 28, Preset Fast)
    për të mbrojtur limitet e Backblaze B2 Free Tier (ul madhësinë deri në 80%).
    """
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vcodec", "libx264", 
            "-crf", "28",           # Kompresim agresiv por ruan cilësinë e mjaftueshme vizuale
            "-preset", "fast",      # Procesim i shpejtë
            "-acodec", "aac", 
            "-b:a", "128k",         # Audio e kompresuar
            output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        if proc.returncode == 0 and os.path.exists(output_path):
            logger.info(f"🎥 [VideoService] Video u kompresua me sukses: {output_path}")
            return True
        else:
            logger.warning(f"⚠️ [VideoService] Kompresimi dështoi (FFmpeg returned {proc.returncode}). Po përdoret origjinali.")
            return False
    except Exception as e:
        logger.error(f"❌ [VideoService] Gabim fatal në kompresim: {e}")
        return False


class VideoService:
    """
    Shërbim i thjeshtuar i përgjithshëm: Nxjerr zërin dhe kompreson videon.
    """
    async def analyze_video_evidence_async(self, video_path: str, file_name: str) -> Dict[str, Any]:
        if not os.path.exists(video_path):
            return {"error": "Skedari video nuk ekziston."}

        temp_audio_path = ""
        try:
            logger.info(f"🎙️ [Video -> Audio] Duke nxjerrë zërin nga: {file_name}")
            temp_audio_path = await asyncio.to_thread(extract_audio_from_video, video_path)

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
            return {"status": "error", "error": str(e), "transcription": ""}
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try: os.remove(temp_audio_path)
                except Exception: pass

video_service = VideoService()