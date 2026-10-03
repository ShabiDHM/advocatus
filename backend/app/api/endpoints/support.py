# FILE: backend/app/api/endpoints/support.py
# PHOENIX PROTOCOL - SUPPORT ENDPOINTS V2.1 (WHITELIST)
# V2.1: `get_current_user` → `get_current_user_identity` për `/messages` + `/reply`
#       (admin only, por pa kërkuar abonim përpara kontrollit të rolit).
#       `/contact` mbetet publik (pa auth) — user pa llogari mund të kontaktojë.
# V2.0: ADDED STORAGE + ADMIN REPLY.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database

from app.api.endpoints.dependencies import get_current_user_identity, get_db
from app.models.user import UserInDB
from app.services import email_service

router = APIRouter()


# --- Request Models ---
class ContactFormRequest(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: EmailStr
    phone: Optional[str] = None
    message: str = Field(..., min_length=10)


class SupportReplyRequest(BaseModel):
    to_email: EmailStr
    reply_message: str = Field(..., min_length=1)
    ticket_id: Optional[str] = None


class SupportMessageOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    message: str
    created_at: datetime
    replied: bool = False


# --- Public Contact Endpoint (stores message) ---
@router.post("/contact", status_code=200)
async def contact_form(
    data: ContactFormRequest,
    db: Database = Depends(get_db)
):
    """Submit a support request. Stores in DB and notifies admin. PUBLIK."""
    doc = {
        "first_name": data.first_name,
        "last_name": data.last_name,
        "email": data.email,
        "phone": data.phone,
        "message": data.message,
        "created_at": datetime.now(timezone.utc),
        "replied": False
    }
    db.support_messages.insert_one(doc)

    try:
        email_service.send_support_notification_sync(data.dict())
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send admin notification: {e}")

    return {"message": "Message sent successfully. We'll respond shortly."}


# --- Admin Endpoints ---
@router.get("/messages", response_model=List[SupportMessageOut])
async def get_support_messages(
    current_user: UserInDB = Depends(get_current_user_identity),
    db: Database = Depends(get_db)
):
    """Admin only: retrieve all support messages."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

    cursor = db.support_messages.find().sort("created_at", -1)
    messages = []
    for msg in cursor:
        messages.append(SupportMessageOut(
            id=str(msg["_id"]),
            first_name=msg["first_name"],
            last_name=msg["last_name"],
            email=msg["email"],
            phone=msg.get("phone"),
            message=msg["message"],
            created_at=msg["created_at"],
            replied=msg.get("replied", False)
        ))
    return messages


@router.post("/reply", status_code=200)
async def support_reply(
    data: SupportReplyRequest,
    current_user: UserInDB = Depends(get_current_user_identity),
    db: Database = Depends(get_db)
):
    """Admin only: send a reply email to the user and mark ticket as replied."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        email_service.send_support_reply(
            to_email=data.to_email,
            reply_message=data.reply_message,
            ticket_id=data.ticket_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reply: {str(e)}")

    if data.ticket_id:
        try:
            db.support_messages.update_one(
                {"_id": ObjectId(data.ticket_id)},
                {"$set": {"replied": True, "replied_at": datetime.now(timezone.utc), "replied_by": current_user.email}}
            )
        except:
            pass

    return {"message": "Reply sent successfully"}