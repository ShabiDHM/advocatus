# FILE: backend/app/services/synthesis/case_types.py
# PHOENIX PROTOCOL - CASE TYPE DETECTION V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import re
import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict
from bson import ObjectId

from .constants import CASE_TYPE_SCAN_CHARS_PER_DOC, CASE_TYPE_MAX_DOCS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

CASE_TYPE_PATTERNS = {
    "Kërkesë për Urdhër Mbrojtjeje": {
        "patterns": [
            r"urdh[eë]r\s+mbrojtj?eje",
            r"urdh[eë]r\s+mbrojt[eë]s",
            r"dhun[eë]\s+n[eë]\s+familje",
            r"mbrojtje\s+nga\s+dhuna\s+n[eë]\s+familje",
            r"LMDHF",
            r"ligj[i]?\s*nr\.?\s*0[48]\s*[\/\-]?\s*L[-\s]*1[28]5",
            r"pal[eë]\s+e\s+mbrojtur",
            r"pal[eë]\s+p[eë]rgjegj[eë]se",
            r"masa\s+t[eë]\s+mbrojtjes",
        ],
        "weight": 3.0,
    },
    "Çështje Familjare": {
        "patterns": [
            r"kujdestari",
            r"bashk[eë]short",
            r"divorc",
            r"ushqim(?:i)?\s+fëmij[eë]s",
            r"alimentacion",
            r"marr[eë]dh[eë]nie\s+familjare",
        ],
        "weight": 2.5,
    },
    "Kallëzim Penal": {
        "patterns": [
            r"kall[eë]zim\s+penal",
            r"aktakuz[eë]\b",
            r"vep[eë]r\s+penale",
            r"prokuror(?:i|ia|in)",
            r"i\s+pandehur",
            r"e\s+pandehur",
        ],
        "weight": 2.0,
    },
    "Padi Civile": {
        "patterns": [
            r"k[eë]rkes[eë]padi",
            r"padit[eë]s(?:i|ja|in)",
            r"\be\s+paditura\b",
            r"\bi\s+padituri\b",
            r"petitum",
        ],
        "weight": 2.0,
    },
    "Procedurë Administrative": {
        "patterns": [
            r"ankes[eë]\s+administrative",
            r"organ(?:i)?\s+administrativ",
            r"procedur[eë]\s+administrative",
        ],
        "weight": 2.0,
    },
}


CASE_TYPE_FAMILIES = {
    "civil_family": {
        "label": "Kërkesë për Urdhër Mbrojtjeje",
        "filename_keywords": [
            "mbrojtje", "mbrojtjes", "mbrojtës", "mbrojtes",
            "urdher_mbrojtje", "urdhermbrojtje",
            "dhune", "dhunë", "dhuna",
            "familje", "familjar",
            "shkurorëzim", "divorc", "kujdestari",
        ],
    },
    "penal_family": {
        "label": "Procedurë Penale",
        "filename_keywords": [
            "aktakuz", "aktakuze",
            "kallzim", "kallëzim",
            "hedhje_akuz", "hedhjes_se_akuz",
            "penale", "penal",
            "prokuror",
            "pandehur", "padisur",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_case_type(
    db,
    case_id: str,
    extractions: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Zbulon llojin e lëndës. Bllok i ekstraktuar nga _detect_case_type V3.8.
    """
    civil_found = False
    penal_found = False
    civil_evidence = None
    penal_evidence = None

    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        query = {
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
            "status": {"$ne": "DELETED"},
        }
        docs = list(db.documents.find(query, {"file_name": 1}))

        for doc in docs:
            filename_lower = (doc.get("file_name") or "").lower()

            if not civil_found:
                for kw in CASE_TYPE_FAMILIES["civil_family"]["filename_keywords"]:
                    if kw in filename_lower:
                        civil_found = True
                        civil_evidence = doc.get("file_name")
                        break

            if not penal_found:
                for kw in CASE_TYPE_FAMILIES["penal_family"]["filename_keywords"]:
                    if kw in filename_lower:
                        penal_found = True
                        penal_evidence = doc.get("file_name")
                        break

            if civil_found and penal_found:
                break

        if civil_found and penal_found:
            dual_type = (
                f"{CASE_TYPE_FAMILIES['civil_family']['label']} → "
                f"{CASE_TYPE_FAMILIES['penal_family']['label']}"
            )
            return dual_type
        elif civil_found:
            return CASE_TYPE_FAMILIES["civil_family"]["label"]
        elif penal_found:
            return CASE_TYPE_FAMILIES["penal_family"]["label"]

    except Exception as e:
        logger.warning(f"⚠️ [SYNTHESIS] Override scan failed: {e}")

    scores = defaultdict(float)
    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        query = {
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
            "status": {"$ne": "DELETED"},
        }

        cursor = db.documents.find(
            query,
            {"_id": 1, "content": 1, "extracted_text": 1, "text": 1},
        ).limit(CASE_TYPE_MAX_DOCS)

        for doc in cursor:
            text = (
                doc.get("content")
                or doc.get("extracted_text")
                or doc.get("text")
                or ""
            )
            if not text:
                continue

            text_lower = text.lower()
            text_scannable = text_lower[:CASE_TYPE_SCAN_CHARS_PER_DOC]

            for case_type, cfg in CASE_TYPE_PATTERNS.items():
                weight = cfg["weight"]
                for pattern in cfg["patterns"]:
                    matches = len(re.findall(pattern, text_scannable, re.IGNORECASE))
                    if matches > 0:
                        scores[case_type] += matches * weight

    except Exception as e:
        logger.warning(f"⚠️ [SYNTHESIS] detect_case_type scan failed: {e}")

    if not scores:
        return None

    best = max(scores.items(), key=lambda x: x[1])
    return best[0]