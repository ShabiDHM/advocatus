# FILE: backend/app/services/video_forensic_service.py
# PHOENIX PROTOCOL - VIDEO FORENSIC VISION SERVICE V1.0 (LICENSE PLATES • OCR TIMESTAMPS • ACTION LOG)

import os
import json
import base64
import logging
import tempfile
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
VISION_MODEL = "google/gemini-2.5-flash-lite"
VISION_FALLBACK_MODEL = "qwen/qwen-2.5-vl-72b-instruct"

def _get_api_key() -> str:
    return getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")

def _get_async_client() -> AsyncOpenAI:
    key = _get_api_key()
    return AsyncOpenAI(api_key=key, base_url=OPENROUTER_URL, timeout=90.0)

def extract_video_keyframes(video_path: str, max_frames: int = 16, interval_seconds: int = 2) -> List[Dict[str, Any]]:
    """
    Nxjerr kuadrot (fotot) kryesore nga skedari video me FFmpeg në mënyrë të shpejtë dhe pa ngarkuar memorien.
    Kthen një listë objektesh: [{'timestamp_str': '00:04', 'base64_data': '...'}]
    """
    frames_data = []
    temp_dir = tempfile.mkdtemp(prefix="video_frames_")

    try:
        # Përdor FFmpeg për të nxjerrë 1 kuadër çdo 'interval_seconds'
        output_pattern = os.path.join(temp_dir, "frame_%04d.jpg")
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", f"fps=1/{interval_seconds},scale=640:-1",  # Zvogëlon madhësinë për shpejtësi maksimale
            "-q:v", "4",
            output_pattern
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
        
        frame_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_") and f.endswith(".jpg")])
        
        # Kufizon deri në 'max_frames' për të mos tejkaluar tokenët
        step = max(1, len(frame_files) // max_frames)
        selected_files = frame_files[::step][:max_frames]

        for idx, fname in enumerate(selected_files):
            fpath = os.path.join(temp_dir, fname)
            sec_offset = idx * interval_seconds * step
            minutes = sec_offset // 60
            seconds = sec_offset % 60
            time_str = f"{minutes:02d}:{seconds:02d}"

            with open(fpath, "rb") as img_file:
                b64_str = base64.b64encode(img_file.read()).decode("utf-8")
                frames_data.append({
                    "timestamp_str": time_str,
                    "seconds": sec_offset,
                    "base64_data": b64_str
                })

    except Exception as e:
        logger.warning(f"⚠️ FFmpeg keyframe extraction fallback/error: {e}")
    finally:
        # Fshin skedarët e përkohshëm
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except Exception:
            pass

    return frames_data

class VideoForensicService:
    """
    Shërbimi Forenzik i Analizës së Video-Provave.
    Zbulon automatikisht targat, orën e kamerave CCTV, personat dhe veprimet me vlerë ligjore.
    """

    async def analyze_video_evidence_async(self, video_path: str, file_name: str) -> Dict[str, Any]:
        if not os.path.exists(video_path):
            return {"error": "Skedari video nuk ekziston."}

        key = _get_api_key()
        if not key:
            return {"error": "Mungon API Key."}

        # 1. Nxjerrja e kuadrove me sekonda
        keyframes = await asyncio.to_thread(extract_video_keyframes, video_path, max_frames=16, interval_seconds=2)
        if not keyframes:
            return {
                "visual_summary": "Nuk u mundësua nxjerrja e kuadrove vizuale nga ky format video.",
                "video_forensic_log": [],
                "detected_plates": [],
                "detected_actions": []
            }

        client = _get_async_client()

        # 2. Ndërtimi i mesazhit multimodal për Vision AI
        system_prompt = """
        Ti je Krye-Eksperti i Forenzikës Vizuale të Video-Provave për Gjykatat dhe Prokuroritë e Kosovës.
        DETYRA JOTE: Analizo këtë sekuencë kuadrosh me sekonda nga videoja e depozituar si provë materiale.

        EKSTRAKTO ME PRECIZION:
        1. TARGAT DHE AUTOMJETET (License Plates): Nxjerr çdo targë të lexueshme, llojin dhe ngjyrën e veturës.
        2. KOHA DHE DATA NË EKRAN (CCTV Clock): Nëse në kuadër ka orë të stampuar nga kamera, lexoje saktësisht.
        3. PERSONAT DHE VESHJA: Numri i personave, përshkrimi vizual dhe veprimet e tyre.
        4. VEPRIMET ME RELEVANCË LIGJORE: Incidentet fizike, shtytjet, lëvizjet agresive, dorëzimi i sendeve/parave, shenjat e frikësimit.

        Përgjigju VETËM në formatin JSON të pastër:
        {
          "visual_summary": "Përmbledhja e përgjithshme ekzekutive e asaj që dëshmohet në video në gjuhën shqipe.",
          "detected_license_plates": [
            { "timestamp": "00:14", "plate_number": "01-123-AB", "vehicle_description": "Golf 7 e zezë" }
          ],
          "video_forensic_log": [
            {
              "timestamp_video": "00:04",
              "cctv_clock": "14:02:11",
              "event_type": "LËVIZJE_PERSONASH | VEHIKËL | INCIDENT_FIZIK | VEPRIM_I_DYSHIMTË",
              "visual_evidence": "Përshkrimi i saktë i asaj që shihet në kuadër në Shqip",
              "evidentiary_value": "Vlera provuese për procedurën gjyqësore"
            }
          ]
        }
        """

        user_content_payload: List[Dict[str, Any]] = [
            {"type": "text", "text": f"VIDEO-PROVA (Emri: {file_name}). Analizo kuadrot e mëposhtme të nxjerra me sekonda:"}
        ]

        for kf in keyframes:
            user_content_payload.append({
                "type": "text",
                "text": f"--- KUADRI NË SEKONDËN [{kf['timestamp_str']}] ---"
            })
            user_content_payload.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{kf['base64_data']}"
                }
            })

        # 3. Thirrja e Modelit Vision në OpenRouter
        try:
            res = await client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content_payload}
                ],
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            raw_text = res.choices[0].message.content or "{}"
            parsed = json.loads(raw_text)
            return parsed
        except Exception as e:
            logger.error(f"❌ Video Vision Forensic Analysis Error ({VISION_MODEL}): {e}")
            return {
                "visual_summary": "Dështoi analiza automatike vizuale e videos.",
                "video_forensic_log": [],
                "error": str(e)
            }

video_forensic_service = VideoForensicService()