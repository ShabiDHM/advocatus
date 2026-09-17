# FILE: backend/app/services/synthesis_service.py
# PHOENIX PROTOCOL - SYNTHESIS SERVICE (SHIM) V4.0
# V4.0: Ky file është vetëm thin shim — logjika është modularizuar në
#       app/services/synthesis/*. Re-export për backward compatibility.
#       File-i origjinal (V3.8) është ruajtur si synthesis_service.py.bak

from .synthesis.service import (
    SynthesisService,
    get_synthesis_service,
)
from .synthesis.prompts import (
    SECTION_PROMPTS,
    STRICT_RULES,
)

__all__ = [
    "SynthesisService",
    "get_synthesis_service",
    "SECTION_PROMPTS",
    "STRICT_RULES",
]