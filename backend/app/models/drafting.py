# FILE: backend/app/models/drafting.py
# PHOENIX PROTOCOL - INPUT COMPATIBILITY
# 1. ALIAS: 'prompt' field now accepts 'user_prompt' from frontend.
# 2. UPDATE: Added 'use_library' flag for Arkiva integration.

from pydantic import BaseModel, Field
from typing import Optional

class DraftRequest(BaseModel):
    # Frontend sends 'user_prompt', maps to 'prompt'
    prompt: str = Field(..., alias="user_prompt")
    case_id: Optional[str] = None
    document_type: Optional[str] = "General"
    jurisdiction: Optional[str] = "Kosovo"
    
    # Context can be passed separately or merged
    context: Optional[str] = None
    
    # PHOENIX FIX: Flag to enable/disable Library RAG
    use_library: bool = False

    class Config:
        populate_by_name = True