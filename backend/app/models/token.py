# FILE: backend/app/models/token.py
# PHOENIX PROTOCOL - MISSING MODEL RESTORED
from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None