# FILE: backend/app/services/email_service.py
# PHOENIX PROTOCOL - EMAIL SYSTEM V6.0 (MULTIPLE EMAIL TYPES)

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
        raise

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
    <p><strong>Dërguesi:</strong> {data.get('first_name')} {data.get('last_name')}</p>
    <p><strong>Email:</strong> {data.get('email')}</p>
    <p><strong>Telefoni:</strong> {data.get('phone', 'N/A')}</p>
    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
    <p><strong>Mesazhi:</strong></p>
    <blockquote style="background: #f3f4f6; padding: 15px; border-left: 4px solid {BRAND_COLOR}; margin: 0;">
        {data.get('message')}
    </blockquote>
    """
    
    final_html = _create_html_wrapper("Qendra e Ndihmës", content)
    send_email_sync(settings.ADMIN_EMAIL, subject, final_html)

# ========== INVITATION EMAIL ==========
def send_invitation_email(to_email: str, token: str) -> bool:
    """Send invitation email with password setup link."""
    invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={token}&email={to_email}"
    
    subject = "Ftesë për t'u bashkuar në Juristi.tech"
    
    body_content = f"""
    <p>Përshëndetje,</p>
    <p>Ju jeni ftuar të bashkoheni në ekipin tonë në <strong>{BRAND_NAME}</strong>.</p>
    <p>Për të aktivizuar llogarinë tuaj dhe për të vendosur fjalëkalimin, ju lutemi klikoni butonin më poshtë:</p>
    <p style="text-align: center;">
        <a href="{invite_link}" 
           style="background-color: {BRAND_COLOR}; color: #ffffff !important; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            Aktivizo Llogarinë
        </a>
    </p>
    <p>Nëse butoni nuk funksionon, kopjoni dhe ngjisni këtë link në shfletuesin tuaj:</p>
    <p><code style="word-break: break-all;">{invite_link}</code></p>
    <p>Ky link është i vlefshëm për 7 ditë.</p>
    <p>Faleminderit,<br>Ekipi {BRAND_NAME}</p>
    """
    
    html_content = _create_html_wrapper("Ftesë për t'u bashkuar", body_content)
    send_email_sync(to_email, subject, html_content)
    return True

# ========== PASSWORD RESET EMAIL ==========
def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset email."""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}&email={to_email}"
    
    subject = "Rivendosja e Fjalëkalimit - Juristi.tech"
    
    body_content = f"""
    <p>Përshëndetje,</p>
    <p>Keni kërkuar të rivendosni fjalëkalimin tuaj në <strong>{BRAND_NAME}</strong>.</p>
    <p>Klikoni butonin më poshtë për të vendosur një fjalëkalim të ri:</p>
    <p style="text-align: center;">
        <a href="{reset_link}" 
           style="background-color: {BRAND_COLOR}; color: #ffffff !important; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            Rivendos Fjalëkalimin
        </a>
    </p>
    <p>Ky link është i vlefshëm për 1 orë.</p>
    <p>Nëse nuk keni kërkuar rivendosje, injoroni këtë email.</p>
    """
    
    html_content = _create_html_wrapper("Rivendosja e Fjalëkalimit", body_content)
    send_email_sync(to_email, subject, html_content)
    return True

# ========== WELCOME EMAIL ==========
def send_welcome_email(to_email: str, username: str) -> bool:
    """Send welcome email after account activation or registration."""
    subject = "Mirëseardhje në Juristi.tech!"
    
    body_content = f"""
    <p>Përshëndetje <strong>{username}</strong>,</p>
    <p>Mirë se vini në <strong>{BRAND_NAME}</strong>!</p>
    <p>Llogaria juaj është aktivizuar me sukses. Tani mund të:</p>
    <ul>
        <li>Menaxhoni rastet tuaja ligjore</li>
        <li>Përdorni asistentin tonë AI për analiza</li>
        <li>Bashkëpunoni me ekipin tuaj</li>
    </ul>
    <p style="text-align: center;">
        <a href="{settings.FRONTEND_URL}/login" 
           style="background-color: {BRAND_COLOR}; color: #ffffff !important; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            Hyni në Llogari
        </a>
    </p>
    <p>Ju urojmë punë të mbarë!</p>
    """
    
    html_content = _create_html_wrapper("Mirëseardhje!", body_content)
    send_email_sync(to_email, subject, html_content)
    return True

# ========== SUPPORT REPLY EMAIL ==========
def send_support_reply(to_email: str, reply_message: str, ticket_id: Optional[str] = None) -> bool:
    """Send a reply from support to user."""
    subject = f"Përgjigje nga Mbështetja e Juristi.tech" + (f" (Kërkesa #{ticket_id})" if ticket_id else "")
    
    body_content = f"""
    <p>Përshëndetje,</p>
    <p>Ekipi ynë i mbështetjes ju ka dërguar një përgjigje:</p>
    <blockquote style="background: #f3f4f6; padding: 15px; border-left: 4px solid {BRAND_COLOR}; margin: 10px 0;">
        {reply_message}
    </blockquote>
    <p>Nëse keni pyetje të tjera, mos hezitoni të na kontaktoni.</p>
    """
    
    html_content = _create_html_wrapper("Përgjigje nga Mbështetja", body_content)
    send_email_sync(to_email, subject, html_content)
    return True

# ========== TEAM INVITE ACCEPTED NOTIFICATION ==========
def send_team_invite_accepted_email(owner_email: str, new_member_email: str, new_member_name: str) -> bool:
    """Notify the organization owner that someone accepted an invitation."""
    subject = f"Përdoruesi {new_member_name} iu bashkua ekipit tuaj"
    
    body_content = f"""
    <p>Përshëndetje,</p>
    <p>Përdoruesi <strong>{new_member_name}</strong> ({new_member_email}) ka pranuar ftesën tuaj dhe tani është pjesë e ekipit tuaj në <strong>{BRAND_NAME}</strong>.</p>
    <p>Ju mund të shihni dhe menaxhoni anëtarët e ekipit tuaj nga paneli i menaxhimit.</p>
    <p style="text-align: center;">
        <a href="{settings.FRONTEND_URL}/team" 
           style="background-color: {BRAND_COLOR}; color: #ffffff !important; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            Shko te Menaxhimi i Ekipit
        </a>
    </p>
    """
    
    html_content = _create_html_wrapper("Anëtar i ri në ekip", body_content)
    send_email_sync(owner_email, subject, html_content)
    return True