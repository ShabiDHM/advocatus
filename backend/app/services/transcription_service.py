# FILE: backend/app/services/transcription_service.py
# PHOENIX PROTOCOL - TRANSCRIPTION SERVICE V13.0 (DIARIZATION SEGMENTS)
# V13.0: Kthen edhe segments (folës + sekonda) për shfaqje UI.
# V12.0: Hequr varësia nga app.services.forensic.

import os
import logging
import asyncio
from typing import Dict, Any, List

# Motorri i pavarur AssemblyAI
from app.services.assemblyai_service import (
    upload_audio_to_assemblyai,
    submit_diarization_job,
    poll_transcript_status,
    format_diarized_transcript,
)

logger = logging.getLogger(__name__)


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


def transcribe_media_file(file_path: str) -> Dict[str, Any]:
    """
    Ekzekuton transkriptimin fjalë-për-fjalë (Verbatim) duke përdorur
    motorin AssemblyAI me diarizim (folës A/B).

    Returns:
        {"text": str, "segments": List[dict]}
    """
    processed_path = file_path
    extracted_audio = False

    try:
        # Nxjerrja e audios nëse është video
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            audio_out = extract_audio_from_video(file_path)
            if audio_out != file_path:
                processed_path = audio_out
                extracted_audio = True

        file_size_mb = os.path.getsize(processed_path) / (1024 * 1024)
        logger.info(
            f"🎙️ [Client Media ASR] AssemblyAI upload ({file_size_mb:.2f} MB)"
        )

        # Përpunimi në AssemblyAI
        with open(processed_path, "rb") as audio_file:
            raw_bytes = audio_file.read()

        upload_url = upload_audio_to_assemblyai(raw_bytes)
        job_id = submit_diarization_job(upload_url)
        assembly_result = poll_transcript_status(job_id)

        # V13.0: Mbaj edhe segments
        formatted_transcript, segments, _ = format_diarized_transcript(assembly_result)

        if not formatted_transcript.strip():
            return {
                "text": "[Nuk u detektua zë i kuptueshëm në këtë incizim.]",
                "segments": [],
            }

        return {
            "text": formatted_transcript,
            "segments": segments,
        }

    except Exception as e:
        logger.error(f"❌ Transcription Error: {e}")
        return {
            "text": f"[Gabim gjatë transkriptimit: {str(e)}]",
            "segments": [],
        }
    finally:
        # Pastrimi i skedarëve të mbetur
        if (
            extracted_audio
            and processed_path != file_path
            and os.path.exists(processed_path)
        ):
            try:
                os.remove(processed_path)
            except Exception:
                pass


# =========================================================================
# PHOENIX ADAPTER: KLASA DHE INSTANCA QË PRITET NGA VIDEO_SERVICE
# =========================================================================
class TranscriptionService:
    """Klasë adapter për pajtueshmëri të plotë me video_service.py."""

    def transcribe(self, file_path: str) -> Dict[str, Any]:
        return transcribe_media_file(file_path)

    async def transcribe_audio_async(self, file_path: str) -> Dict[str, Any]:
        """Metodë asinkrone e kërkuar drejtpërdrejt nga VideoService."""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, transcribe_media_file, file_path)
        return {
            "text": result.get("text", ""),
            "segments": result.get("segments", []),
            "language": "sq",
            "duration": 0,
            "summary": "Transkript i plotë Verbatim fjalë-për-fjalë.",
        }


# Instanca zyrtare e eksportuar
transcription_service = TranscriptionService()