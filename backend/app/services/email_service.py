# FILE: backend/app/services/email_service.py
# PHOENIX PROTOCOL - EMAIL SYSTEM V4.1
# 1. VISUALS: Sends HTML emails with 'Juristi.tech' branding.
# 2. ENCODING: Explicit UTF-8 support for Albanian characters.
# 3. REUSABILITY: Generic 'send_email' function for future expansion.

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

BRAND_COLOR = "#2563EB" # Primary Blue
BRAND_NAME = "Juristi.tech"

def _create_html_wrapper(title: str, body_content: str) -> str:
    """
    Wraps content in a professional HTML Email Template.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }}
            .header {{ background-color: {BRAND_COLOR}; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 25px; background-color: #ffffff; }}
            .footer {{ background-color: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
            .label {{ font-weight: bold; color: #4b5563; }}
            .value {{ color: #111827; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{BRAND_NAME}</h2>
                <p>{title}</p>
            </div>
            <div class="content">
                {body_content}
            </div>
            <div class="footer">
                &copy; {2025} {BRAND_NAME}. Të gjitha të drejtat e rezervuara.<br>
                Prishtinë, Republika e Kosovës
            </div>
        </div>
    </body>
    </html>
    """

def send_email_sync(to_email: str, subject: str, html_content: str):
    """
    Core function to send an email via SMTP (Synchronous).
    Should be run in a thread.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("⚠️ Email configuration missing. Email not sent.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg['From'] = f"{BRAND_NAME} <{SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach HTML version
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # Send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Email sent to {to_email}: {subject}")

    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")

def send_support_notification_sync(data: dict):
    """
    Formats and sends the Support Request email to Admin.
    """
    if not ADMIN_EMAIL:
        logger.warning("Admin email not configured.")
        return

    subject = f"🔔 Kërkesë e Re për Mbështetje: {data.get('first_name')} {data.get('last_name')}"
    
    # Build content body
    content = f"""
    <p>Përshëndetje Admin,</p>
    <p>Keni marrë një mesazh të ri nga forma e kontaktit:</p>
    <br>
    <p><span class="label">Dërguesi:</span> <span class="value">{data.get('first_name')} {data.get('last_name')}</span></p>
    <p><span class="label">Email:</span> <span class="value">{data.get('email')}</span></p>
    <p><span class="label">Telefoni:</span> <span class="value">{data.get('phone', 'N/A')}</span></p>
    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
    <p><span class="label">Mesazhi:</span></p>
    <blockquote style="background: #f3f4f6; padding: 15px; border-left: 4px solid {BRAND_COLOR}; margin: 0;">
        {data.get('message')}
    </blockquote>
    """
    
    final_html = _create_html_wrapper("Qendra e Ndihmës", content)
    
    send_email_sync(ADMIN_EMAIL, subject, final_html)