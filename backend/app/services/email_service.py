# FILE: backend/app/services/email_service.py
# PHOENIX PROTOCOL - EMAIL SYSTEM V5.0 (ADDED INVITATION EMAIL)

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

BRAND_COLOR = "#2563EB"  # Primary Blue
BRAND_NAME = "Juristi.tech"

def _create_html_wrapper(title: str, body_content: str) -> str:
    """Wraps content in a professional HTML Email Template."""
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
            .button {{ display: inline-block; background-color: {BRAND_COLOR}; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
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
                &copy; 2025 {BRAND_NAME}. Të gjitha të drejtat e rezervuara.<br>
                Prishtinë, Republika e Kosovës
            </div>
        </div>
    </body>
    </html>
    """

def send_email_sync(to_email: str, subject: str, html_content: str):
    """Core function to send an email via SMTP (Synchronous)."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("⚠️ Email configuration missing. Email not sent.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg['From'] = f"{BRAND_NAME} <{settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Email sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        raise  # Re-raise to let caller know

def send_support_notification_sync(data: dict):
    """Formats and sends the Support Request email to Admin."""
    if not settings.ADMIN_EMAIL:
        logger.warning("Admin email not configured.")
        return

    subject = f"🔔 Kërkesë e Re për Mbështetje: {data.get('first_name')} {data.get('last_name')}"
    
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
    send_email_sync(settings.ADMIN_EMAIL, subject, final_html)

def send_invitation_email(to_email: str, token: str) -> bool:
    """
    Send invitation email with password setup link.
    Returns True if sent successfully, raises exception otherwise.
    """
    invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={token}&email={to_email}"
    
    subject = "Ftesë për t'u bashkuar në Juristi.tech"
    
    body_content = f"""
    <p>Përshëndetje,</p>
    <p>Ju jeni ftuar të bashkoheni në ekipin tonë në <strong>{BRAND_NAME}</strong>.</p>
    <p>Për të aktivizuar llogarinë tuaj dhe për të vendosur fjalëkalimin, ju lutemi klikoni butonin më poshtë:</p>
    <p style="text-align: center;">
        <a href="{invite_link}" class="button">Aktivizo Llogarinë</a>
    </p>
    <p>Nëse butoni nuk funksionon, kopjoni dhe ngjisni këtë link në shfletuesin tuaj:</p>
    <p><code style="word-break: break-all;">{invite_link}</code></p>
    <p>Ky link është i vlefshëm për 7 ditë.</p>
    <p>Faleminderit,<br>Ekipi {BRAND_NAME}</p>
    """
    
    html_content = _create_html_wrapper("Ftesë për t'u bashkuar", body_content)
    send_email_sync(to_email, subject, html_content)
    return True