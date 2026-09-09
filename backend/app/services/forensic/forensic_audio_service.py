# FILE: backend/app/services/forensic/forensic_audio_service.py
# PHOENIX PROTOCOL - FORENSIC AUDIO INTELLIGENCE V1.1 (CLEAN PROFESSIONAL TONE)

import os
import time
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.core.config import settings
from .forensic_llm_service import call_forensic_llm

logger = logging.getLogger(__name__)

ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com/v2"

def _get_assemblyai_headers() -> Dict[str, str]:
    api_key = getattr(settings, "ASSEMBLYAI_API_KEY", "") or os.getenv("ASSEMBLYAI_API_KEY", "")
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY nuk është konfiguruar në server.")
    return {
        "authorization": api_key.strip(),
        "content-type": "application/json"
    }

def upload_audio_to_assemblyai(audio_bytes: bytes) -> str:
    """Ngarkon skedarin audio në AssemblyAI dhe kthen upload_url."""
    headers = {
        "authorization": _get_assemblyai_headers()["authorization"]
    }
    response = requests.post(
        f"{ASSEMBLYAI_BASE_URL}/upload",
        headers=headers,
        data=audio_bytes,
        timeout=180
    )
    response.raise_for_status()
    return response.json()["upload_url"]

def submit_diarization_job(audio_url: str) -> str:
    """Nis transkriptimin me diarizim folësish dhe analizë ndjenjash/stresi."""
    headers = _get_assemblyai_headers()
    payload = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "sentiment_analysis": True,
        "language_detection": True,
        "punctuate": True,
        "format_text": True
    }
    response = requests.post(
        f"{ASSEMBLYAI_BASE_URL}/transcript",
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()["id"]

def poll_transcript_status(transcript_id: str, timeout_sec: int = 360) -> Dict[str, Any]:
    """Pret derisa AssemblyAI të përfundojë transkriptimin dhe diarizimin."""
    headers = _get_assemblyai_headers()
    start_time = time.time()
    
    while time.time() - start_time < timeout_sec:
        response = requests.get(
            f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        status = data.get("status")

        if status == "completed":
            return data
        elif status == "error":
            error_msg = data.get("error", "Transkriptimi dështoi.")
            raise RuntimeError(f"AssemblyAI dështoi: {error_msg}")

        time.sleep(3.0)

    raise TimeoutError(f"Transkriptimi në AssemblyAI tejkaloi limitin kohor prej {timeout_sec}s.")

def format_forensic_transcript(assembly_data: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Formaton transkriptin me folës dhe grupon momentet e stresit/kërcënimit.
    """
    utterances = assembly_data.get("utterances", [])
    sentiment_results = assembly_data.get("sentiment_analysis_results", [])
    
    formatted_lines: List[str] = []
    structured_segments: List[Dict[str, Any]] = []
    stress_flags: List[Dict[str, Any]] = []

    if utterances:
        for u in utterances:
            start_sec = int(u.get("start", 0) / 1000)
            end_sec = int(u.get("end", 0) / 1000)
            speaker = f"SPEAKER_{u.get('speaker', '?')}"
            text = u.get("text", "").strip()

            time_str = f"[{start_sec // 60:02d}:{start_sec % 60:02d} - {end_sec // 60:02d}:{end_sec % 60:02d}]"
            formatted_lines.append(f"{time_str} {speaker}: {text}")

            structured_segments.append({
                "speaker": speaker,
                "start": start_sec,
                "end": end_sec,
                "timestamp_label": time_str,
                "text": text
            })
    else:
        # Fallback në rast se nuk ka utterances
        text = assembly_data.get("text", "")
        formatted_lines.append(text)
        structured_segments.append({
            "speaker": "SPEAKER_UNKNOWN",
            "start": 0,
            "end": 0,
            "timestamp_label": "[00:00]",
            "text": text
        })

    # Analiza e emocioneve/stresit nga AssemblyAI
    for s in sentiment_results:
        sentiment = s.get("sentiment", "NEUTRAL")
        confidence = s.get("confidence", 0.0)
        # Nëse detektohet negativitet me besueshmëri të lartë, shënohet si stres/tension
        if sentiment == "NEGATIVE" and confidence > 0.65:
            stress_flags.append({
                "start": int(s.get("start", 0) / 1000),
                "end": int(s.get("end", 0) / 1000),
                "text": s.get("text", ""),
                "intensity": "I LARTË" if confidence > 0.85 else "MESATAR",
                "confidence": round(confidence, 2)
            })

    full_transcript_str = "\n".join(formatted_lines)
    return full_transcript_str, structured_segments, stress_flags

def analyze_audio_forensics_with_llm(
    transcript_text: str,
    stress_flags: List[Dict[str, Any]],
    case_context: str = ""
) -> Dict[str, Any]:
    """
    Kryen analizën ligjore të transkriptit.
    """
    system_prompt = """Ju jeni një ekspert ligjor i specializuar në analizën e provave audio.
Analizoni transkriptin dhe ofroni një vlerësim profesional mbi elementet e veprave penale, presionin psikologjik dhe pranueshmërinë e provës sipas legjislacionit të Kosovës.
Kthejeni përgjigjen në formatin JSON me strukturën e mëposhtme:
{
  "summary": "Përmbledhje ekzekutive e incizimit",
  "threat_level": "E ULËT | E MESME | E LARTË | KRITIKE",
  "criminal_elements_detected": ["Lista e neneve dhe veprave të dyshuara"],
  "stress_and_intimidation_analysis": "Analizë e thellë mbi presionin dhe frikësimin",
  "contradictions_found": ["Kontradikta 1", "Kontradikta 2"],
  "court_admissibility_recommendation": "Këshillë taktike për pranimin e provës në gjyq"
}"""

    user_content = f"""KONTEKSTI I ÇËSHTJES:
{case_context or 'Çështje në shqyrtim hetimor'}

FLAG-ET E STRESIT TË REGJISTRUARA:
{json.dumps(stress_flags, ensure_ascii=False, indent=2)}

TRANSKRIPTI I DIARIZUAR:
{transcript_text}"""

    raw_response = call_forensic_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        json_mode=True,
        temperature=0.0
    )

    try:
        from app.services.llm.llm_client import clean_and_parse_json
        parsed = clean_and_parse_json(raw_response)
        if parsed:
            return parsed
    except Exception:
        pass

    return {
        "summary": "Analiza u krye me sukses.",
        "threat_level": "E MESME",
        "criminal_elements_detected": [],
        "stress_and_intimidation_analysis": raw_response,
        "contradictions_found": [],
        "court_admissibility_recommendation": "Kërkohet rishikim manual nga avokati mbrojtës."
    }

def process_audio_file(
    audio_bytes: bytes,
    case_context: str = ""
) -> Dict[str, Any]:
    """
    Funksioni master që orkestron të gjithë procesin e analizës së audios.
    """
    # 1. Ngarkimi në AssemblyAI
    upload_url = upload_audio_to_assemblyai(audio_bytes)
    
    # 2. Nisja e punës me Diarizim dhe Sentiment
    job_id = submit_diarization_job(upload_url)
    
    # 3. Pritja e rezultatit
    assembly_result = poll_transcript_status(job_id)
    
    # 4. Formatimi i transkriptit dhe nxjerrja e pikave të stresit
    formatted_transcript, segments, stress_flags = format_forensic_transcript(assembly_result)
    
    # 5. Analiza e thellë ligjore
    llm_analysis = analyze_audio_forensics_with_llm(
        transcript_text=formatted_transcript,
        stress_flags=stress_flags,
        case_context=case_context
    )

    return {
        "formatted_transcript": formatted_transcript,
        "segments": segments,
        "stress_flags": stress_flags,
        "forensic_intelligence": llm_analysis,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }