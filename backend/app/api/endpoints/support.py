# FILE: backend/app/api/endpoints/support.py
# PHOENIX PROTOCOL - ENDPOINT UPDATE
# 1. ADDED: Call to 'email_service' to notify admin.
# 2. ASYNC: Uses asyncio.to_thread to send email without slowing down the response.

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.core.db import get_db
from app.models.support import ContactRequest
from app.services import email_service # <--- IMPORT
import logging
import asyncio
from datetime import datetime, timezone

router = APIRouter(tags=["Support"])
logger = logging.getLogger(__name__)

@router.post("/contact", status_code=status.HTTP_201_CREATED)
async def submit_support_request(request: ContactRequest, db: Database = Depends(get_db)):
    """
    Saves a contact form submission and emails the admin.
    """
    try:
        # 1. Prepare Data
        message_data = request.model_dump()
        message_data["created_at"] = datetime.now(timezone.utc)
        message_data["status"] = "UNREAD"
        
        # 2. Save to MongoDB (Backup/Log)
        result = db.support_messages.insert_one(message_data)
        
        # 3. Send Email (Fire and Forget - run in background)
        # We assume the DB save is the critical part. If email fails, it's logged.
        asyncio.create_task(
            asyncio.to_thread(email_service.send_support_notification_sync, message_data)
        )
        
        logger.info(f"New support message received from {request.email}")
        return {"message": "Support request received successfully.", "id": str(result.inserted_id)}
        
    except Exception as e:
        logger.error(f"Failed to process support message: {e}")
        raise HTTPException(status_code=500, detail="Could not process message.")