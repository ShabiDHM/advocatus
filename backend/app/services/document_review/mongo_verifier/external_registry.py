# FILE: backend/app/services/document_review/mongo_verifier/external_registry.py
# PHOENIX PROTOCOL - EXTERNAL SOURCES REGISTRY V1.0
#
# Lexon `data/external_sources.json` dhe ofron lookup për traktate ndërkombëtare
# që Kosova i ka ratifikuar (KEDNJ, OKB-Fëmijës, Hagë).
#
# ZERO HARDCODING — të gjitha burimet në JSON, jo në kod.
#
# Përdoret nga `articles.py` për të klasifikuar citimet si:
#   - "external" (traktat ndërkombëtar — verifikuar si i njohur)
#   - "unverified" (nuk u gjet në DB dhe nuk njihet si traktat)


import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..helpers import normalize_albanian

logger = logging.getLogger(__name__)

EXTERNAL_FILE_NAME = "external_sources.json"

_REGISTRY_CACHE: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════
# FILE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def _find_external_file() -> Optional[Path]:
    """Gjen `external_sources.json` në disa vende të mundshme."""
    current = Path(__file__).resolve()

    for parent in [current, *current.parents]:
        for sub in ("data", "backend/data"):
            candidate = parent / sub / EXTERNAL_FILE_NAME
            if candidate.exists() and candidate.is_file():
                return candidate

    for base in (Path.cwd(), Path.cwd().parent):
        for sub in ("data", "backend/data"):
            candidate = base / sub / EXTERNAL_FILE_NAME
            if candidate.exists() and candidate.is_file():
                return candidate

    for base in (Path("/app/data"), Path("/app/backend/data")):
        candidate = base / EXTERNAL_FILE_NAME
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════

def _load_registry() -> Dict[str, Any]:
    """Lexon regjistrin nga JSON (cache in-memory)."""
    global _REGISTRY_CACHE

    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    path = _find_external_file()
    if not path:
        logger.warning(
            f"[EXTERNAL_REGISTRY] '{EXTERNAL_FILE_NAME}' nuk u gjet — "
            f"burimet eksterne joaktive"
        )
        _REGISTRY_CACHE = {"external_sources": {}}
        return _REGISTRY_CACHE

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "external_sources" not in data:
            logger.warning(
                f"[EXTERNAL_REGISTRY] Formati i '{EXTERNAL_FILE_NAME}' i pavlefshëm"
            )
            data = {"external_sources": {}}

        _REGISTRY_CACHE = data
        n = len(data.get("external_sources", {}))
        logger.info(f"[EXTERNAL_REGISTRY] Loaded {n} external sources from {path}")
        return _REGISTRY_CACHE
    except Exception as e:
        logger.error(f"[EXTERNAL_REGISTRY] Load failed: {e}", exc_info=True)
        _REGISTRY_CACHE = {"external_sources": {}}
        return _REGISTRY_CACHE


def clear_registry_cache() -> None:
    """Invalidon cache-in (thirret pas update JSON)."""
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
    logger.info("[EXTERNAL_REGISTRY] Cache cleared")


# ═══════════════════════════════════════════════════════════════════════════
# LOOKUP
# ═══════════════════════════════════════════════════════════════════════════

def find_external_source(law_hint: str) -> Optional[Dict[str, Any]]:
    """
    Kontrollon nëse `law_hint` i përket një burimi ekstern.

    Returns:
        None nëse nuk përputhet
        Dict me:
          {
            "id": "KEDNJ",
            "canonical_name": "Konventa Evropiane për të Drejtat e Njeriut",
            "short_name": "KEDNJ",
            "category": "international_treaty",
            "constitutional_basis": "Neni 22 i Kushtetutës...",
            "note": "...",
          }
    """
    if not law_hint:
        return None

    registry = _load_registry()
    sources = registry.get("external_sources", {})
    if not sources:
        return None

    h = normalize_albanian(law_hint)
    if not h:
        return None

    for source_id, source_info in sources.items():
        keywords = source_info.get("pattern_keywords", []) or []
        for kw in keywords:
            kw_norm = normalize_albanian(kw)
            if kw_norm and kw_norm in h:
                return {
                    "id": source_id,
                    "canonical_name": source_info.get("canonical_name", ""),
                    "short_name": source_info.get("short_name", ""),
                    "category": source_info.get("category", "international_treaty"),
                    "constitutional_basis": source_info.get("constitutional_basis", ""),
                    "note": source_info.get("note", ""),
                }

    return None


def get_all_external_sources() -> List[Dict[str, Any]]:
    """Kthen listën e të gjitha burimeve eksterne (për stats / debug)."""
    registry = _load_registry()
    sources = registry.get("external_sources", {})
    result = []
    for source_id, source_info in sources.items():
        result.append({
            "id": source_id,
            "canonical_name": source_info.get("canonical_name", ""),
            "short_name": source_info.get("short_name", ""),
            "category": source_info.get("category", "international_treaty"),
        })
    return result


__all__ = [
    "find_external_source",
    "get_all_external_sources",
    "clear_registry_cache",
]