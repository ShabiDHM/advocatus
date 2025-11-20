# FILE: backend/app/services/email_service.py
# PHOENIX PROTOCOL - EMAIL NOTIFICATION SYSTEM
# 1. USES: Standard 'smtplib' (no new dependencies required).
# 2. SECURITY: Uses TLS encryption.
# 3. ASYNC: Runs in a thread to prevent blocking the API.

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

def send_support_notification_sync(data: dict):
    """
    Synchronous function to send email. 
    (Called via asyncio.to_thread to be non-blocking)
    """
    if not SMTP_USER or not SMTP_PASSWORD or not ADMIN_EMAIL:
        logger.warning("Email configuration missing. Skipping notification.")
        return

    try:
        # 1. Setup Message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f"🔔 New Support Request: {data.get('first_name')} {data.get('last_name')}"

        # 2. Create Body
        body = f"""
        ----------------------------------------
        NEW SUPPORT MESSAGE RECEIVED
        ----------------------------------------
        
        FROM:    {data.get('first_name')} {data.get('last_name')}
        EMAIL:   {data.get('email')}
        PHONE:   {data.get('phone', 'N/A')}
        
        MESSAGE:
        "{data.get('message')}"
        
        ----------------------------------------
        Time: {data.get('created_at')}
        """
        
        msg.attach(MIMEText(body, 'plain'))

        # 3. Connect and Send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"📧 Email notification sent to {ADMIN_EMAIL}")

    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")