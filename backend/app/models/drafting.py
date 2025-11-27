# FILE: backend/app/models/drafting.py
# PHOENIX PROTOCOL - INPUT COMPATIBILITY
# 1. ALIAS: 'prompt' field now accepts 'user_prompt' from frontend.
# 2. RESULT: Drafting input is correctly passed to the AI.

from pydantic import BaseModel, Field
from typing import Optional

class DraftRequest(BaseModel):
    # PHOENIX FIX: Allow 'user_prompt' (Frontend) to map to 'prompt' (Backend)
    prompt: str = Field(..., alias="user_prompt")
    case_id: Optional[str] = None
    document_type: Optional[str] = "General"
    jurisdiction: Optional[str] = "Kosovo"
    
    # Context can be passed separately or merged
    context: Optional[str] = None 

    class Config:
        populate_by_name = True