# FILE: backend/app/services/document_review/dynamic_config.py
# PHOENIX PROTOCOL - DYNAMIC CONFIG LOADER V1.1 (HAPI B2)
# V1.1: Shtuar get_known_laws() — lexon map-in name→number të ligjeve
#       nga data/dynamic_config.json (key: "known_laws").
#       Zero hardcoding në hallucination_checker — ligjet shtohen në JSON.
# H2+H3+H4+H5: Lexon konfigurimin dinamik nga data/dynamic_config.json.
# Zero hardcoding — shtimi/ndryshimi i ligjeve, konventave, akronimeve
# bëhet pa ndryshim kodi, vetëm në JSON.
#
# Fallback: nëse JSON mungon ose ka gabim → default-et e hardcoduara në
# modulet përdoruese (mbajnë funksionalitetin minimal).
#
# Cache: lru_cache(maxsize=1) → lexohet një herë, aplikohet pas restart.
# Për reload dinamik: reload_dynamic_config().

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "data" / "dynamic_config.json"


@lru_cache(maxsize=1)
def _load_dynamic_config() -> Dict[str, Any]:
    """Lexon JSON-in një herë dhe cache-on. Fallback {} nëse mungon/gabim."""
    if not _CONFIG_PATH.exists():
        logger.warning(
            f"⚠️ [DYNAMIC CONFIG] {_CONFIG_PATH} nuk ekziston — "
            f"përdor default-et e moduleve."
        )
        return {}

    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning(
                f"⚠️ [DYNAMIC CONFIG] {_CONFIG_PATH} nuk përmban objekt JSON."
            )
            return {}
        logger.info(
            f"✅ [DYNAMIC CONFIG] U lexua: {_CONFIG_PATH} "
            f"(keys: {sorted(data.keys())})"
        )
        return data
    except Exception as e:
        logger.error(
            f"❌ [DYNAMIC CONFIG] Leximi i {_CONFIG_PATH} dështoi: {e}"
        )
        return {}


def reload_dynamic_config() -> None:
    """Pastron cache-in — ndryshimet në JSON aplikohen menjëherë."""
    _load_dynamic_config.cache_clear()
    logger.info("🔄 [DYNAMIC CONFIG] Cache u pastrua — rilexohet me thirrjen tjetër.")


# ═══════════════════════════════════════════════════════════════════════════
# GETTERS (me fallback në default)
# ═══════════════════════════════════════════════════════════════════════════

def get_law_successors(
    default: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    data = _load_dynamic_config().get("law_successors")
    if isinstance(data, dict) and data:
        return data
    return default


def get_international_law_keywords(default: List[str]) -> List[str]:
    data = _load_dynamic_config().get("international_law_keywords")
    if isinstance(data, list) and data:
        return data
    return default


def get_known_abbrev_keywords(
    default: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    data = _load_dynamic_config().get("known_abbrev_keywords")
    if isinstance(data, dict) and data:
        return data
    return default


def get_known_abbrev_excludes(
    default: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    data = _load_dynamic_config().get("known_abbrev_excludes")
    if isinstance(data, dict) and data:
        return data
    return default


# ═══════════════════════════════════════════════════════════════════════════
# V1.1: KNOWN LAWS (name → list of numbers)
# ═══════════════════════════════════════════════════════════════════════════

def get_known_laws(
    default: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    V1.1: Lexon map-in name→numbers të ligjeve të njohura.

    Key në JSON: "known_laws" (objekt).
    Struktura: { "kodi penal": ["06/L-074"], "ligji per familjen": ["2004/32"], ... }

    Fallback: default (minimal) nëse JSON mungon ose bosh.

    Përdoret nga hallucination_checker për:
      - _get_globally_allowed_laws() → allowed laws
      - _check_law_name_number_consistency() → validim name↔number
    """
    data = _load_dynamic_config().get("known_laws")
    if isinstance(data, dict) and data:
        return data
    return default