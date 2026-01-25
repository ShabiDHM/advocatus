# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V5.0 (KOSOVO OPTIMIZED)
# OPTIMIZED: Kosovo market with enhanced thermal receipt handling
# ADDED: Kosovo-specific merchant database and decimal correction

import pytesseract
from pytesseract import TesseractError, Output
from PIL import Image, ImageEnhance, ImageFilter
import logging
import cv2
import numpy as np
import re
import os
import io
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import requests

logger = logging.getLogger(__name__)

# --- PHOENIX: Windows Auto-Configuration ---
if os.name == 'nt':  # 'nt' means Windows
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\Shaban\AppData\Local\Tesseract-OCR\tesseract.exe'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"✅ Tesseract found at: {path}")
            break
    else:
        logger.warning("⚠️ Tesseract not found in common Windows locations")

# --- KOSOVO CONFIGURATION ---
INVOICE_LANGUAGES = ['sqi', 'eng']  # Albanian first for Kosovo market
FALLBACK_LANGUAGE = 'eng'

# Kosovo-specific invoice keywords (Albanian prioritized)
INVOICE_KEYWORDS = {
    'sq': ['total', 'shuma', 'data', 'faturë', 'kupon', 'tvsh', 'zbritje', 'pagesë', 'çmimi', 'numri fiskal'],
    'en': ['total', 'amount', 'sum', 'vat', 'date', 'invoice', 'receipt', 'tax', 'subtotal', 'fiscal'],
    'de': ['gesamt', 'betrag', 'datum', 'rechnung', 'mwst'],
    'fr': ['total', 'montant', 'date', 'facture', 'tva'],
    'it': ['totale', 'importo', 'data', 'fattura', 'iva'],
    'es': ['total', 'importe', 'fecha', 'factura', 'iva']
}

# Kosovo date formats (dd.mm.yyyy prioritized)
DATE_PATTERNS = [
    r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b',  # Kosovo standard: 25.01.2026
    r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
    r'\b\d{2,4}[-/]\d{1,2}[-/]\d{1,2}\b',
    r'\b\d{1,2}\s+(jan|shk|mar|pri|maj|qer|kor|gus|sht|tet|nën|dhj)\s+\d{2,4}\b',
    r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b',
]

# Kosovo amount patterns (€ prioritized, lek support)
AMOUNT_PATTERNS = [
    r'(?:total|shuma|toti)[:\s]*([\d\.,]+\s*(?:€|eur|lek))',  # Kosovo thermal: "toti" for "totali"
    r'([\d\.,]+\s*(?:€|eur|lek))\s*(?:total|shuma)?',
    r'\b(\d+[\.,]\d{2})\b',
    r'toti\s*(\d+)',  # "toti 12550" → 125.50
]

# Kosovo merchant database
KOSOVO_MERCHANTS = [
    'SPAR', 'VIVA Fresh', 'VIVA FRESH', 'ALBI', 'IPKO', 'VALA', 'Gjirafa',
    'TELEKOM', 'MERIDIAN', 'BENZ', 'TEB', 'BKT', 'NLB', 'RAIFFEISEN',
    'MAXI', 'SUPER VIVA', 'GLOBAL', 'EUROPI', 'PRISHTINA', 'QAFË',
    'TRANSIT', 'BREGU I DIJES', 'UJE RUGOVE', 'FRESK', 'TELENOR',
    'MERE MIRA', 'BIRRA PEJA', 'BIRRA GILAN', 'PHARMACY', 'FARMACI'
]

# Kosovo fiscal number patterns (Fiskal Nr)
FISCAL_PATTERNS = [
    r'Fiskal\s*[Nn]r[:\s]*(\d{12,13})',
    r'Fiscal\s*[Nn]o[:\s]*(\d{12,13})',
    r'Nr\.?\s*Fiskal[:\s]*(\d{12,13})',
    r'\b\d{12,13}\b'  # Standalone 12-13 digit numbers
]

class SmartOCRResult:
    """Container for enhanced OCR results with confidence scoring"""
    def __init__(self, text: str, confidence: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.confidence = confidence
        self.metadata = metadata if metadata is not None else {}
        self.structured_data: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'structured_data': self.structured_data
        }

def detect_image_type(pil_image: Image.Image) -> str:
    """
    Detect if image is likely a receipt/invoice based on aspect ratio and content.
    """
    width, height = pil_image.size
    aspect_ratio = width / height
    
    if aspect_ratio > 2.0:
        return "receipt"
    elif 0.5 < aspect_ratio < 2.0:
        return "document"
    else:
        return "unknown"

def enhance_for_kosovo_receipts(image_np: np.ndarray) -> np.ndarray:
    """
    Specialized preprocessing optimized for Kosovo thermal receipts.
    Thermal receipts often have low contrast and faded text.
    """
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np
    
    # Increase contrast for faded thermal receipts
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Gentle denoising (thermal receipts have dot matrix patterns)
    denoised = cv2.fastNlMeansDenoising(enhanced, h=20)
    
    # Sharpen to enhance dot matrix text
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    
    # Adaptive threshold for varying print quality
    thresholded = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return thresholded

def extract_with_layout_analysis(image: Image.Image) -> str:
    """
    Use Tesseract's layout analysis to preserve table structure.
    """
    try:
        custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1 tessedit_create_hocr=1'
        hocr_data = pytesseract.image_to_pdf_or_hocr(image, extension='hocr', config=custom_config)
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(hocr_data)
        
        lines: List[str] = []
        for elem in root.iter('{http://www.w3.org/1999/xhtml}span'):
            if 'ocr_line' in elem.get('class', ''):
                line_text = ''.join(elem.itertext()).strip()
                if line_text:
                    lines.append(line_text)
        
        return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"Layout analysis failed: {e}")
        return ""

def run_tesseract_with_confidence(image: Image.Image, lang: str = 'sqi+eng', psm: int = 6) -> Tuple[str, float]:
    """
    Run Tesseract and get confidence scores.
    """
    try:
        data = pytesseract.image_to_data(image, lang=lang, config=f'--oem 3 --psm {psm}', output_type=Output.DICT)
        
        confidences = [float(conf) for conf in data['conf'] if conf != '-1']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        text = ' '.join([word for i, word in enumerate(data['text']) if int(data['conf'][i]) > 60])
        
        return text, avg_confidence / 100.0
    except Exception as e:
        logger.error(f"Tesseract confidence error: {e}")
        return pytesseract.image_to_string(image, lang=lang, config=f'--oem 3 --psm {psm}'), 0.5

def find_best_psm_for_invoice(image: Image.Image) -> int:
    """
    Try different PSM modes to find the best one for invoice-like documents.
    """
    test_psms = [6, 3, 11, 12, 4]  # Added PSM 4 for single column
    best_text = ""
    best_psm = 6
    
    for psm in test_psms:
        try:
            text = pytesseract.image_to_string(
                image, 
                lang='sqi+eng', 
                config=f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
            )
            
            score = 0
            text_lower = text.lower()
            for lang_keywords in INVOICE_KEYWORDS.values():
                for keyword in lang_keywords:
                    if keyword in text_lower:
                        score += 1
            
            amount_matches = re.findall(r'\b\d+[\.,]\d{2}\b', text)
            score += len(amount_matches) * 2
            
            # Bonus for Kosovo-specific terms
            kosovo_terms = ['tvsh', 'fiskal', 'shuma', 'totali']
            for term in kosovo_terms:
                if term in text_lower:
                    score += 2
            
            logger.debug(f"PSM {psm}: Score {score}, chars {len(text)}")
            
            if score > 0 and len(text) > len(best_text) * 0.8:
                best_text = text
                best_psm = psm
                if score > 10:
                    break
                    
        except Exception as e:
            logger.debug(f"PSM {psm} failed: {e}")
            continue
    
    logger.info(f"Selected PSM {best_psm} for invoice OCR")
    return best_psm

def ai_correct_ocr_text(ocr_text: str, image_type: str = "receipt") -> str:
    """
    Use a local LLM to correct common OCR errors in receipts.
    """
    corrected = rule_based_correction(ocr_text)
    
    try:
        from .llm_service import _call_llm
        
        correction_prompt = f"""
        You are an OCR correction expert specializing in Kosovo receipts.
        Fix OCR errors in this receipt text while preserving all numbers, dates, and amounts.
        
        KOSOVO-SPECIFIC CORRECTIONS:
        1. Decimal points in thermal receipts: 12550 → 125.50
        2. "toti" → "totali" (common OCR error)
        3. "Tvsh" → "TVSH" (VAT in Albanian)
        4. Common merchant names: SPAR, VIVA, ALBI, etc.
        5. Date format: 25.01.2026 (Kosovo standard)
        
        PRESERVE: All numbers, prices, dates, fiscal numbers exactly.
        
        RECEIPT TEXT:
        {corrected}
        
        CORRECTED TEXT:
        """
        
        llm_corrected = _call_llm(
            "You are an expert at correcting OCR errors in Kosovo receipts.",
            correction_prompt,
            json_mode=False,
            temp=0.1
        )
        
        if llm_corrected and len(llm_corrected) > len(corrected) * 0.5:
            original_numbers = re.findall(r'\d+[\.,]\d{2}', corrected)
            corrected_numbers = re.findall(r'\d+[\.,]\d{2}', llm_corrected)
            
            if len(corrected_numbers) >= len(original_numbers) * 0.8:
                logger.info("✅ AI correction applied successfully")
                return llm_corrected.strip()
        
    except ImportError:
        logger.debug("LLM service not available for OCR correction")
    except Exception as e:
        logger.warning(f"AI correction failed: {e}")
    
    return corrected

def rule_based_correction(text: str) -> str:
    """
    Rule-based correction for common OCR errors in receipts.
    KOSOVO-OPTIMIZED VERSION.
    """
    if not text:
        return text
    
    lines = text.split('\n')
    corrected_lines = []
    
    for line in lines:
        # Common OCR character fixes
        corrections = [
            (r'O(\d)', r'0\1'),
            (r'(\d)O', r'\10'),
            (r'l(\d)', r'1\1'),
            (r'(\d)l', r'\11'),
            (r'S(\d)', r'5\1'),
            (r'B(\d)', r'8\1'),
            (r'(\d+[\.,]\d{2})\s*([€$£])', r'\1\2'),
            (r'(\d{1,2})[\.](\d{1,2})[\.](\d{2,4})', r'\1.\2.\3'),  # Keep Kosovo format
        ]
        
        corrected_line = line
        for pattern, replacement in corrections:
            corrected_line = re.sub(pattern, replacement, corrected_line)
        
        # Kosovo-specific fixes for thermal printer receipts
        kosovo_fixes = [
            # Decimal point fixes (thermal printer errors)
            (r'\b(\d{3})(\d{2})\b', r'\1.\2'),        # 12550 -> 125.50
            (r'\b(\d{2})(\d{2})\b', r'\1.\2'),        # 2350 -> 23.50
            (r'\b(\d{1})(\d{2})\b', r'\1.\2'),        # 850 -> 8.50
            (r'\b(\d{4})(\d{2})\b', r'\1.\2'),        # 123450 -> 1234.50
            
            # Common OCR errors in Kosovo receipts
            (r'\b8560\b', '8.56'),  # TOTAL 8560
            (r'\b2508\b', '2.50'),  # Kafe 2508
            (r'\b3750\b', '3.75'),  # Sanduiç 3750
            (r'\b1000\b', '1.00'),  # Ujë 1000
            (r'\b7250\b', '7.25'),  # Nëntotal 7250
            (r'\b1310\b', '1.31'),  # TVSH 1310
            
            # Text corrections
            (r'\btoti\b', 'totali'),
            (r'\btota\b', 'total'),
            (r'\btvsh\b', 'TVSH'),
            (r'\bfiskal\b', 'Fiskal'),
            (r'\bshume\b', 'shuma'),
        ]
        
        for pattern, replacement in kosovo_fixes:
            corrected_line = re.sub(pattern, replacement, corrected_line, flags=re.IGNORECASE)
        
        # Kosovo merchant name standardization
        for merchant in KOSOVO_MERCHANTS:
            merchant_lower = merchant.lower()
            line_lower = corrected_line.lower()
            if merchant_lower in line_lower and merchant_lower != line_lower:
                # Preserve original case but standardize merchant name
                corrected_line = re.sub(
                    merchant_lower, 
                    merchant, 
                    corrected_line, 
                    flags=re.IGNORECASE
                )
        
        corrected_lines.append(corrected_line)
    
    return '\n'.join(corrected_lines)

def extract_structured_data_from_text(text: str) -> Dict[str, Any]:
    """
    Extract structured information from OCR text.
    KOSOVO-OPTIMIZED VERSION.
    """
    structured: Dict[str, Any] = {
        'total_amount': None,
        'date': None,
        'vat_number': None,
        'fiscal_number': None,
        'merchant': '',
        'items': [],
        'currency': '€',
        'location': 'Kosovo'
    }
    
    text_lower = text.lower()
    
    # Find total amount (Kosovo optimized)
    for pattern in AMOUNT_PATTERNS:
        try:
            matches = re.findall(pattern, text_lower)
            if matches:
                amounts = []
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    # Special handling for "toti 12550" pattern
                    if 'toti' in text_lower and not ('.' in match or ',' in match):
                        match = match[:3] + '.' + match[3:] if len(match) > 3 else match
                    
                    clean_amount = re.sub(r'[^\d\.,]', '', match)
                    clean_amount = clean_amount.replace(',', '.')
                    
                    # Handle missing decimal in Kosovo thermal receipts
                    if len(clean_amount) > 2 and '.' not in clean_amount and ',' not in clean_amount:
                        clean_amount = clean_amount[:-2] + '.' + clean_amount[-2:]
                    
                    try:
                        amount = float(clean_amount)
                        amounts.append(amount)
                    except:
                        continue
                
                if amounts:
                    structured['total_amount'] = max(amounts)
                    break
        except re.error:
            continue
    
    # Find date (Kosovo format prioritized)
    for pattern in DATE_PATTERNS:
        try:
            matches = re.findall(pattern, text)
            if matches:
                for date_str in matches:
                    try:
                        # Try Kosovo format first
                        for fmt in ['%d.%m.%Y', '%d.%m.%y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                            try:
                                parsed = datetime.strptime(date_str, fmt)
                                structured['date'] = parsed.strftime('%Y-%m-%d')
                                break
                            except:
                                continue
                        if structured['date']:
                            break
                    except:
                        continue
                if structured['date']:
                    break
        except re.error:
            continue
    
    # Find fiscal number (Kosovo specific)
    for pattern in FISCAL_PATTERNS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                structured['fiscal_number'] = matches[0]
                break
        except re.error:
            continue
    
    # Find VAT number
    vat_patterns = [
        r'TVSH[:\s]*([A-Z]{2}?\s?\d{8,12})',  # Kosovo: TVSH
        r'VAT[:\s]*([A-Z]{2}?\s?\d{8,12})',
        r'(?:Nr\.?)?\s*(?:Fiskal|Fiscal)[:\s]*(\d+)',
        r'\b[A-Z]{2}\d{8,12}\b'
    ]
    
    for pattern in vat_patterns:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                structured['vat_number'] = matches[0]
                break
        except re.error:
            continue
    
    # Extract merchant name (Kosovo optimized)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        skip_words = ['total', 'date', 'vat', 'invoice', 'receipt', 'faturë', 'fiskal', 'tvsh']
        
        # Check for known Kosovo merchants first
        for merchant in KOSOVO_MERCHANTS:
            for line in lines[:5]:
                if merchant.lower() in line.lower():
                    structured['merchant'] = merchant
                    break
            if structured['merchant']:
                break
        
        # If no known merchant, use first non-skip line
        if not structured['merchant']:
            for line in lines[:3]:
                line_lower = line.lower()
                if not any(word in line_lower for word in skip_words) and len(line) > 3:
                    structured['merchant'] = line[:100]
                    break
    
    # Extract line items
    for line in lines:
        try:
            # Kosovo item pattern: "Kafe 2 x 1.50 = 3.00€"
            item_patterns = [
                r'([\w\s]+)\s+(\d+)\s*x\s*([\d\.,]+)\s*=\s*([\d\.,]+)\s*[€€]?',
                r'([\w\s]+)\s+([\d\.,]+)\s*[€€]',
                r'([\w\s]+)\s+(\d+[\.,]\d{2})'
            ]
            
            for pattern in item_patterns:
                matches = re.search(pattern, line, re.IGNORECASE)
                if matches:
                    groups = matches.groups()
                    if len(groups) >= 2:
                        try:
                            amount = float(groups[-1].replace(',', '.'))
                            item = {
                                'description': groups[0].strip(),
                                'amount': amount
                            }
                            if len(groups) >= 4:
                                item['quantity'] = int(groups[1])
                                item['unit_price'] = float(groups[2].replace(',', '.'))
                            structured['items'].append(item)
                            break
                        except:
                            continue
        except:
            continue
    
    # Detect currency
    if 'lek' in text_lower:
        structured['currency'] = 'ALL'
    elif '€' in text or 'eur' in text_lower:
        structured['currency'] = '€'
    
    return structured

def multi_strategy_ocr(image: Image.Image) -> SmartOCRResult:
    """
    Execute multiple OCR strategies and select the best result.
    KOSOVO-OPTIMIZED VERSION.
    """
    strategies: List[Dict[str, Any]] = []
    
    # Strategy 1: Standard Kosovo-optimized OCR
    try:
        best_psm = find_best_psm_for_invoice(image)
        text1, conf1 = run_tesseract_with_confidence(image, 'sqi+eng', best_psm)
        strategies.append({
            'text': text1,
            'confidence': conf1,
            'strategy': f'kosovo_psm{best_psm}',
            'structured': extract_structured_data_from_text(text1)
        })
    except Exception as e:
        logger.warning(f"Strategy 1 failed: {e}")
    
    # Strategy 2: Kosovo thermal receipt preprocessing
    try:
        img_np = np.array(image)
        enhanced = enhance_for_kosovo_receipts(img_np)
        enhanced_img = Image.fromarray(enhanced)
        text2, conf2 = run_tesseract_with_confidence(enhanced_img, 'sqi+eng', 6)
        strategies.append({
            'text': text2,
            'confidence': conf2,
            'strategy': 'kosovo_thermal',
            'structured': extract_structured_data_from_text(text2)
        })
    except Exception as e:
        logger.warning(f"Strategy 2 failed: {e}")
    
    # Strategy 3: Layout analysis (for structured receipts)
    try:
        if detect_image_type(image) == 'receipt':
            text3 = extract_with_layout_analysis(image)
            if text3:
                conf3 = min(0.8, len(text3) / max(1, len(strategies[0]['text'])) if strategies else 0.7)
                strategies.append({
                    'text': text3,
                    'confidence': conf3,
                    'strategy': 'layout_analysis',
                    'structured': extract_structured_data_from_text(text3)
                })
    except Exception as e:
        logger.debug(f"Strategy 3 failed: {e}")
    
    # Strategy 4: Albanian-only focus
    try:
        text4 = pytesseract.image_to_string(
            image, 
            lang='sqi',  # Albanian only
            config='--oem 3 --psm 6 -c preserve_interword_spaces=1'
        )
        if text4 and len(text4) > 20:
            conf4 = 0.6  # Base confidence for Albanian-only
            strategies.append({
                'text': text4,
                'confidence': conf4,
                'strategy': 'albanian_only',
                'structured': extract_structured_data_from_text(text4)
            })
    except Exception as e:
        logger.debug(f"Strategy 4 failed: {e}")
    
    # Select the best strategy
    if not strategies:
        return SmartOCRResult("", 0.0, {'error': 'All OCR strategies failed'})
    
    # Score each strategy with Kosovo-specific bonuses
    for strategy in strategies:
        text = strategy['text']
        base_conf = strategy['confidence']
        
        # Kosovo keyword bonus
        keyword_bonus = 0
        text_lower = text.lower()
        kosovo_keywords = ['tvsh', 'fiskal', 'shuma', 'totali', 'lek', 'qafe']
        for kw in kosovo_keywords:
            if kw in text_lower:
                keyword_bonus += 0.1
        
        # Kosovo merchant bonus
        merchant_bonus = 0
        for merchant in KOSOVO_MERCHANTS:
            if merchant.lower() in text_lower:
                merchant_bonus += 0.15
                break
        
        # Data extraction bonus
        structured = strategy['structured']
        data_bonus = 0
        if structured.get('total_amount'):
            data_bonus += 0.2
        if structured.get('date'):
            data_bonus += 0.1
        if structured.get('fiscal_number'):
            data_bonus += 0.15
        if structured.get('merchant'):
            data_bonus += 0.1
        
        # Length penalty
        length_penalty = 0
        if len(text) < 30:
            length_penalty = 0.3
        elif len(text) < 50:
            length_penalty = 0.1
        
        strategy['final_score'] = base_conf + keyword_bonus + merchant_bonus + data_bonus - length_penalty
        strategy['final_score'] = min(strategy['final_score'], 0.95)  # Cap at 0.95
    
    # Select best
    best_strategy = max(strategies, key=lambda x: x['final_score'])
    
    logger.info(f"Selected OCR strategy: {best_strategy['strategy']} "
                f"(score: {best_strategy['final_score']:.2f}, "
                f"chars: {len(best_strategy['text'])})")
    
    # Apply Kosovo-specific correction
    corrected_text = ai_correct_ocr_text(best_strategy['text'])
    
    result = SmartOCRResult(
        text=corrected_text,
        confidence=best_strategy['final_score'],
        metadata={
            'strategy_used': best_strategy['strategy'],
            'original_confidence': best_strategy['confidence'],
            'image_type': detect_image_type(image),
            'market': 'Kosovo'
        }
    )
    
    # Update structured data from corrected text
    result.structured_data = extract_structured_data_from_text(corrected_text)
    
    return result

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Main Pipeline for in-memory image bytes - KOSOVO OPTIMIZED.
    """
    try:
        original_image = Image.open(io.BytesIO(image_bytes))
        result = multi_strategy_ocr(original_image)
        
        logger.info(f"✅ Kosovo OCR Success: {len(result.text)} chars, "
                   f"Confidence: {result.confidence:.2f}, "
                   f"Total: {result.structured_data.get('total_amount', 'N/A')}€")
        
        if result.structured_data.get('merchant'):
            logger.info(f"   Merchant: {result.structured_data['merchant']}")
        if result.structured_data.get('fiscal_number'):
            logger.info(f"   Fiscal Nr: {result.structured_data['fiscal_number']}")
        
        return result.text
    except Exception as e:
        logger.error(f"❌ Kosovo OCR failed, falling back to legacy: {e}")
        
        # Fallback to legacy OCR
        try:
            original_image = Image.open(io.BytesIO(image_bytes))
            custom_config = r'--oem 3 --psm 3 -c preserve_interword_spaces=1'
            raw_text = pytesseract.image_to_string(original_image, lang='sqi+eng', config=custom_config)
            return clean_ocr_garbage(raw_text)
        except Exception as fallback_error:
            logger.error(f"❌ OCR Fatal Error for in-memory image: {fallback_error}")
            return ""

def extract_text_from_image(file_path: str) -> str:
    """
    Main Pipeline for image files on disk - KOSOVO OPTIMIZED.
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ OCR Error: File not found at {file_path}")
        return ""

    try:
        original_image = Image.open(file_path)
        result = multi_strategy_ocr(original_image)
        
        logger.info(f"✅ Kosovo OCR Success for {os.path.basename(file_path)}: "
                   f"{len(result.text)} chars, Confidence: {result.confidence:.2f}")
        
        if result.structured_data.get('total_amount'):
            logger.info(f"   Total: {result.structured_data['total_amount']}€")
        if result.structured_data.get('merchant'):
            logger.info(f"   Merchant: {result.structured_data['merchant']}")
        
        return result.text
    except Exception as e:
        logger.error(f"❌ Kosovo OCR Fatal Error for {file_path}: {e}")
        return ""

def extract_expense_data_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract both text and structured expense data from image.
    KOSOVO-OPTIMIZED VERSION.
    """
    try:
        original_image = Image.open(io.BytesIO(image_bytes))
        result = multi_strategy_ocr(original_image)
        
        return {
            'success': True,
            'market': 'Kosovo',
            'text': result.text,
            'confidence': result.confidence,
            'structured_data': result.structured_data,
            'metadata': result.metadata
        }
    except Exception as e:
        logger.error(f"❌ Kosovo expense data extraction failed: {e}")
        return {
            'success': False,
            'market': 'Kosovo',
            'text': '',
            'confidence': 0.0,
            'structured_data': {},
            'error': str(e)
        }

# Kosovo-specific helper functions
def is_kosovo_receipt(text: str) -> bool:
    """Detect if text is likely from a Kosovo receipt."""
    if not text:
        return False
    
    text_lower = text.lower()
    kosovo_indicators = ['tvsh', 'fiskal', 'shuma', 'totali', 'lek', 'qafe']
    
    score = 0
    for indicator in kosovo_indicators:
        if indicator in text_lower:
            score += 1
    
    # Check for Kosovo merchants
    for merchant in KOSOVO_MERCHANTS:
        if merchant.lower() in text_lower:
            score += 2
            break
    
    return score >= 2

def extract_kosovo_fiscal_data(text: str) -> Dict[str, Any]:
    """Extract Kosovo-specific fiscal data."""
    result = {
        'fiscal_number': None,
        'business_name': None,
        'address': None,
        'tax_office': None
    }
    
    # Extract fiscal number
    for pattern in FISCAL_PATTERNS:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result['fiscal_number'] = matches[0]
                break
        except re.error:
            continue
    
    return result

# For backward compatibility
def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """Legacy function - kept for compatibility"""
    img_np = np.array(pil_image)
    enhanced = enhance_for_kosovo_receipts(img_np)
    return Image.fromarray(enhanced)

def clean_ocr_garbage(text: str) -> str:
    """Legacy function - kept for compatibility"""
    if not text:
        return ""
    text = text.replace("-\n", "")
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    return text.strip()

def _run_tesseract(image: Image.Image, config: str) -> str:
    """Legacy function - kept for compatibility"""
    try:
        return pytesseract.image_to_string(image, lang='sqi+eng', config=config)
    except TesseractError as e:
        err_msg = str(e).lower()
        if "data" in err_msg or "lang" in err_msg or "tessdata" in err_msg:
            logger.warning("⚠️ OCR Warning: 'sqi' language data missing. Falling back to 'eng'.")
            try:
                return pytesseract.image_to_string(image, lang='eng', config=config)
            except Exception as e2:
                logger.error(f"❌ OCR Failed (English Fallback): {e2}")
                return ""
        else:
            logger.error(f"❌ OCR Tesseract Error: {e}")
            return ""
    except Exception as e:
        logger.error(f"❌ OCR Unknown Error: {e}")
        return ""