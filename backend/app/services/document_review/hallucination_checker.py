# FILE: backend/app/services/document_review/hallucination_checker.py
# PHOENIX PROTOCOL - HALLUCINATION CHECKER SHIM V1.25
# V1.25: SHIM — Logjika u zhvendos në paketën `hallucination/`.
#        Ky file ri-eksporton TË GJITHA funksionet ekzistuese për
#        BACKWARD COMPATIBILITY. Importuesit ekzistues vazhdojnë të punojnë
#        pa ndryshim.
#        Për kod të re, importoni direkt nga paketa:
#            from app.services.document_review.hallucination import check_all_sections

# Re-export TË GJITHA nga paketa
from .hallucination import *  # noqa: F401,F403
from .hallucination import __all__  # noqa: F401