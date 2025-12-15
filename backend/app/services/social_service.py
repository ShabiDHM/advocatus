# FILE: backend/app/services/social_service.py
# PHOENIX PROTOCOL - SOCIAL ENGAGEMENT V2.0 (BRANDING)
# 1. FEATURE: Added 'generate_landing_card' for main site sharing.
# 2. DESIGN: Dark Mode, High-Contrast Text for maximum visibility on WhatsApp/Viber.

import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# Font paths (using standard linux fonts or fallbacks)
try:
    # Try common Linux paths first
    if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        FONT_BOLD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        FONT_REGULAR = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        FONT_LOGO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    else:
        # Fallback to default if specific ttf not found
        FONT_BOLD = ImageFont.load_default()
        FONT_REGULAR = ImageFont.load_default()
        FONT_SMALL = ImageFont.load_default()
        FONT_LOGO = ImageFont.load_default()
except:
    # Extreme fallback
    FONT_BOLD = ImageFont.load_default()
    FONT_REGULAR = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_LOGO = ImageFont.load_default()

def generate_social_card(case_title: str, client_name: str, status: str) -> bytes:
    """
    Creates a 1200x630 image for specific CASE sharing.
    """
    # 1. Create Canvas (Dark Blue/Black)
    W, H = 1200, 630
    img = Image.new('RGB', (W, H), color='#0B1120')
    draw = ImageDraw.Draw(img)

    # 2. Add Gradient/Glow Effect
    draw.ellipse((-100, -100, 500, 500), fill='#1e3a8a', outline=None)
    draw.ellipse((800, 300, 1400, 900), fill='#4c1d95', outline=None)
    
    img = img.filter(ImageFilter.GaussianBlur(radius=60))
    draw = ImageDraw.Draw(img)

    # 3. Add Glass Card Container
    card_x, card_y, card_w, card_h = 100, 80, 1000, 470
    draw.rectangle((card_x, card_y, card_x+card_w, card_y+card_h), fill='#1f2937', outline='#374151', width=3)

    # 4. Add Text
    draw.text((150, 130), "JURISTI.TECH", font=FONT_SMALL, fill='#3b82f6')
    draw.text((150, 160), "RAPORTI I RASTIT", font=FONT_SMALL, fill='#9ca3af')

    draw.text((150, 220), case_title.upper(), font=FONT_BOLD, fill='white')

    draw.text((150, 300), f"KLIENTI: {client_name}", font=FONT_REGULAR, fill='#d1d5db')
    
    status_color = '#10b981' if status == 'Hapur' else '#ef4444'
    draw.text((150, 340), f"STATUSI: {status.upper()}", font=FONT_REGULAR, fill=status_color)

    draw.text((150, 480), "Siguri e garantuar nga Phoenix Protocol.", font=FONT_SMALL, fill='#6b7280')

    # 5. Output
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()

def generate_landing_card() -> bytes:
    """
    Creates a 1200x630 image for MAIN LANDING PAGE sharing.
    """
    # 1. Canvas
    W, H = 1200, 630
    img = Image.new('RGB', (W, H), color='#0B1120')
    draw = ImageDraw.Draw(img)

    # 2. Background Glow
    draw.ellipse((200, -100, 1000, 700), fill='#1e3a8a', outline=None)
    img = img.filter(ImageFilter.GaussianBlur(radius=80))
    draw = ImageDraw.Draw(img)

    # 3. Glass Overlay
    card_x, card_y, card_w, card_h = 50, 50, 1100, 530
    draw.rectangle((card_x, card_y, card_x+card_w, card_y+card_h), fill=None, outline='#374151', width=4)

    # 4. Typography
    # Center Text Logic
    text_main = "JURISTI.TECH"
    
    # Simple centering logic
    try:
        # Approximate check if font object supports getlength
        w_main = FONT_LOGO.getlength(text_main)
    except:
        w_main = 600 # Fallback width guess
        
    x_pos = (W - w_main) / 2
    
    # Draw Main Title
    draw.text((x_pos, 180), text_main, font=FONT_LOGO, fill='white', stroke_width=2, stroke_fill='#3b82f6')

    # Slogan
    text_sub = "INTELIGJENCA ARTIFICIALE PËR DREJTËSINË"
    try:
        w_sub = FONT_REGULAR.getlength(text_sub)
    except:
        w_sub = 400
        
    x_pos_sub = (W - w_sub) / 2
    draw.text((x_pos_sub, 300), text_sub, font=FONT_REGULAR, fill='#9ca3af')

    # Features
    features = "• Analizë Automatike   • Hartim i Padive   • Arkivë Inteligjente"
    try:
        w_feat = FONT_SMALL.getlength(features)
    except:
        w_feat = 300
        
    x_pos_feat = (W - w_feat) / 2
    draw.text((x_pos_feat, 450), features, font=FONT_SMALL, fill='#60a5fa')

    # 5. Output
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()