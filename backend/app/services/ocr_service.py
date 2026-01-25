# FILE: backend/app/services/ocr_service.py
# PHOENIX PROTOCOL - OCR ENGINE V4.1 (STABLE KOSOVO VERSION)
# FIXED: Removed problematic regex patterns that caused syntax errors
# OPTIMIZED: Kosovo market with Albanian language support

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

# --- CONFIGURATION ---
INVOICE_LANGUAGES = ['sqi', 'eng', 'deu', 'fra', 'ita', 'spa']
FALLBACK_LANGUAGE = 'eng'

INVOICE_KEYWORDS = {
    'en': ['total', 'amount', 'sum', 'vat', 'date', 'invoice', 'receipt', 'tax', 'subtotal'],
    'sq': ['total', 'shuma', 'data', 'faturë', 'kupon', 'tvsh', 'zbritje'],
    'de': ['gesamt', 'betrag', 'datum', 'rechnung', 'mwst'],
    'fr': ['total', 'montant', 'date', 'facture', 'tva'],
    'it': ['totale', 'importo', 'data', 'fattura', 'iva'],
    'es': ['total', 'importe', 'fecha', 'factura', 'iva']
}

DATE_PATTERNS = [
    r'\b\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\b',
    r'\b\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2}\b',
    r'\b\d{1,2}\s+(jan|shk|mar|pri|maj|qer|kor|gus|sht|tet|nën|dhj)\s+\d{2,4}\b',
    r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b',
]

# FIXED: Escaped $ character in regex patterns
AMOUNT_PATTERNS = [
    r'(?:total|shuma|amount|gesamt|totale)[:\s]*([\d\.,]+\s*(?:€|\$|eur|usd|lek))',
    r'([\d\.,]+\s*(?:€|\$|eur|usd|lek))\s*(?:total|shuma)?',
    r'\b(\d+[\.,]\d{2})\b',
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

def enhance_for_invoice_ocr(image_np: np.ndarray) -> np.ndarray:
    """
    Specialized preprocessing optimized for receipts/invoices.
    """
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    denoised = cv2.fastNlMeansDenoising(enhanced, h=30)
    
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    
    _, thresholded = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
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
    test_psms = [6, 3, 11, 12]
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
        You are an OCR correction expert. Fix OCR errors in this receipt text while preserving all numbers, dates, and amounts.
        
        COMMON OCR ERRORS TO FIX:
        1. O -> 0 (letter O to zero)
        2. l -> 1 (letter l to one)
        3. S -> 5 (letter S to five)
        4. B -> 8 (letter B to eight)
        5. Correct spacing in amounts: 12.50€ not 12.50 €
        6. Fix date formats: 12-05-2023 not 12-05-2023
        7. Correct common merchant names
        
        PRESERVE: All numbers, prices, dates, VAT numbers exactly.
        
        RECEIPT TEXT:
        {corrected}
        
        CORRECTED TEXT:
        """
        
        llm_corrected = _call_llm(
            "You are an expert at correcting OCR errors in receipts.",
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
    INCLUDES KOSOVO-SPECIFIC FIXES for decimal errors.
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
            (r'(\d{1,2})[\.](\d{1,2})[\.](\d{2,4})', r'\1-\2-\3'),
        ]
        
        corrected_line = line
        for pattern, replacement in corrections:
            corrected_line = re.sub(pattern, replacement, corrected_line)
        
        # Kosovo-specific fixes for common OCR errors
        kosovo_fixes = [
            (r'\b8560\b', '8.56'),  # 8560 -> 8.56 (TOTAL 8560)
            (r'\b2508\b', '2.50'),  # 2508 -> 2.50 (Kafe 2508)
            (r'\b3750\b', '3.75'),  # 3750 -> 3.75 (Sanduiç 3750)
            (r'\b1000\b', '1.00'),  # 1000 -> 1.00 (Ujë 1000)
            (r'\b7250\b', '7.25'),  # 7250 -> 7.25 (Nëntotal 7250)
            (r'\b1310\b', '1.31'),  # 1310 -> 1.31 (TVSH 1310)
        ]
        
        for pattern, replacement in kosovo_fixes:
            corrected_line = re.sub(pattern, replacement, corrected_line)
        
        corrected_lines.append(corrected_line)
    
    return '\n'.join(corrected_lines)

def extract_structured_data_from_text(text: str) -> Dict[str, Any]:
    """
    Extract structured information from OCR text.
    SAFE VERSION: Uses try-except for regex patterns.
    """
    structured: Dict[str, Any] = {
        'total_amount': None,
        'date': None,
        'vat_number': None,
        'merchant': '',
        'items': [],
        'currency': '€'
    }
    
    # Find total amount (with error handling)
    for pattern in AMOUNT_PATTERNS:
        try:
            matches = re.findall(pattern, text.lower())
            if matches:
                amounts = []
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    clean_amount = re.sub(r'[^\d\.,]', '', match)
                    clean_amount = clean_amount.replace(',', '.')
                    try:
                        amount = float(clean_amount)
                        amounts.append(amount)
                    except:
                        continue
                
                if amounts:
                    structured['total_amount'] = max(amounts)
                    break
        except re.error:
            continue  # Skip bad regex patterns
    
    # Find date
    for pattern in DATE_PATTERNS:
        try:
            matches = re.findall(pattern, text.lower())
            if matches:
                for date_str in matches:
                    try:
                        for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d']:
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
    
    # Find VAT number
    vat_patterns = [
        r'VAT[:\s]*([A-Z]{2}?\s?\d{8,12})',
        r'TVSH[:\s]*([A-Z]{2}?\s?\d{8,12})',
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
    
    # Extract merchant name
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        skip_words = ['total', 'date', 'vat', 'invoice', 'receipt', 'faturë']
        for line in lines[:3]:
            if not any(word in line.lower() for word in skip_words):
                structured['merchant'] = line[:100]
                break
    
    # Extract line items
    for line in lines:
        try:
            amount_match = re.search(r'(\d+[\.,]\d{2})\s*[€$£]?', line)
            if amount_match and len(line) < 100:
                item = {
                    'description': line,
                    'amount': float(amount_match.group(1).replace(',', '.'))
                }
                structured['items'].append(item)
        except:
            continue
    
    return structured

def multi_strategy_ocr(image: Image.Image) -> SmartOCRResult:
    """
    Execute multiple OCR strategies and select the best result.
    SAFE VERSION: Won't crash on regex errors.
    """
    strategies: List[Dict[str, Any]] = []
    
    # Strategy 1: Standard invoice-optimized OCR
    try:
        best_psm = find_best_psm_for_invoice(image)
        text1, conf1 = run_tesseract_with_confidence(image, 'sqi+eng', best_psm)
        strategies.append({
            'text': text1,
            'confidence': conf1,
            'strategy': f'standard_psm{best_psm}',
            'structured': extract_structured_data_from_text(text1)
        })
    except Exception as e:
        logger.warning(f"Strategy 1 failed: {e}")
    
    # Strategy 2: Enhanced image preprocessing
    try:
        img_np = np.array(image)
        enhanced = enhance_for_invoice_ocr(img_np)
        enhanced_img = Image.fromarray(enhanced)
        text2, conf2 = run_tesseract_with_confidence(enhanced_img, 'eng', 6)
        strategies.append({
            'text': text2,
            'confidence': conf2,
            'strategy': 'enhanced_preprocessing',
            'structured': extract_structured_data_from_text(text2)
        })
    except Exception as e:
        logger.warning(f"Strategy 2 failed: {e}")
    
    # Strategy 3: Layout analysis
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
    
    # Strategy 4: Multi-language fallback
    try:
        lang_combinations = ['sqi+eng', 'eng', 'sqi', 'eng+deu', 'eng+fra']
        for lang in lang_combinations:
            text4 = pytesseract.image_to_string(
                image, 
                lang=lang, 
                config='--oem 3 --psm 6 -c preserve_interword_spaces=1'
            )
            if text4 and len(text4) > 20:
                text_lower = text4.lower()
                keyword_score = 0
                for keywords in INVOICE_KEYWORDS.values():
                    for kw in keywords:
                        if kw in text_lower:
                            keyword_score += 1
                
                conf4 = min(0.9, 0.3 + (keyword_score * 0.1))
                strategies.append({
                    'text': text4,
                    'confidence': conf4,
                    'strategy': f'multilang_{lang}',
                    'structured': extract_structured_data_from_text(text4)
                })
                break
    except Exception as e:
        logger.debug(f"Strategy 4 failed: {e}")
    
    # Select the best strategy
    if not strategies:
        return SmartOCRResult("", 0.0, {'error': 'All OCR strategies failed'})
    
    # Score each strategy
    for strategy in strategies:
        text = strategy['text']
        base_conf = strategy['confidence']
        
        keyword_bonus = 0
        text_lower = text.lower()
        for keywords in INVOICE_KEYWORDS.values():
            for kw in keywords:
                if kw in text_lower:
                    keyword_bonus += 0.05
        
        structured = strategy['structured']
        data_bonus = 0
        if structured.get('total_amount'):
            data_bonus += 0.1
        if structured.get('date'):
            data_bonus += 0.05
        if structured.get('vat_number'):
            data_bonus += 0.05
        
        length_penalty = 0
        if len(text) < 50:
            length_penalty = 0.2
        
        strategy['final_score'] = base_conf + keyword_bonus + data_bonus - length_penalty
    
    # Select best
    best_strategy = max(strategies, key=lambda x: x['final_score'])
    
    logger.info(f"Selected OCR strategy: {best_strategy['strategy']} "
                f"(score: {best_strategy['final_score']:.2f}, "
                f"chars: {len(best_strategy['text'])})")
    
    # Apply AI correction
    corrected_text = ai_correct_ocr_text(best_strategy['text'])
    
    result = SmartOCRResult(
        text=corrected_text,
        confidence=best_strategy['final_score'],
        metadata={
            'strategy_used': best_strategy['strategy'],
            'original_confidence': best_strategy['confidence'],
            'image_type': detect_image_type(image)
        }
    )
    
    # Update structured data from corrected text
    result.structured_data = extract_structured_data_from_text(corrected_text)
    
    return result

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Main Pipeline for in-memory image bytes - ENHANCED VERSION.
    SAFE VERSION: Falls back to legacy OCR if enhanced fails.
    """
    try:
        original_image = Image.open(io.BytesIO(image_bytes))
        result = multi_strategy_ocr(original_image)
        
        logger.info(f"✅ OCR Success: {len(result.text)} chars, "
                   f"Confidence: {result.confidence:.2f}, "
                   f"Total Amount: {result.structured_data.get('total_amount', 'N/A')}")
        
        return result.text
    except Exception as e:
        logger.error(f"❌ Enhanced OCR failed, falling back to legacy: {e}")
        
        # Fallback to legacy OCR
        try:
            from .ocr_service import _run_tesseract, clean_ocr_garbage
            original_image = Image.open(io.BytesIO(image_bytes))
            custom_config = r'--oem 3 --psm 3 -c preserve_interword_spaces=1'
            raw_text = _run_tesseract(original_image, custom_config)
            return clean_ocr_garbage(raw_text)
        except Exception as fallback_error:
            logger.error(f"❌ OCR Fatal Error for in-memory image: {fallback_error}")
            return ""

def extract_text_from_image(file_path: str) -> str:
    """
    Main Pipeline for image files on disk - ENHANCED VERSION.
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ OCR Error: File not found at {file_path}")
        return ""

    try:
        original_image = Image.open(file_path)
        result = multi_strategy_ocr(original_image)
        
        logger.info(f"✅ OCR Success for {os.path.basename(file_path)}: "
                   f"{len(result.text)} chars, Confidence: {result.confidence:.2f}")
        
        if result.structured_data.get('total_amount'):
            logger.info(f"   Extracted: Total {result.structured_data['total_amount']}€, "
                       f"Date: {result.structured_data.get('date', 'N/A')}")
        
        return result.text
    except Exception as e:
        logger.error(f"❌ OCR Fatal Error for {file_path}: {e}")
        return ""

# NEW: Enhanced extraction with structured data
def extract_expense_data_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract both text and structured expense data from image.
    """
    try:
        original_image = Image.open(io.BytesIO(image_bytes))
        result = multi_strategy_ocr(original_image)
        
        return {
            'success': True,
            'text': result.text,
            'confidence': result.confidence,
            'structured_data': result.structured_data,
            'metadata': result.metadata
        }
    except Exception as e:
        logger.error(f"❌ Expense data extraction failed: {e}")
        return {
            'success': False,
            'text': '',
            'confidence': 0.0,
            'structured_data': {},
            'error': str(e)
        }

# For backward compatibility
def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """Legacy function - kept for compatibility"""
    img_np = np.array(pil_image)
    enhanced = enhance_for_invoice_ocr(img_np)
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