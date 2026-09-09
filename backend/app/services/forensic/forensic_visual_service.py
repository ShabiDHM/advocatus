# FILE: backend/app/services/forensic/forensic_visual_service.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED VISUAL & CCTV VIDEO ENGINE V2.1 (CLEAN PROFESSIONAL TONE)

import os
import io
import json
import base64
import logging
import tempfile
import subprocess
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS

from app.core.config import settings
from .forensic_llm_service import call_forensic_llm

logger = logging.getLogger(__name__)

GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

# ==========================================================
# 1. EXIF & GPS EXTRACTION (FOTO DHE METADATA)
# ==========================================================
def _convert_to_degrees(value) -> Optional[float]:
    try:
        if not value or len(value) < 3:
            return None
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None

def extract_exif_and_gps(image_bytes: bytes) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "camera_make": None,
        "camera_model": None,
        "software_used": None,
        "original_date": None,
        "has_gps": False,
        "latitude": None,
        "longitude": None,
        "google_maps_url": None,
        "raw_tags": {}
    }

    try:
        img = Image.open(io.BytesIO(image_bytes))
        info = img._getexif()
        if not info:
            return metadata

        gps_info = {}
        for tag_id, value in info.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if tag_name == "GPSInfo":
                for key in value:
                    sub_tag = GPSTAGS.get(key, str(key))
                    gps_info[sub_tag] = value[key]
            elif tag_name == "Make":
                metadata["camera_make"] = str(value).strip()
            elif tag_name == "Model":
                metadata["camera_model"] = str(value).strip()
            elif tag_name == "Software":
                metadata["software_used"] = str(value).strip()
            elif tag_name in ["DateTimeOriginal", "DateTime"]:
                metadata["original_date"] = str(value).strip()
            else:
                try:
                    metadata["raw_tags"][tag_name] = str(value)[:100]
                except Exception:
                    pass

        if gps_info:
            lat_ref = gps_info.get("GPSLatitudeRef", "N")
            lat_val = _convert_to_degrees(gps_info.get("GPSLatitude"))
            lon_ref = gps_info.get("GPSLongitudeRef", "E")
            lon_val = _convert_to_degrees(gps_info.get("GPSLongitude"))

            if lat_val is not None and lon_val is not None:
                if lat_ref != "N":
                    lat_val = -lat_val
                if lon_ref != "E":
                    lon_val = -lon_val

                metadata["has_gps"] = True
                metadata["latitude"] = round(lat_val, 6)
                metadata["longitude"] = round(lon_val, 6)
                metadata["google_maps_url"] = f"https://www.google.com/maps?q={lat_val},{lon_val}"

    except Exception as e:
        logger.warning(f"EXIF error: {e}")

    return metadata

# ==========================================================
# 2. ELA TAMPER DETECTION (ANALIZA E MANIPULIMIT TË PIKSELAVE)
# ==========================================================
def calculate_ela_manipulation(image_bytes: bytes, quality: int = 90) -> Dict[str, Any]:
    try:
        orig = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        buffer = io.BytesIO()
        orig.save(buffer, 'JPEG', quality=quality)
        buffer.seek(0)
        resaved = Image.open(buffer)

        diff = ImageChops.difference(orig, resaved)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        scale = 255.0 / max_diff if max_diff != 0 else 1.0
        diff = ImageEnhance.Brightness(diff).enhance(scale)

        diff_bytes = diff.tobytes()
        avg_diff = sum(diff_bytes) / len(diff_bytes)
        manipulation_score = min(100.0, round((avg_diff / 64.0) * 100, 2))
        is_suspicious = manipulation_score > 40.0

        return {
            "manipulation_risk_score": manipulation_score,
            "is_suspicious": is_suspicious,
            "verdict": "I DYSHUAR PËR NDËRHYRJE / MONTAZH" if is_suspicious else "INTEGRITET I QËNDRUESHËM",
            "max_difference_channel": max_diff
        }
    except Exception as e:
        return {
            "manipulation_risk_score": 0.0,
            "is_suspicious": False,
            "verdict": "ANALIZA ELA NUK MUNDI TË EKZEKUTOHET",
            "error": str(e)
        }

# ==========================================================
# 3. GOOGLE CLOUD VISION (ZBULIMI I OBJEKTEVE & ENTITETEVE)
# ==========================================================
def analyze_with_google_vision(image_bytes: bytes) -> Dict[str, Any]:
    api_key = getattr(settings, "GOOGLE_VISION_API_KEY", "") or os.getenv("GOOGLE_VISION_API_KEY", "")
    if not api_key:
        return {"objects": [], "labels": [], "text_detected": ""}

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "requests": [{
            "image": {"content": base64_image},
            "features": [
                {"type": "OBJECT_LOCALIZATION", "maxResults": 15},
                {"type": "LABEL_DETECTION", "maxResults": 15},
                {"type": "TEXT_DETECTION", "maxResults": 5}
            ]
        }]
    }

    try:
        res = requests.post(f"{GOOGLE_VISION_URL}?key={api_key.strip()}", json=payload, timeout=20)
        res.raise_for_status()
        data = res.json()["responses"][0]

        objects = [{"name": it.get("name"), "score": round(it.get("score", 0.0), 2)} for it in data.get("localizedObjectAnnotations", [])]
        labels = [{"description": it.get("description"), "score": round(it.get("score", 0.0), 2)} for it in data.get("labelAnnotations", [])]
        text_full = data.get("fullTextAnnotation", {}).get("text", "")

        return {"objects": objects, "labels": labels, "text_detected": text_full.strip()}
    except Exception as e:
        return {"objects": [], "labels": [], "text_detected": "", "error": str(e)}

# ==========================================================
# 4. FFMPEG KEYFRAME EXTRACTOR (PËR VIDEOT DHE CCTV)
# ==========================================================
def extract_video_keyframes(video_bytes: bytes, interval_sec: int = 15, max_frames: int = 8) -> List[Dict[str, Any]]:
    """
    Përdor FFmpeg për të nxjerrë kornizat kyçe nga videoja në intervale kohore.
    Kthen listën e kornizave me sekonda dhe të dhëna base64.
    """
    temp_video_fd, temp_video_path = tempfile.mkstemp(suffix=".mp4")
    os.close(temp_video_fd)

    with open(temp_video_path, "wb") as f:
        f.write(video_bytes)

    temp_dir = tempfile.mkdtemp(prefix="forensic_frames_")
    frames: List[Dict[str, Any]] = []

    try:
        # Nxjerr 1 kornizë çdo interval_sec sekonda deri në max_frames
        output_pattern = os.path.join(temp_dir, "frame_%03d.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_video_path,
            "-vf", f"fps=1/{interval_sec}",
            "-vframes", str(max_frames),
            "-q:v", "3",
            output_pattern
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, check=True)

        extracted_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_") and f.endswith(".jpg")])

        for idx, filename in enumerate(extracted_files):
            frame_path = os.path.join(temp_dir, filename)
            with open(frame_path, "rb") as ff:
                frame_bytes = ff.read()

            timestamp_sec = idx * interval_sec
            time_str = f"{timestamp_sec // 60:02d}:{timestamp_sec % 60:02d}"

            # Ekzekuto ELA dhe Vision mbi kornizën kyçe
            ela_result = calculate_ela_manipulation(frame_bytes)
            vision_result = analyze_with_google_vision(frame_bytes)

            frames.append({
                "frame_index": idx + 1,
                "timestamp_sec": timestamp_sec,
                "timestamp_label": f"[{time_str}]",
                "tamper_ela": ela_result,
                "vision": vision_result,
                "frame_base64": base64.b64encode(frame_bytes).decode("utf-8")[:1000] # preview token
            })

    except Exception as e:
        logger.error(f"Keyframe extraction error: {e}")
    finally:
        if os.path.exists(temp_video_path):
            try: os.remove(temp_video_path)
            except Exception: pass
        if os.path.exists(temp_dir):
            import shutil
            try: shutil.rmtree(temp_dir)
            except Exception: pass

    return frames

# ==========================================================
# 5. ANALIZA E PLOTË E VIDEOS CCTV
# ==========================================================
def analyze_cctv_video_forensics(
    video_bytes: bytes,
    file_name: str,
    case_context: str = ""
) -> Dict[str, Any]:
    """
    Kryen analizën e videos CCTV: nxjerr kornizat, analizon integritetin dhe gjeneron raport.
    """
    # 1. Nxjerrja e kornizave
    keyframes = extract_video_keyframes(video_bytes, interval_sec=10, max_frames=8)

    # 2. Mesatarja e rrezikut të montazhit
    ela_scores = [f["tamper_ela"].get("manipulation_risk_score", 0.0) for f in keyframes]
    avg_tamper_score = round(sum(ela_scores) / len(ela_scores), 2) if ela_scores else 0.0
    is_video_manipulated = avg_tamper_score > 35.0

    # 3. Përmbledhja e objekteve të identifikuara në të gjitha kornizat
    all_objects = []
    for kf in keyframes:
        for obj in kf.get("vision", {}).get("objects", []):
            label = f"{obj['name']} ({kf['timestamp_label']})"
            if label not in all_objects:
                all_objects.append(label)

    # 4. Analiza ligjore me LLM
    system_prompt = """Ju jeni një ekspert ligjor për analizën e provave video.
Vlerësoni integritetin e videos, identifikoni objektet dhe rindërtoni kronologjinë e ngjarjeve.
Kthejeni përgjigjen në formatin JSON:
{
  "cctv_chronology": [
    {"timestamp": "[00:00]", "description": "Përshkrimi i skenës"}
  ],
  "tamper_verdict": "E PACËNUAR | E DYSHUAR PËR NDËRHYRJE | E MONTAJAR",
  "key_identifications": ["Objekti/Personi 1", "Objekti/Personi 2"],
  "alibi_impact_assessment": "Vlerësimi mbi alibinë",
  "court_admissibility_statement": "Deklarata për gjykatë",
  "expert_summary": "Përmbledhje ekzekutive"
}"""

    user_content = f"""EMRI I VIDEOS: {file_name}
KONTEKSTI I LËNDËS: {case_context or 'Analizë e video-provës'}
REZULTATI I ANALIZËS ELA: {avg_tamper_score}% rrezik ndërhyrjeje
KORNIZAT E ANALIZUARA:
{json.dumps([{'timestamp': k['timestamp_label'], 'objects': k['vision'].get('objects', [])} for k in keyframes], ensure_ascii=False, indent=2)}"""

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
            return {
                "keyframes_count": len(keyframes),
                "keyframes_summary": [{'timestamp': k['timestamp_label'], 'tamper_score': k['tamper_ela']['manipulation_risk_score']} for k in keyframes],
                "avg_tamper_score": avg_tamper_score,
                "is_manipulated": is_video_manipulated,
                "detected_entities": all_objects[:15],
                "forensic_report": parsed,
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception:
        pass

    return {
        "keyframes_count": len(keyframes),
        "avg_tamper_score": avg_tamper_score,
        "is_manipulated": is_video_manipulated,
        "detected_entities": all_objects[:15],
        "forensic_report": {
            "cctv_chronology": [],
            "tamper_verdict": "E PACËNUAR",
            "key_identifications": all_objects[:5],
            "alibi_impact_assessment": "Kërkohet shqyrtim i mëtejshëm.",
            "court_admissibility_statement": "Prova vizuale është proceduar.",
            "expert_summary": raw_response
        },
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }

# ==========================================================
# 6. FUNKSIONI MASTER PËR FOTO/IMAZHE
# ==========================================================
def process_visual_evidence(image_bytes: bytes, case_context: str = "") -> Dict[str, Any]:
    exif_data = extract_exif_and_gps(image_bytes)
    ela_data = calculate_ela_manipulation(image_bytes)
    vision_data = analyze_with_google_vision(image_bytes)

    system_prompt = """Ju jeni një ekspert ligjor për analizën e provave fotografike.
Vlerësoni autenticitetin, metadatat dhe objektet sipas legjislacionit të Kosovës.
Kthejeni përgjigjen në formatin JSON me fushat: authenticity_assessment, key_findings, chain_of_custody_impact, court_defense_strategy, expert_statement."""

    user_content = f"Të dhënat EXIF: {json.dumps(exif_data)}\nELA: {json.dumps(ela_data)}\nVision: {json.dumps(vision_data)}"
    raw = call_forensic_llm(system_prompt=system_prompt, user_content=user_content, json_mode=True, temperature=0.0)

    try:
        from app.services.llm.llm_client import clean_and_parse_json
        opinion = clean_and_parse_json(raw) or {"expert_statement": raw}
    except Exception:
        opinion = {"expert_statement": raw}

    return {
        "exif_metadata": exif_data,
        "tamper_analysis": ela_data,
        "vision_detection": vision_data,
        "forensic_opinion": opinion,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }