# FILE: backend/app/services/report_service/helpers.py
# PHOENIX PROTOCOL - REPORT HELPERS & TEXT CLEANERS V2.0 (FIXED NONE TYPO)

import io
import os
import re
import requests
import structlog
from typing import Optional
from bson import ObjectId
from pymongo.database import Database
from PIL import Image as PILImage

from app.services import storage_service
from .styles import TRANSLATIONS, BRAND_COLOR_DEFAULT

logger = structlog.get_logger(__name__)

def clean_text_for_pdf(text: str) -> str:
    """Strips unrenderable emojis, black box glyphs ('■'), stray 'None' values, and translates English markers."""
    if not text:
        return ""
    
    clean = text
    bad_chars = [
        "■", "□", "▪", "▫", "◆", "◇", "●", "○", "★", "☆", "✔", "✓", "✅", "❌", "✖",
        "⚖", "👨", "💼", "⚖️", "👨‍💼", "👨‍⚖️", "🛡", "⚔", "🛡️", "⚔️", "💀", "⏱", "⏱️",
        "⚡", "📁", "📂", "🔍"
    ]
    for char in bad_chars:
        clean = clean.replace(char, "")

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\u2702-\u27B0"
        "\u24C2-\U0001F251"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]+", flags=re.UNICODE
    )
    clean = emoji_pattern.sub("", clean)

    replacements = {
        "Conflict: CRITICAL": "Mospërputhje: KRITIKE",
        "Conflict: HIGH": "Mospërputhje: E LARTË",
        "Conflict: MEDIUM": "Mospërputhje: E MESME",
        "Conflict: LOW": "Mospërputhje: E ULËT",
        "Konflikt: CRITICAL": "Mospërputhje: KRITIKE",
        "Konflikt: HIGH": "Mospërputhje: E LARTË",
        "Konflikt: MEDIUM": "Mospërputhje: E MESME",
        "Konflikt: LOW": "Mospërputhje: E ULËT",
        "Severity: CRITICAL": "Rrezikshmëria: KRITIKE",
        "Severity: HIGH": "Rrezikshmëria: E LARTË",
        "Severity: MEDIUM": "Rrezikshmëria: E MESME",
        "Severity: LOW": "Rrezikshmëria: E ULËT",
        "Rrezikshmëria: CRITICAL": "Rrezikshmëria: KRITIKE",
        "Rrezikshmëria: HIGH": "Rrezikshmëria: E LARTË",
        "Rrezikshmëria: MEDIUM": "Rrezikshmëria: E MESME",
        "Rrezikshmëria: LOW": "Rrezikshmëria: E ULËT",
        "supports": "mbështet",
        "contradicts": "kundërshton",
        "related": "lidhet me",
        "opponent_strategy": "strategjia_e_kundershtarit",
        "weakness_attacks": "pikat_e_sulmit"
    }
    for eng, alb in replacements.items():
        clean = re.sub(r'\b' + re.escape(eng) + r'\b', alb, clean, flags=re.IGNORECASE)

    clean = re.sub(r'^\s*(None|\*\*None\*\*)\s*$', '', clean, flags=re.MULTILINE | re.IGNORECASE)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    
    return clean.strip()

def _get_text(key: str, lang: str = "sq") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["sq"]).get(key, key)

def _get_branding(db: Database, user_id: str) -> dict:
    try:
        try: oid = ObjectId(user_id)
        except: oid = user_id
        
        profile = db.business_profiles.find_one({"user_id": oid})
        if not profile: profile = db.business_profiles.find_one({"user_id": str(user_id)})

        if profile:
            return {
                "firm_name": profile.get("firm_name", "Juristi.tech"), "address": profile.get("address", ""),"email_public": profile.get("email_public", ""), "phone": profile.get("phone", ""),"branding_color": profile.get("branding_color", BRAND_COLOR_DEFAULT), "logo_url": profile.get("logo_url"), "logo_storage_key": profile.get("logo_storage_key"), "website": profile.get("website", ""), "nui": profile.get("tax_id", "") 
            }
    except Exception as e: logger.error(f"Branding fetch failed: {e}")
    return {"firm_name": "Juristi.tech", "branding_color": BRAND_COLOR_DEFAULT}

def _process_image_bytes(data: bytes) -> Optional[io.BytesIO]:
    try:
        img = PILImage.open(io.BytesIO(data))
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'P': img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[3]) 
            img = bg
        elif img.mode != 'RGB': img = img.convert('RGB')
        
        out_buffer = io.BytesIO()
        img.save(out_buffer, format='JPEG', quality=100)
        out_buffer.seek(0)
        return out_buffer
    except Exception as e: logger.error(f"Image processing failed: {e}")
    return None

def _fetch_logo_buffer(url: Optional[str], storage_key: Optional[str] = None) -> Optional[io.BytesIO]:
    if not url and not storage_key: return None
    if url and "static" in url:
        clean_path = url.split("static/", 1)[-1] 
        candidates = [f"/app/static/{clean_path}", f"app/static/{clean_path}", f"static/{clean_path}", f"/usr/src/app/static/{clean_path}"]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    with open(cand, "rb") as f: return _process_image_bytes(f.read())
                except Exception: pass
    if storage_key:
        try:
            stream = storage_service.get_file_stream(storage_key)
            if hasattr(stream, 'read'): return _process_image_bytes(stream.read())
            if isinstance(stream, bytes): return _process_image_bytes(stream)
        except Exception: pass
    if url and url.startswith("http"):
        try:
            response = requests.get(url, timeout=2) 
            if response.status_code == 200: return _process_image_bytes(response.content)
        except Exception: pass
    return None