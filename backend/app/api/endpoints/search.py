# backend/app/api/endpoints/search.py
# DEFINITIVE VERSION 3.0 (ARCHITECTURAL CORRECTION):
# Corrected the import path for 'get_db' to align with the centralized
# dependency architecture, resolving the 'ImportError' startup crash.

from fastapi import APIRouter, Depends
from typing import List, Annotated
from pymongo.database import Database

from ...services import search_service
from ...models.document import DocumentOut
from ...models.user import UserInDB
# --- PHOENIX PROTOCOL FIX: Import all dependencies from the correct, centralized location ---
from .dependencies import get_current_active_user, get_db

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/")
def search_documents(
    query: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
) -> List[DocumentOut]:
    """Performs a cross-case semantic search across all accessible documents."""
    # The call to the service layer is already correct.
    return search_service.perform_search(query=query, user=current_user, db=db)