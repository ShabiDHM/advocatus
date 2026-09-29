# FILE: backend/app/api/endpoints/laws_pkg/repealed_registry.py
# PHOENIX PROTOCOL - REPEALED LAWS REGISTRY V1.0
#
# Lexon regjistrin e ligjeve të shfuqizuara nga `data/repealed_laws.json`
# dhe ofron API për të kontrolluar nëse një titull ligji është i shfuqizuar.
#
# ZERO HARDCODING: të gjitha të dhënat vijnë nga JSON file.
# Cache in-memory për performancë.

import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

REPEALED_FILE_NAME = "repealed_laws.json"

_REGISTRY_CACHE: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════
# FILE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def _find_data_file() -> Optional[Path]:
    """
    Gjen `repealed_laws.json` në disa vende të mundshme.
    """
    current = Path(__file__).resolve()

    # Provo nga backend/data
    for parent in [current, *current.parents]:
        # parent / "data" / filename  (kur parent == backend)
        candidate = parent / "data" / REPEALED_FILE_NAME
        if candidate.exists() and candidate.is_file():
            return candidate
        # parent / "backend" / "data" / filename
        candidate = parent / "backend" / "data" / REPEALED_FILE_NAME
        if candidate.exists() and candidate.is_file():
            return candidate

    # Provo nga CWD
    for base in [Path.cwd(), Path.cwd().parent]:
        for sub in ("data", "backend/data"):
            candidate = base / sub / REPEALED_FILE_NAME
            if candidate.exists() and candidate.is_file():
                return candidate

    # Docker
    for base in (Path("/app/data"), Path("/app/backend/data")):
        candidate = base / REPEALED_FILE_NAME
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(s: str) -> str:
    """
    Normalizim për matching:
    - Lowercase
    - Heq diakritikat (ë→e, ç→c)
    - Collapse whitespace
    """
    if not s:
        return ""
    try:
        from app.api.endpoints.laws_pkg.laws_dictionary import _normalize_diacritics
        n = _normalize_diacritics(s.lower())
    except Exception:
        n = s.lower()
    return re.sub(r'\s+', ' ', n).strip()


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════

def load_repealed_registry(force_reload: bool = False) -> Dict[str, Any]:
    """
    Lexon regjistrin nga JSON dhe e cache-on in-memory.
    Kthen dict me `version`, `updated_at`, `repealed` (list).
    """
    global _REGISTRY_CACHE

    if _REGISTRY_CACHE is not None and not force_reload:
        return _REGISTRY_CACHE

    path = _find_data_file()
    if not path:
        logger.warning(
            f"[REPEALED] '{REPEALED_FILE_NAME}' nuk u gjet — regjistri bosh"
        )
        _REGISTRY_CACHE = {"version": "0.0", "repealed": []}
        return _REGISTRY_CACHE

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validim minimal
        if not isinstance(data, dict):
            raise ValueError("JSON root duhet të jetë objekt")
        if "repealed" not in data or not isinstance(data["repealed"], list):
            data["repealed"] = []

        _REGISTRY_CACHE = data
        n = len(data["repealed"])
        logger.info(f"[REPEALED] Loaded {n} repealed law(s) from {path}")
        return _REGISTRY_CACHE

    except Exception as e:
        logger.error(f"[REPEALED] Load failed: {e}", exc_info=True)
        _REGISTRY_CACHE = {"version": "0.0", "repealed": []}
        return _REGISTRY_CACHE


def clear_registry_cache() -> None:
    """Invalidon cache-in e regjistrit (thirret pas update JSON)."""
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
    logger.info("[REPEALED] Cache cleared")


# ═══════════════════════════════════════════════════════════════════════════
# LOOKUP
# ═══════════════════════════════════════════════════════════════════════════

def find_repealed_info(law_title: str) -> Optional[Dict[str, Any]]:
    """
    Kontrollon nëse një titull ligji i përket regjistrit të shfuqizuarve.

    Returns:
        None nëse nuk është i shfuqizuar.
        Dict me:
          {
            "id": "03-L-182",
            "is_repealed": True,
            "repealed_by": "...",
            "repealed_date": "2023-10-12",
            "source": "...",
            "reason": "...",
            "warning_message": "⚠️ Ky ligj është shfuqizuar më ...",
            "successor_patterns": [...]
          }
    """
    if not law_title:
        return None

    registry = load_repealed_registry()
    norm_target = _normalize(law_title)

    if not norm_target:
        return None

    for entry in registry.get("repealed", []):
        patterns = entry.get("title_patterns", [])
        for pattern in patterns:
            norm_pattern = _normalize(pattern)
            if norm_pattern and norm_pattern in norm_target:
                repealed_by = entry.get("repealed_by", "")
                repealed_date = entry.get("repealed_date", "")
                source = entry.get("source", "")

                # Warning message i strukturuar
                parts = ["⚠️ KY LIGJ ËSHTË SHFUQIZUAR"]
                if repealed_date:
                    parts.append(f"më {repealed_date}")
                if repealed_by:
                    parts.append(f"nga '{repealed_by}'")
                if source:
                    parts.append(f"({source}).")

                warning_msg = " ".join(parts)
                warning_msg += (
                    " Konsulto ligjin zëvendësues për informacion të përditësuar."
                )

                return {
                    "id": entry.get("id", ""),
                    "is_repealed": True,
                    "repealed_by": repealed_by,
                    "repealed_date": repealed_date,
                    "source": source,
                    "reason": entry.get("reason", ""),
                    "warning_message": warning_msg,
                    "successor_patterns": entry.get("repealed_by_patterns", []),
                }

    return None


def get_all_repealed_titles() -> List[Dict[str, Any]]:
    """
    Kthen të gjithë ligjet e shfuqizuara (nga regjistri) me detaje.
    """
    registry = load_repealed_registry()
    result = []
    for entry in registry.get("repealed", []):
        result.append({
            "id": entry.get("id", ""),
            "law_title": entry.get("title_patterns", [""])[0] if entry.get("title_patterns") else "",
            "all_patterns": entry.get("title_patterns", []),
            "repealed_by": entry.get("repealed_by", ""),
            "repealed_date": entry.get("repealed_date", ""),
            "source": entry.get("source", ""),
            "reason": entry.get("reason", ""),
        })
    return result


__all__ = [
    "load_repealed_registry",
    "clear_registry_cache",
    "find_repealed_info",
    "get_all_repealed_titles",
]