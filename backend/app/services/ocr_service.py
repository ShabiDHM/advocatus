# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - AI VISION OCR ENGINE V20.0 (OPENROUTER MULTIMODAL ZERO-DROP TRANSCRIBER)

import os
import json
import logging
import re
import io
import time
import base64
from typing import Dict, List, Tuple, Optional, Any

from app.services.llm.llm_client import _get_sync_client, _get_api_key

logger = logging.getLogger(__name__)

# Modelet e Inteligjencës Vizuale (Të testuara në OpenRouter për OCR të dokumenteve)
VISION_PRIMARY_MODEL = "openai/gpt-4o-mini"
VISION_FALLBACK_MODELS = [
    "google/gemini-2.0-flash-001",
    "anthropic/claude-sonnet-latest"
]

class SmartOCRResult:
    def __init__(self, text: str, confidence: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.confidence = confidence
        self.metadata = metadata if metadata is not None else {}
        self.structured_data: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {'text': self.text, 'confidence': self.confidence, 'metadata': self.metadata, 'structured_data': self.structured_data}

# --- 1. LOCAL PDF DIGITAL EXTRACTOR (Nëse dokumenti ka tekst dixhital të gatshëm) ---

def extract_text_from_pdf_locally(pdf_bytes: bytes) -> Optional[str]:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text_runs = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_runs.append(t)
        full_text = "\n".join(text_runs).strip()
        if len(full_text) > 100:
            logger.info(f"✅ [Local PDF] U nxorën {len(full_text)} karaktere dixhitale pa pasur nevojë për OCR.")
            return full_text
    except Exception as e:
        logger.warning(f"Local PDF parser skipped: {e}")
    return None

# --- 2. OPENROUTER MULTIMODAL AI VISION OCR (Zëvendësimi i Plotë i OCR Space) ---

def run_ai_vision_ocr(image_bytes: bytes) -> Tuple[str, float]:
    """
    Përdor Inteligjencën Vizuale të OpenRouter (GPT-4o-mini / Gemini / Claude)
    për të transkriptuar 100% të gjithë tekstin shqip nga faqja e skanuar.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("❌ Mungon OPENROUTER_API_KEY për Vision OCR.")
        return "", 0.0

    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{b64_image}"

    client = _get_sync_client()

    ocr_system_prompt = (
        "Ti je një Transkriptues Ligjor dhe Ekspert i Forenzikës së Dokumenteve për Gjykatat e Kosovës.\n"
        "DETYRA JOTE E VETME:\n"
        "Transkripto me saktësi 100% literale çdo fjalë, numër, datë, dhe element të shkruar në këtë faqe të skanuar.\n\n"
        "RREGULLAT E HEKURTA:\n"
        "1. Transkripto çdo datë (p.sh. 31.08.2026), numër lënde (p.sh. KE.nr.662/2022), emra palësh, emra gjyqtarësh dhe shuma monetare me saktësi absolute.\n"
        "2. Ruaj strukturën origjinale të paragrafeve, pikave të dispozitivit (I, II, III) dhe neneve ligjore.\n"
        "3. MOS bëj përmbledhje, MOS bëj analiza, dhe MOS shto asnjë koment. Kthe VETËM tekstin e plotë të transkriptuar."
    )

    models_to_try = [VISION_PRIMARY_MODEL] + [m for m in VISION_FALLBACK_MODELS if m != VISION_PRIMARY_MODEL]

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                logger.info(f"👁️ [AI Vision OCR] Duke transkriptuar faqen me modelin: {model_name}...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": ocr_system_prompt},
                                {"type": "image_url", "image_url": {"url": data_url}}
                            ]
                        }
                    ],
                    temperature=0.0,
                    max_tokens=4000
                )

                if response and response.choices and len(response.choices) > 0:
                    raw_text = response.choices[0].message.content or ""
                    cleaned_text = raw_text.strip()
                    if len(cleaned_text) > 10:
                        logger.info(f"✅ [AI Vision OCR] Faqja u transkriptua me sukses: {len(cleaned_text)} karaktere me {model_name}.")
                        return cleaned_text, 0.99
            except Exception as e:
                logger.warning(f"⚠️ [AI Vision OCR] Modeli {model_name} dështoi (Përpjekja {attempt + 1}): {e}")
                time.sleep(1.0)
                continue

    logger.error("❌ Të gjitha modelet e AI Vision dështuan për këtë faqe.")
    return "", 0.0

def rule_based_correction(text: str) -> str:
    if not text: 
        return text
    text = re.sub(r'SPARKOSOVA', 'SPAR KOSOVA', text, flags=re.IGNORECASE)
    return text.strip()

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    try:
        # Nëse është PDF dixhital, nxjerr tekstin pa shpenzuar asnjë token
        if image_bytes.startswith(b'%PDF-'):
            local_text = extract_text_from_pdf_locally(image_bytes)
            if local_text:
                return rule_based_correction(local_text)
                
        # Nëse është imazh/skanim, përdor AI Vision OCR me sy inteligjentë
        raw_text, confidence = run_ai_vision_ocr(image_bytes)
        corrected_text = rule_based_correction(raw_text)
        return corrected_text
    except Exception as e:
        logger.error(f"❌ Gabim i përgjithshëm në OCR: {e}")
        return ""

def extract_text_from_image(file_path: str) -> str:
    if not os.path.exists(file_path): 
        return ""
    try:
        with open(file_path, "rb") as f: 
            image_bytes = f.read()
        return extract_text_from_image_bytes(image_bytes)
    except Exception as e:
        logger.error(f"❌ Gabim gjatë leximit të imazhit nga disku: {e}")
        return ""

def preprocess_image_for_ocr(pil_image): 
    return pil_image

def clean_ocr_garbage(text): 
    return text.strip()

def extract_expense_data_from_image(image_bytes: bytes) -> Dict[str, Any]:
    text = extract_text_from_image_bytes(image_bytes)
    return {'success': True, 'text': text, 'structured_data': {}}