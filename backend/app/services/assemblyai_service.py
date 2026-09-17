# FILE: backend/app/services/assemblyai_service.py
# PHOENIX PROTOCOL - ASSEMBLYAI TRANSCRIPTION SERVICE V1.0
# Migruar nga forensic_audio_service.py (V4.1) për CaseView.
# Ofron: upload, diarizim (me shqip të detyruar), polling, formatim.
# NUK ka varësi nga forenzik / DeepSeek.

import os
import time
import json
import logging
import requests
from typing import Dict, Any, List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com/v2"


# ────────────────────────────────────────────────────────────────────────────
# HEADERS
# ────────────────────────────────────────────────────────────────────────────

def _get_assemblyai_headers() -> Dict[str, str]:
    api_key = (
        getattr(settings, "ASSEMBLYAI_API_KEY", "")
        or os.getenv("ASSEMBLYAI_API_KEY", "")
    )
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY nuk është konfiguruar në server.")
    return {
        "authorization": api_key.strip(),
        "content-type": "application/json",
    }


# ────────────────────────────────────────────────────────────────────────────
# 1. UPLOAD
# ────────────────────────────────────────────────────────────────────────────

def upload_audio_to_assemblyai(audio_bytes: bytes) -> str:
    """Ngarkon skedarin audio në AssemblyAI dhe kthen upload_url."""
    headers = {"authorization": _get_assemblyai_headers()["authorization"]}
    response = requests.post(
        f"{ASSEMBLYAI_BASE_URL}/upload",
        headers=headers,
        data=audio_bytes,
        timeout=180,
    )
    if response.status_code >= 400:
        error_body = response.text
        logger.error(
            f"❌ [AssemblyAI Upload] Status {response.status_code}: {error_body}"
        )
        raise RuntimeError(
            f"AssemblyAI Upload {response.status_code}: {error_body}"
        )

    upload_url = response.json().get("upload_url")
    if not upload_url:
        raise RuntimeError("AssemblyAI nuk ktheu upload_url.")
    logger.info(f"✅ [AssemblyAI Upload] Success: {upload_url[:80]}...")
    return upload_url


# ────────────────────────────────────────────────────────────────────────────
# 2. SUBMIT (DIARIZIM + SHQIP)
# ────────────────────────────────────────────────────────────────────────────

def submit_diarization_job(audio_url: str) -> str:
    """
    Nis transkriptimin me Diarizim.
    Forcon gjuhën shqipe (language_code='sq') për të shmangur
    klasifikim të gabuar (p.sh. Turqisht për shkak të fonetikës).
    """
    headers = _get_assemblyai_headers()
    payload = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "language_code": "sq",
    }

    logger.info(f"🎙️ [AssemblyAI] Payload: {json.dumps(payload)}")

    response = requests.post(
        f"{ASSEMBLYAI_BASE_URL}/transcript",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        error_body = response.text
        logger.error(
            f"❌ [AssemblyAI Submit] Status {response.status_code}: {error_body}"
        )
        raise RuntimeError(
            f"AssemblyAI Submit {response.status_code}: {error_body}"
        )

    response_data = response.json()
    job_id = response_data.get("id")
    if not job_id:
        raise RuntimeError(f"AssemblyAI nuk ktheu job ID: {response_data}")

    logger.info(f"✅ [AssemblyAI Submit] Job ID: {job_id} (language=sq)")
    return job_id


# ────────────────────────────────────────────────────────────────────────────
# 3. POLL
# ────────────────────────────────────────────────────────────────────────────

def poll_transcript_status(
    transcript_id: str, timeout_sec: int = 360
) -> Dict[str, Any]:
    """Pret derisa transkriptimi dhe diarizimi të përfundojnë me sukses."""
    headers = _get_assemblyai_headers()
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
        response = requests.get(
            f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}",
            headers=headers,
            timeout=30,
        )
        if response.status_code >= 400:
            error_body = response.text
            logger.error(
                f"❌ [AssemblyAI Poll] Status {response.status_code}: {error_body}"
            )
            raise RuntimeError(
                f"AssemblyAI Poll {response.status_code}: {error_body}"
            )

        data = response.json()
        status = data.get("status")

        if status == "completed":
            return data
        elif status == "error":
            error_msg = data.get("error", "Transkriptimi dështoi.")
            raise RuntimeError(f"AssemblyAI dështoi: {error_msg}")

        time.sleep(3.0)

    raise TimeoutError(
        f"Transkriptimi në AssemblyAI tejkaloi limitin kohor prej {timeout_sec}s."
    )


# ────────────────────────────────────────────────────────────────────────────
# 4. FORMATIM ME FOLËS DHE SEKONDA
# ────────────────────────────────────────────────────────────────────────────

def format_diarized_transcript(
    assembly_data: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Krijon transkriptin e saktë gjyqësor me folësit (FOLËSI_A, FOLËSI_B)
    dhe sekondat e sakta për secilën deklaratë.

    Returns:
        (full_transcript_str, structured_segments, [])
    """
    utterances = assembly_data.get("utterances", [])

    formatted_lines: List[str] = []
    structured_segments: List[Dict[str, Any]] = []

    if utterances:
        for u in utterances:
            start_sec = int(u.get("start", 0) / 1000)
            end_sec = int(u.get("end", 0) / 1000)
            speaker = f"FOLËSI_{u.get('speaker', '?')}"
            text = u.get("text", "").strip()

            time_str = (
                f"[{start_sec // 60:02d}:{start_sec % 60:02d} - "
                f"{end_sec // 60:02d}:{end_sec % 60:02d}]"
            )
            formatted_lines.append(f"{time_str} {speaker}: {text}")

            structured_segments.append({
                "speaker": speaker,
                "start": start_sec,
                "end": end_sec,
                "timestamp_label": time_str,
                "text": text,
            })
    else:
        text = assembly_data.get("text", "").strip()
        formatted_lines.append(text)
        structured_segments.append({
            "speaker": "FOLËSI_A",
            "start": 0,
            "end": 0,
            "timestamp_label": "[00:00]",
            "text": text,
        })

    full_transcript_str = "\n".join(formatted_lines)
    return full_transcript_str, structured_segments, []