# FILE: backend/app/services/social_service.py
# PHOENIX PROTOCOL - SOCIAL ENGAGEMENT V1.0
# 1. LOGIC: Generates dynamic PNG cards for social sharing.
# 2. DESIGN: Uses the 'Dark Mode' aesthetic of the app.

import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Tuple
import os

# Font paths (using standard linux fonts or fallbacks)
try:
    FONT_BOLD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    FONT_REGULAR = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except:
    # Fallback if fonts missing (Docker env)
    FONT_BOLD = ImageFont.load_default()
    FONT_REGULAR = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()

def generate_social_card(case_title: str, client_name: str, status: str) -> bytes:
    """
    Creates a 1200x630 (Facebook/WhatsApp Standard) image.
    """
    # 1. Create Canvas (Dark Blue/Black)
    W, H = 1200, 630
    img = Image.new('RGB', (W, H), color='#0B1120')
    draw = ImageDraw.Draw(img)

    # 2. Add Gradient/Glow Effect (Simulated with circles)
    # Blue glow top left
    draw.ellipse((-100, -100, 500, 500), fill='#1e3a8a', outline=None)
    # Purple glow bottom right
    draw.ellipse((800, 300, 1400, 900), fill='#4c1d95', outline=None)
    
    # Blur the background to make it look like a gradient
    img = img.filter(ImageFilter.GaussianBlur(radius=60))
    draw = ImageDraw.Draw(img) # Re-init draw after filter

    # 3. Add Glass Card Container
    card_x, card_y, card_w, card_h = 100, 80, 1000, 470
    draw.rectangle((card_x, card_y, card_x+card_w, card_y+card_h), fill='#1f2937', outline='#374151', width=3)

    # 4. Add Text
    # Header
    draw.text((150, 130), "JURISTI.TECH", font=FONT_SMALL, fill='#3b82f6')
    draw.text((150, 160), "RAPORTI I RASTIT", font=FONT_SMALL, fill='#9ca3af')

    # Case Title (Main)
    draw.text((150, 220), case_title.upper(), font=FONT_BOLD, fill='white')

    # Meta Info
    draw.text((150, 300), f"KLIENTI: {client_name}", font=FONT_REGULAR, fill='#d1d5db')
    
    status_color = '#10b981' if status == 'Hapur' else '#ef4444'
    draw.text((150, 340), f"STATUSI: {status.upper()}", font=FONT_REGULAR, fill=status_color)

    # Footer
    draw.text((150, 480), "Siguri e garantuar nga Phoenix Protocol.", font=FONT_SMALL, fill='#6b7280')

    # 5. Output
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()