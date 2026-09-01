# FILE: backend/app/services/pillars/media_forensics_service.py
# PHOENIX PROTOCOL - MEDIA FORENSICS V25.0 (UNIFIED ULTRA-FAST VERBATIM & RAG INDEXING)

import os
import re
import json
import logging
import subprocess
import asyncio
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from openai import OpenAI
import redis.asyncio as aioredis

from app.core.config import settings
from app.services.vector_store_service import create_and_store_embeddings_from_chunks
from app.services.pillars.role_guard_service import RoleGuardService

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

WHISPER_INITIAL_PROMPT = (
    "Transkriptim forenzik fjalë-për-fjalë (verbatim) në gjuhën shqipe dhe bisedore: "
    "dialog i drejtpërdrejtë, fjalët ekzakte të palëve, 'babi', 'mami', 'gjykata', 'seanca'."
)

NOISE_PATTERNS = [
    "Hvala",
    "Subtitles by",
    "Amara.org",
    "Subtitles",
    "Transcriber:",
    "www.",
    ".com",
    ".org",
    "REV.com",
    "Rev.com"
]


class MediaForensicsService:
    """
    Modul Ekskluziv për Zbardhjen Verbatim të Provave Audio dhe Video:
    - Nxjerrje automatike e zërit me FFmpeg nga çdo video/audio
    - Kompresim 32k mono 16kHz për të mos tejkaluar limitin 25MB të Whisper
    - 100% Verbatim me sekonda [MM:SS - MM:SS]
    - Indeksim i drejtpërdrejtë në RAG si Provë Materiale për Paditë dhe Analizat
    """

    @classmethod
    def extract_audio_for_whisper(cls, media_path: str) -> Optional[str]:
        """
        Nxjerr zërin nga videoja ose audioja dhe e optimizon në MP3 të lehtë.
        """
        temp_fd, audio_out = tempfile.mkstemp(suffix="_whisper.mp3")
        os.close(temp_fd)
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", media_path,
                "-vn",                  # Heq figurën nëse është video
                "-ar", "16000",         # 16kHz optimale për Whisper
                "-ac", "1",             # Mono
                "-b:a", "32k",          # Madhësi minimale
                audio_out
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
            if res.returncode == 0 and os.path.exists(audio_out) and os.path.getsize(audio_out) > 100:
                return audio_out
        except Exception as e:
            logger.error(f"❌ Audio extraction failed for whisper: {e}")
        
        if os.path.exists(audio_out):
            try:
                os.remove(audio_out)
            except Exception:
                pass
        return None

    @staticmethod
    def format_timestamp(seconds_float: float) -> str:
        total_seconds = int(seconds_float)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def clean_verbatim_transcript(raw_segments_text: str) -> str:
        if not raw_segments_text or len(raw_segments_text.strip()) < 10:
            return raw_segments_text
        
        cleaned_lines = []
        for line in raw_segments_text.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            has_noise = any(noise_word.lower() in line_stripped.lower() for noise_word in NOISE_PATTERNS)
            if has_noise:
                timestamp_match = re.match(r'^(\[\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\])\s*(.*)$', line_stripped)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    content = timestamp_match.group(2)
                    for noise_word in NOISE_PATTERNS:
                        content = re.sub(re.escape(noise_word), '', content, flags=re.IGNORECASE)
                    content = content.strip()
                    if content:
                        cleaned_lines.append(f"{timestamp} {content}")
            else:
                cleaned_lines.append(line_stripped)
        
        return "\n".join(cleaned_lines)

    @classmethod
    def transcribe_audio_file(cls, file_path: str) -> str:
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "[Gabim: Mungon API Key për transkriptim.]"

        whisper_audio_path = cls.extract_audio_for_whisper(file_path) or file_path
        created_temp = (whisper_audio_path != file_path)

        try:
            file_size_mb = os.path.getsize(whisper_audio_path) / (1024 * 1024)
            if file_size_mb > 24.5:
                return f"[Gabim: Skedari audio është {file_size_mb:.1f}MB. Kufiri maksimal është 25MB.]"

            client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=120.0)

            response_data = None
            try:
                with open(whisper_audio_path, "rb") as audio_file:
                    response_data = client.audio.transcriptions.create(
                        model=WHISPER_TURBO_MODEL,
                        file=audio_file,
                        prompt=WHISPER_INITIAL_PROMPT,
                        response_format="verbose_json"
                    )
            except Exception as turbo_err:
                logger.warning(f"Whisper turbo fallback: {turbo_err}")
                with open(whisper_audio_path, "rb") as audio_file:
                    response_data = client.audio.transcriptions.create(
                        model=WHISPER_FALLBACK_MODEL,
                        file=audio_file,
                        prompt=WHISPER_INITIAL_PROMPT,
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
                    if clean_text:
                        time_badge = f"[{cls.format_timestamp(start_sec)} - {cls.format_timestamp(end_sec)}]"
                        formatted_lines.append(f"{time_badge} {clean_text}")

                raw_transcript = "\n".join(formatted_lines)
                return cls.clean_verbatim_transcript(raw_transcript)

            raw_text = getattr(response_data, "text", "") if hasattr(response_data, "text") else (response_data.get("text", "") if isinstance(response_data, dict) else str(response_data))
            return raw_text.strip() if raw_text else "[Nuk u detektua zë i kuptueshëm në këtë regjistrim.]"

        except Exception as e:
            logger.error(f"❌ Transcription Exception: {e}")
            return f"[Gabim gjatë transkriptimit: {str(e)}]"
        finally:
            if created_temp and os.path.exists(whisper_audio_path):
                try:
                    os.remove(whisper_audio_path)
                except Exception:
                    pass

    @classmethod
    async def process_and_index_media_async(
        cls,
        db: Any,
        media_id_str: str,
        file_path: str,
        user_id_str: str,
        case_id_str: str,
        file_name: str,
        is_video: bool,
        case_domain: Optional[str] = None
    ):
        media_oid = ObjectId(media_id_str)
        try:
            logger.info(f"🎙️ [Media Forensics] Duke filluar transkriptimin: {file_name}")
            role = RoleGuardService.get_role_from_case(case_id_str, db)
            
            # Zbardhja e audios me Whisper
            transcript = await asyncio.to_thread(cls.transcribe_audio_file, file_path)

            # 1. Ruajtja e transkriptit zyrtar në MongoDB
            db.media_evidence.update_one(
                {"_id": media_oid},
                {"$set": {
                    "transcript": transcript,
                    "status": "READY",
                    "role": role,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )

            # 2. Indeksimi në RAG si Provë Materiale me Sekonda
            media_type_label = "VIDEO-REGJISTRIM" if is_video else "FONOGRAM / AUDIO"
            role_trace = RoleGuardService.build_role_trace(role, user_id_str, case_domain)
            
            combined_rag_text = (
                f"{role_trace}\n"
                f"PROVË MATERIALE ({media_type_label}): {file_name}\n"
                f"Lëmia: {case_domain or 'E PAZBULUAR'}\n"
                f"Roli: {role}\n\n"
                f"TRANSKRIPTI ZYRTAR VERBATIM ME SEKONDA [MM:SS - MM:SS]:\n"
                f"{transcript}\n"
            )

            create_and_store_embeddings_from_chunks(
                user_id=user_id_str,
                document_id=media_id_str,
                case_id=case_id_str,
                file_name=f"Media: {file_name}",
                chunks=[combined_rag_text],
                metadatas=[{
                    'file_name': f"Media: {file_name}",
                    'category': 'audio_evidence',
                    'evidence_type': 'material_evidence',
                    'is_physical_evidence': True,
                    'case_domain': case_domain or 'UNKNOWN',
                    'role': role
                }]
            )
            logger.info(f"✅ [Media Forensics] U indeksua me sukses në RAG: {file_name}!")

        except Exception as e:
            logger.error(f"❌ [Media Forensics] Dështoi për {file_name}: {e}")
            db.media_evidence.update_one(
                {"_id": media_oid},
                {"$set": {"status": "FAILED", "transcript": f"Dështoi transkriptimi: {str(e)}"}}
            )
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

    @classmethod
    def process_and_index_media(cls, *args, **kwargs):
        try:
            asyncio.run(cls.process_and_index_media_async(*args, **kwargs))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cls.process_and_index_media_async(*args, **kwargs))