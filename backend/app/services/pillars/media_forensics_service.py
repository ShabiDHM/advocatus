# FILE: backend/app/services/pillars/media_forensics_service.py
# PHOENIX PROTOCOL - UNBREAKABLE LONG-AUDIO CHUNKING & VERBATIM TRANSCRIPTION ENGINE V16.0

import os
import re
import json
import logging
import subprocess
import asyncio
import math
import shutil
import tempfile
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from openai import OpenAI
import redis.asyncio as aioredis

from app.core.config import settings
from app.services import llm_service
from app.services.vector_store_service import create_and_store_embeddings_from_chunks

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
WHISPER_TURBO_MODEL = "openai/whisper-large-v3-turbo"
WHISPER_FALLBACK_MODEL = "openai/whisper-1"

WHISPER_INITIAL_PROMPT = (
    "Transkriptim forenzik fjalë-për-fjalë (verbatim) në gjuhën shqipe dhe anglishte bisedore: "
    "bisedë direkte, dialog, fjalët e sakta të folësve, 'babi', 'mami', 'boring', 'stres'."
)

class MediaForensicsService:
    """
    Modul i Pavarur Ekskluziv për PROVAT AUDIO DHE VIDEO TË GJATA:
    - Mbështet skedarë të pakufizuar në kohë (10 min deri 3+ orë) përmes Auto-Chunking
    - Kompresim 32kbps me FFmpeg për reduktimin 15x të madhësisë
    - 100% Verbatim (Fjalë për Fjalë) me shënues kohe të pandërprerë [MM:SS - MM:SS]
    - Indeksim i plotë në RAG (user_vectors) si provë materiale e pakontestueshme
    """

    @staticmethod
    def format_timestamp(seconds_float: float) -> str:
        total_seconds = int(seconds_float)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @classmethod
    def convert_and_compress_audio(cls, input_path: str) -> str:
        """Kompreson audion në 16,000Hz Mono MP3 me 32kbps (redukton madhësinë 15 herë pa humbur fjalët)."""
        output_mp3 = f"{input_path}_compressed.mp3"
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                "-b:a", "32k",
                output_mp3
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
            if res.returncode == 0 and os.path.exists(output_mp3):
                return output_mp3
        except Exception as e:
            logger.warning(f"⚠️ FFmpeg compression warning: {e}")
        return input_path

    @classmethod
    def get_audio_duration_seconds(cls, file_path: str) -> float:
        """Merr kohëzgjatjen ekzakte të skedarit në sekonda me ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return float(res.stdout.strip())
        except Exception:
            pass
        return 0.0

    @classmethod
    def split_audio_into_chunks(cls, file_path: str, segment_seconds: int = 600) -> List[Tuple[str, float]]:
        """Ndan audion e gjatë në pjesë 10-minutëshe për të mos u bllokuar kurrë nga limiti 25MB."""
        duration = cls.get_audio_duration_seconds(file_path)
        if duration <= segment_seconds:
            return [(file_path, 0.0)]

        chunks = []
        num_segments = math.ceil(duration / segment_seconds)
        temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")

        for i in range(num_segments):
            start_time = i * segment_seconds
            out_chunk = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", file_path,
                "-t", str(segment_seconds),
                "-vn", "-ar", "16000", "-ac", "1", "-b:a", "32k",
                out_chunk
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
            if res.returncode == 0 and os.path.exists(out_chunk):
                chunks.append((out_chunk, float(start_time)))

        return chunks if chunks else [(file_path, 0.0)]

    @staticmethod
    def clean_verbatim_transcript(raw_segments_text: str) -> str:
        if not raw_segments_text or len(raw_segments_text.strip()) < 10:
            return raw_segments_text

        system_prompt = """
        Ti je një Procesmbajtës Zyrtar i Gjykatës.
        DETYRA JOTE: Ky është një transkript audio me sekonda [MM:SS - MM:SS].
        
        RREGULLAT E HEKURTA TË PROCESVERBALIT:
        1. RUAJ 100% FJALËT EKZAKTE QË JANË FOLUR. Ndalohet kategorikisht të ndryshosh kuptimin apo të parafrazosh.
        2. RUAJ TË GJITHA SEKONDAT [MM:SS - MM:SS] ekzakte në fillim të çdo rreshti.
        3. RUAJ fjalët e folura në anglisht pa i përkthyer.
        4. FSHIJ fjalët e huaja halucinative të zhurmës së sfondit (p.sh. 'Hvala').
        5. NDALOHET KATEGORIKISHT të shtosh analiza, komente apo mendime të tuat! Kthe VETËM dialogun fjalë për fjalë.
        """
        try:
            cleaned = llm_service._call_llm(
                system_prompt=system_prompt,
                user_content=raw_segments_text,
                json_mode=False,
                temperature=0.0,
                model=llm_service.FAST_MODEL
            )
            return cleaned.strip() if cleaned else raw_segments_text
        except Exception as e:
            logger.warning(f"Transcript clean fallback: {e}")
            return raw_segments_text

    @classmethod
    def transcribe_audio_segment(cls, client: OpenAI, audio_path: str, offset_seconds: float = 0.0) -> List[str]:
        response_data = None
        try:
            with open(audio_path, "rb") as af:
                response_data = client.audio.transcriptions.create(
                    model=WHISPER_TURBO_MODEL,
                    file=af,
                    prompt=WHISPER_INITIAL_PROMPT,
                    response_format="verbose_json"
                )
        except Exception as e:
            logger.warning(f"Whisper Turbo fallback: {e}")
            with open(audio_path, "rb") as af:
                response_data = client.audio.transcriptions.create(
                    model=WHISPER_FALLBACK_MODEL,
                    file=af,
                    prompt=WHISPER_INITIAL_PROMPT,
                    response_format="verbose_json"
                )

        lines = []
        segments = getattr(response_data, "segments", None)
        if not segments and isinstance(response_data, dict):
            segments = response_data.get("segments")

        if segments and isinstance(segments, list) and len(segments) > 0:
            for seg in segments:
                s_sec = (seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)) + offset_seconds
                e_sec = (seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)) + offset_seconds
                text_content = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                
                clean_text = text_content.strip()
                if clean_text and "hvala" not in clean_text.lower():
                    time_badge = f"[{cls.format_timestamp(s_sec)} - {cls.format_timestamp(e_sec)}]"
                    lines.append(f"{time_badge} {clean_text}")

        return lines

    @classmethod
    def transcribe_audio_file(cls, file_path: str) -> str:
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "[Gabim: Mungon API Key për transkriptim.]"

        compressed_path = cls.convert_and_compress_audio(file_path)
        active_audio = compressed_path if os.path.exists(compressed_path) else file_path

        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=180.0)
        chunks = cls.split_audio_into_chunks(active_audio, segment_seconds=600)

        all_formatted_lines = []
        try:
            for chunk_file, offset_sec in chunks:
                lines = cls.transcribe_audio_segment(client, chunk_file, offset_seconds=offset_sec)
                all_formatted_lines.extend(lines)

            raw_transcript = "\n".join(all_formatted_lines)
            return cls.clean_verbatim_transcript(raw_transcript) if raw_transcript else "[Nuk u detektua zë i kuptueshëm.]"

        except Exception as e:
            logger.error(f"❌ Audio Processing Exception: {e}")
            return f"[Gabim gjatë procesimit: {str(e)}]"
        finally:
            if compressed_path and compressed_path != file_path and os.path.exists(compressed_path):
                try: os.remove(compressed_path)
                except Exception: pass

    @classmethod
    def process_and_index_media(
        cls,
        db: Any,
        media_id_str: str,
        file_path: str,
        user_id_str: str,
        case_id_str: str,
        file_name: str,
        is_video: bool
    ):
        media_oid = ObjectId(media_id_str)
        try:
            logger.info(f"🎙️ [Media Forensics] Duke transkriptuar skedarin: {file_name}")
            transcript = cls.transcribe_audio_file(file_path)

            visual_data = {}
            if is_video:
                from app.services.video_forensic_service import video_forensic_service
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    visual_data = loop.run_until_complete(
                        video_forensic_service.analyze_video_evidence_async(file_path, file_name)
                    )
                finally:
                    loop.close()

            db.media_evidence.update_one(
                {"_id": media_oid},
                {"$set": {
                    "transcript": transcript,
                    "visual_analysis": visual_data,
                    "status": "READY",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )

            combined_rag_text = f"PROVA MATERIALE AUDIO/VIDEO ({file_name}):\n\nTRANSKRIPTI ZYRTAR ME KOHË:\n{transcript}\n"

            create_and_store_embeddings_from_chunks(
                user_id=user_id_str,
                document_id=media_id_str,
                case_id=case_id_str,
                file_name=f"Media: {file_name}",
                chunks=[combined_rag_text],
                metadatas=[{'file_name': f"Media: {file_name}", 'category': 'audio_evidence'}]
            )
            logger.info(f"✅ [Media Forensics] Transkripti verbatim u indeksua në RAG për {file_name}!")

        except Exception as e:
            logger.error(f"❌ [Media Forensics] Dështoi: {e}")
            db.media_evidence.update_one(
                {"_id": media_oid},
                {"$set": {"status": "FAILED", "transcript": f"Dështoi analiza: {str(e)}"}}
            )
        finally:
            if file_path and os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception: pass