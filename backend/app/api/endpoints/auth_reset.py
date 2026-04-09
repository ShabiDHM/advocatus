# FILE: backend/app/api/endpoints/auth_reset.py
# PHOENIX PROTOCOL - PASSWORD RESET ENDPOINTS (FIXED: Removed Double Prefix)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone, timedelta
import uuid
from pymongo.database import Database
from app.api.endpoints.dependencies import get_db
from app.core.security import get_password_hash
from app.services import email_service

# Removed prefix="/auth" to prevent double-prefixing when included in main.py
router = APIRouter(tags=["auth"])

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)

@router.post("/forgot-password", status_code=200)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Database = Depends(get_db)
):
    user = db.users.find_one({"email": data.email})
    if not user:
        # Return success even if email not found to prevent email enumeration
        return {"message": "If an account exists, a reset link has been sent."}
    
    reset_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"reset_token": reset_token, "reset_expires": expires_at}}
    )
    
    email_service.send_password_reset_email(data.email, reset_token)
    return {"message": "If an account exists, a reset link has been sent."}

@router.post("/reset-password", status_code=200)
async def reset_password(
    data: ResetPasswordRequest,
    db: Database = Depends(get_db)
):
    user = db.users.find_one({
        "reset_token": data.token,
        "reset_expires": {"$gt": datetime.now(timezone.utc)}
    })
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
    
    hashed_password = get_password_hash(data.password)
    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"hashed_password": hashed_password},
            "$unset": {"reset_token": "", "reset_expires": ""}
        }
    )
    return {"message": "Password reset successfully. You can now log in."}