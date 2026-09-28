# FILE: backend/app/services/document_review/verify/prompt_doc_types.py
# PHOENIX PROTOCOL - VERIFY DOC TYPES V1.0
# Ekstraktuar nga verify_prompts.py V1.14 (pa ndryshim logjike).

from typing import Dict

VERIFY_DOC_TYPES: Dict[str, str] = {
    "padi_civile":         "Padi Civile",
    "pergjigje_padi":      "Përgjigje në Padi",
    "kallzim_penal":       "Kallëzim Penal",
    "kontrate":            "Kontratë",
    "kerkese_propozim":    "Kërkesë / Propozim",
    "ankese_kundershtim":  "Ankesë / Kundërshtim",
    "tjeter":              "Tjetër",
}