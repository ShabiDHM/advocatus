# FILE: backend/app/services/forensic/forensic_visual_service.py
# PHOENIX PROTOCOL - FORENSIC VISUAL INTELLIGENCE V1.0 (EXIF/GPS • ELA TAMPER DETECTION • GOOGLE VISION • CLAUDE)

import os
import io
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS

from app.core.config import settings
from .forensic_llm_service import call_forensic_llm

logger = logging.getLogger(__name__)

GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"

# --- 1. EXIF DHE GPS EXTRACTION ---
def _convert_to_degrees(value) -> Optional[float]:
    """Konverton koordinatat GPS nga formati DMS në shkallë decimale."""
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
    """Nxjerr të gjitha të dhënat e fshehura EXIF dhe lokacionin GPS."""
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

        # GPS Processing
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
        logger.warning(f"⚠️ Dështoi leximi i EXIF: {e}")

    return metadata

# --- 2. ERROR LEVEL ANALYSIS (ELA) PËR ZBULIMIN E MANIPULIMIT ---
def calculate_ela_manipulation(image_bytes: bytes, quality: int = 90) -> Dict[str, Any]:
    """
    Kryen analizën e nivelit të gabimit (ELA).
    Dallon pikselat e modifikuar (Photoshop/Deepfake) nga ata origjinalë.
    """
    try:
        orig = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Ri-ruajmë imazhin në memorje me një cilësi të caktuar kompresimi JPEG
        buffer = io.BytesIO()
        orig.save(buffer, 'JPEG', quality=quality)
        buffer.seek(0)
        resaved = Image.open(buffer)

        # Llogarisim ndryshimin absolut midis origjinalit dhe versionit të ri-kompresuar
        diff = ImageChops.difference(orig, resaved)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        scale = 255.0 / max_diff if max_diff != 0 else 1.0
        diff = ImageEnhance.Brightness(diff).enhance(scale)

        # Llogarisim mesataren e ndryshimit për të nxjerrë një risk score (0-100)
        diff_bytes = diff.tobytes()
        avg_diff = sum(diff_bytes) / len(diff_bytes)
        
        # Risk Score empirik forenzik
        manipulation_score = min(100.0, round((avg_diff / 64.0) * 100, 2))
        is_suspicious = manipulation_score > 40.0

        return {
            "manipulation_risk_score": manipulation_score,
            "is_suspicious": is_suspicious,
            "verdict": "I DYSHUAR PËR NDËRHYRJE / MONTAZH" if is_suspicious else "INTEGRITET I QËNDRUESHËM",
            "max_difference_channel": max_diff
        }
    except Exception as e:
        logger.warning(f"⚠️ ELA nuk u llogarit dot: {e}")
        return {
            "manipulation_risk_score": 0.0,
            "is_suspicious": False,
            "verdict": "ANALIZA ELA NUK MUNDI TË EKZEKUTOHET",
            "error": str(e)
        }

# --- 3. GOOGLE CLOUD VISION API (ZBULIMI I OBJEKTEVE & VEGLAVE) ---
def analyze_with_google_vision(image_bytes: bytes) -> Dict[str, Any]:
    """Dërgon imazhin te Google Vision API për zbulim objektesh, armësh, dhe teksti."""
    api_key = getattr(settings, "GOOGLE_VISION_API_KEY", "") or os.getenv("GOOGLE_VISION_API_KEY", "")
    if not api_key:
        logger.info("GOOGLE_VISION_API_KEY mungon. Po kalohet pa Google Vision.")
        return {"objects": [], "labels": [], "text_detected": ""}

    import base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": base64_image},
                "features": [
                    {"type": "OBJECT_LOCALIZATION", "maxResults": 15},
                    {"type": "LABEL_DETECTION", "maxResults": 15},
                    {"type": "TEXT_DETECTION", "maxResults": 5},
                    {"type": "SAFE_SEARCH_DETECTION"}
                ]
            }
        ]
    }

    try:
        res = requests.post(f"{GOOGLE_VISION_URL}?key={api_key.strip()}", json=payload, timeout=25)
        res.raise_for_status()
        data = res.json()
        response_data = data["responses"][0]

        objects = [
            {"name": item.get("name"), "score": round(item.get("score", 0.0), 2)}
            for item in response_data.get("localizedObjectAnnotations", [])
        ]
        labels = [
            {"description": item.get("description"), "score": round(item.get("score", 0.0), 2)}
            for item in response_data.get("labelAnnotations", [])
        ]
        text_full = response_data.get("fullTextAnnotation", {}).get("text", "")

        return {
            "objects": objects,
            "labels": labels,
            "text_detected": text_full.strip()
        }
    except Exception as e:
        logger.warning(f"⚠️ Google Vision API Error: {e}")
        return {"objects": [], "labels": [], "text_detected": "", "error": str(e)}

# --- 4. EKSPERTIZA E THELLË ME CLAUDE SONNET 4.6 ---
def generate_visual_forensic_opinion(
    exif_data: Dict[str, Any],
    ela_data: Dict[str, Any],
    vision_data: Dict[str, Any],
    case_context: str = ""
) -> Dict[str, Any]:
    """Përpilon ekspertizën forenzike gjyqësore me Claude Sonnet 4.6."""
    system_prompt = """EKSPERTIZA FORENZIKE E PROVAVE VIZUALE DHE ELEKTRONIKE (CLAUDE SONNET 4.6):
Ju jeni Eksperti Kriminalistik i Provave Digjitale i autorizuar nga Gjykata.
Detyra juaj:
1. Vlerësoni autenticitetin e provës bazuar në EXIF, ELA (manipulim), dhe objektet e zbuluara.
2. Nëse 'software_used' tregon Photoshop apo mjete redaktimi, theksoni rrezikun e manipulimit.
3. Nëse ka koordinata GPS, vlerësoni rëndësinë e vendndodhjes së ngjarjes.
4. Jepni konkluzionin e qartë për përdorim në proces penal apo civil sipas Kodit të Procedurës Penale të Kosovës.

Kthe përgjigjen VETËM në format JSON:
{
  "authenticity_assessment": "E BESUESHME | E DYSHUAR | E MANIPULUAR",
  "key_findings": ["Gjetja 1", "Gjetja 2"],
  "chain_of_custody_impact": "Vlerësim mbi paprekshmërinë e provës",
  "court_defense_strategy": "Këshillë taktike për pranimin ose refuzimin e provës në gjykatë",
  "expert_statement": "Deklarata përfundimtare formale e ekspertit ligjor"
}"""

    user_content = f"""KONTEKSTI I ÇËSHTJES:
{case_context or 'Ekspertizë e pavarur forenzike'}

TË DHËNAT EXIF & GPS:
{json.dumps(exif_data, ensure_ascii=False, indent=2)}

ANALIZA E MANIPULIMIT (ELA):
{json.dumps(ela_data, ensure_ascii=False, indent=2)}

OBJEKTET DHE TEKSTI I DETEKTUAR:
{json.dumps(vision_data, ensure_ascii=False, indent=2)}"""

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
        "authenticity_assessment": "E DYSHUAR",
        "key_findings": ["Përgjigja u procedua."],
        "chain_of_custody_impact": "Kërkohet verifikim shtesë manual.",
        "court_defense_strategy": "Kërkoni ekspertizë shtesë në seancë.",
        "expert_statement": raw_response
    }

def process_visual_evidence(image_bytes: bytes, case_context: str = "") -> Dict[str, Any]:
    """Orkestron të gjithë procesin e analizës vizuale forenzike."""
    exif_data = extract_exif_and_gps(image_bytes)
    ela_data = calculate_ela_manipulation(image_bytes)
    vision_data = analyze_with_google_vision(image_bytes)
    opinion = generate_visual_forensic_opinion(exif_data, ela_data, vision_data, case_context)

    return {
        "exif_metadata": exif_data,
        "tamper_analysis": ela_data,
        "vision_detection": vision_data,
        "forensic_opinion": opinion,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }