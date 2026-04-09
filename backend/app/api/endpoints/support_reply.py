# FILE: backend/app/api/endpoints/support_reply.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from pymongo.database import Database
from app.api.endpoints.dependencies import get_current_user, get_db
from app.models.user import UserInDB
from app.services import email_service

router = APIRouter(prefix="/support", tags=["Support"])

class SupportReplyRequest(BaseModel):
    to_email: EmailStr
    reply_message: str
    ticket_id: Optional[str] = None

@router.post("/reply", status_code=200)
async def send_support_reply(
    data: SupportReplyRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    # Only admin users can send support replies
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        email_service.send_support_reply(
            to_email=data.to_email,
            reply_message=data.reply_message,
            ticket_id=data.ticket_id
        )
        return {"message": "Reply sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {str(e)}")