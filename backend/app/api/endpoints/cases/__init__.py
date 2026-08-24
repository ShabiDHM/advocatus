# FILE: backend/app/api/endpoints/cases/__init__.py
# PHOENIX PROTOCOL - CASES ROUTER HUB V6.0 (STREAMLINED ULTRA-CLEAN WORKSPACE)

from fastapi import APIRouter, Depends, status
from typing import List, Annotated
from pymongo.database import Database
import asyncio

from app.models.case import CaseOut, CaseCreate
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db
from app.services import case_service

from app.api.endpoints.cases.case_management_router import router as case_management_router
from app.api.endpoints.cases.document_router import router as document_router

router = APIRouter()

# 1. Rruga Kryesore: /api/v1/cases
@router.get("", response_model=List[CaseOut], include_in_schema=True)
async def get_user_cases_root(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        case_service.get_cases_for_user,
        db=db,
        owner=current_user
    )

@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED, include_in_schema=True)
async def create_new_case_root(
    case_in: CaseCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        case_service.create_case,
        db=db,
        case_in=case_in,
        owner=current_user
    )

# 2. Përfshirja e nën-routerave aktive
router.include_router(case_management_router)
router.include_router(document_router)