# FILE: backend/app/services/text_extraction_service.py
# PHOENIX PROTOCOL - OCR & SEQUENTIAL DOCX ENGINE V17.0 (IN-LINE TABLES + REAL PAGE SEGMENTATION)
# 100% COMPLETE CODE • ZERO PY WARNINGS • BACKWARD COMPATIBLE SERVICE ADAPTER

import fitz
import logging
import os
import tempfile
import re
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Union

try:
    import docx
    from docx.document import Document as _DocxDocument
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError:
    docx = None

try: 
    from app.services.ocr_service import extract_text_from_image_bytes as advanced_bytes_ocr
except Exception:
    try:
        from .ocr_service import extract_text_from_image_bytes as advanced_bytes_ocr
    except Exception:
        advanced_bytes_ocr = None

logger = logging.getLogger(__name__)
FOOTER_PATTERN = re.compile(r'Rasti:\s*\S+\s*\|\s*Juristi AI System')

# OCR parallelization settings
OCR_WORKERS = int(os.environ.get("OCR_WORKERS", "4"))
OCR_PAGE_DELAY = float(os.environ.get("OCR_PAGE_DELAY", "0.0"))

def _sanitize_text(text: str) -> str: 
    return text.replace("\x00", "") if text else ""


def _strip_footer(text: str) -> str: 
    return '\n'.join([l for l in text.split('\n') if not FOOTER_PATTERN.search(l)])


def _extract_legacy_doc_text(file_path: str) -> str:
    """Extracts text from binary Word 97-2003 (.doc) files safely."""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        decoded_latin = content.decode('latin-1', errors='ignore')
        clean_blocks = re.findall(r'[\w\s\.,;:!?\(\)\[\]\/\-\–\—\+\@\#\%\&\=\"]{4,}', decoded_latin)
        extracted = "\n".join([b.strip() for b in clean_blocks if len(b.strip()) > 5])
        
        if extracted and len(extracted) > 50:
            return _sanitize_text(extracted)
    except Exception as e:
        logger.warning(f"Legacy .doc binary parser warning: {e}")

    return ""


def _extract_docx_headers_footers(doc) -> str:
    """Extract text from all headers and footers of a DOCX document."""
    header_footer_texts = []
    try:
        for section in doc.sections:
            for header in [section.header, section.first_page_header, section.even_page_header]:
                if header is not None and not header.is_linked_to_previous:
                    for para in header.paragraphs:
                        if para.text.strip():
                            header_footer_texts.append(f"[HEADER] {para.text.strip()}")
            for footer in [section.footer, section.first_page_footer, section.even_page_footer]:
                if footer is not None and not footer.is_linked_to_previous:
                    for para in footer.paragraphs:
                        if para.text.strip():
                            header_footer_texts.append(f"[FOOTER] {para.text.strip()}")
    except Exception as e:
        logger.warning(f"Header/footer extraction warning: {e}")

    return "\n".join(header_footer_texts)


def _extract_docx_text(file_path: str) -> str:
    """
    Ekstrakton tekstin nga .docx duke ruajtur renditjen kronologjike të paragrafëve dhe tabelave,
    si dhe duke segmentuar saktë faqet (--- [FAQJA X] ---) për Claude dhe sistemin RAG.
    """
    if not docx:
        return _extract_legacy_doc_text(file_path)

    try:
        doc = docx.Document(file_path)
        parts: List[str] = []

        headers_footers_text = _extract_docx_headers_footers(doc)
        if headers_footers_text:
            parts.append(headers_footers_text)

        current_page = 1
        parts.append(f"\n--- [FAQJA {current_page}] ---\n")

        char_count_in_page = 0
        PAGE_CHAR_THRESHOLD = 2300  # Mesatare e standardizuar për faqe ligjore A4

        # Përshkimi sekuencial i trupit të dokumentit (Paragrafët dhe Tabelat në renditje natyrale)
        for element in doc.element.body:
            if isinstance(element, CT_P):
                p = Paragraph(element, doc)
                text = p.text.strip()

                # Kontrollo për thyerje të qartë faqeje në XML të Word-it
                has_hard_page_break = bool(
                    element.xpath('.//w:br[@w:type="page"]') or 
                    element.xpath('.//w:lastRenderedPageBreak')
                )

                if has_hard_page_break and char_count_in_page > 150:
                    current_page += 1
                    parts.append(f"\n--- [FAQJA {current_page}] ---\n")
                    char_count_in_page = 0

                if text:
                    parts.append(text)
                    char_count_in_page += len(text)

                # Ndarje natyrale faqeje sipas vëllimit nëse Word nuk ka ruajtur hard break
                if char_count_in_page >= PAGE_CHAR_THRESHOLD:
                    current_page += 1
                    parts.append(f"\n--- [FAQJA {current_page}] ---\n")
                    char_count_in_page = 0

            elif isinstance(element, CT_Tbl):
                table = Table(element, doc)
                table_rows_text: List[str] = []

                for row in table.rows:
                    cell_values = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                    if any(cell_values):
                        table_rows_text.append("| " + " | ".join(cell_values) + " |")

                if table_rows_text:
                    col_count = len(table.rows[0].cells) if table.rows else 2
                    sep = "| " + " | ".join(["---"] * col_count) + " |"
                    formatted_table = [table_rows_text[0], sep] + table_rows_text[1:]
                    tbl_str = "\n".join(formatted_table)

                    parts.append("\n" + tbl_str + "\n")
                    char_count_in_page += len(tbl_str)

                    if char_count_in_page >= PAGE_CHAR_THRESHOLD:
                        current_page += 1
                        parts.append(f"\n--- [FAQJA {current_page}] ---\n")
                        char_count_in_page = 0

        full_text = "\n\n".join(parts) if parts else ""
        if full_text and len(full_text.strip()) > 0:
            logger.info(f"✅ [DOCX Sequential Extraction] U nxorën {len(full_text)} karaktere nga {current_page} faqe të identifikuara.")
            return _sanitize_text(full_text)

    except Exception as docx_err:
        logger.warning(f"python-docx sequential warning: {docx_err}")
        return _extract_legacy_doc_text(file_path)

    return _extract_legacy_doc_text(file_path)


def _ocr_single_page_bytes(page_num: int, jpeg_bytes: bytes) -> str:
    """Ekzekuton OCR me përpikëri të lartë për një faqe të vetme."""
    marker = f"\n--- [FAQJA {page_num + 1}] ---\n"
    if not advanced_bytes_ocr:
        return marker + "[SCANNED - NO OCR ENGINE AVAILABLE]"

    try:
        ocr_text = _sanitize_text(advanced_bytes_ocr(jpeg_bytes))
        if ocr_text and len(ocr_text.strip()) > 15:
            return marker + ocr_text.strip()
        return marker + "[Faqe pa tekst të dallueshëm]"
    except Exception as e:
        logger.error(f"❌ [OCR] Gabim në Faqen {page_num + 1}: {e}")
        return marker + ""


def _extract_text_from_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        total = len(doc)
        if total < 1: 
            doc.close()
            return ""
        
        pages_results: Dict[int, str] = {}
        pages_needing_ocr: List[Tuple[int, bytes]] = []

        # Pass 1: Digital Text Extraction
        for i in range(total):
            page = doc[i]
            digital_text = _strip_footer(_sanitize_text("\n".join([b[4] for b in sorted(page.get_text("blocks"), key=lambda b: (int(b[1]/3), int(b[0])))])))
            
            if digital_text and len(digital_text.strip()) > 100:
                pages_results[i] = f"\n--- [FAQJA {i + 1}] ---\n" + digital_text.strip()
            else:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                jpeg_bytes = pix.tobytes("jpeg", jpg_quality=92)
                pages_needing_ocr.append((i, jpeg_bytes))

        doc.close()

        # Pass 2: PHOENIX PARALLEL OCR (thread pool)
        if pages_needing_ocr:
            logger.info(f"📄 [OCR Parallel] Filloi leximi i {len(pages_needing_ocr)} faqeve të skanuara me {OCR_WORKERS} punëtorë...")
            with ThreadPoolExecutor(max_workers=OCR_WORKERS) as executor:
                future_to_page = {
                    executor.submit(_ocr_single_page_bytes, page_num, j_bytes): page_num
                    for page_num, j_bytes in pages_needing_ocr
                }
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        pages_results[page_num] = future.result()
                    except Exception as exc:
                        logger.error(f"❌ [OCR] Faqja {page_num + 1} dështoi: {exc}")
                        pages_results[page_num] = f"\n--- [FAQJA {page_num + 1}] ---\n[Gabim OCR]"

            if OCR_PAGE_DELAY > 0:
                time.sleep(OCR_PAGE_DELAY)

        ordered_text = "\n\n".join([pages_results[i] for i in range(total) if i in pages_results])
        logger.info(f"✅ [PDF Extraction Complete] U nxorën gjithsej {len(ordered_text)} karaktere nga {total} faqe.")
        return ordered_text

    except Exception as e:
        logger.error(f"❌ PDF Extraction Failed: {e}")
        return ""


def _ensure_string_path(file_path: Union[str, bytes, os.PathLike]) -> str:
    if isinstance(file_path, bytes):
        return file_path.decode('utf-8', errors='ignore')
    if isinstance(file_path, os.PathLike):
        return str(file_path)
    return str(file_path)


def extract_text(file_path: Union[str, bytes, os.PathLike], mime_type: str = "") -> str:
    path_str = _ensure_string_path(file_path)
    file_name_lower = path_str.lower()
    mime_lower = (mime_type or "").lower()

    # PDF
    if "pdf" in mime_lower or file_name_lower.endswith(".pdf"):
        return _extract_text_from_pdf(path_str)

    # WORD DOCUMENTS (.docx & legacy .doc)
    if ("word" in mime_lower or 
        "officedocument" in mime_lower or 
        file_name_lower.endswith(".docx") or 
        file_name_lower.endswith(".doc") or 
        mime_lower == "application/msword"):
        return _extract_docx_text(path_str)

    # DIRECT IMAGE OCR SUPPORT (.jpg, .jpeg, .png, .webp)
    if (any(mime_lower.startswith(img_t) for img_t in ["image/jpeg", "image/png", "image/webp", "image/jpg"]) or 
        any(file_name_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])):
        if advanced_bytes_ocr:
            try:
                with open(path_str, "rb") as img_f:
                    img_bytes = img_f.read()
                return _sanitize_text(advanced_bytes_ocr(img_bytes))
            except Exception as img_err:
                logger.error(f"❌ Direct Image OCR Error: {img_err}")
        return ""

    # EXCEL
    if "excel" in mime_lower or "spreadsheet" in mime_lower or file_name_lower.endswith(".xlsx") or file_name_lower.endswith(".xls"):
        try:
            import pandas as pd
            return _sanitize_text("\n".join(df.to_string() for _, df in pd.read_excel(path_str, sheet_name=None).items()))
        except Exception:
            return ""

    return ""


def extract_text_from_file(file_obj: io.BytesIO, file_type: str = "PDF") -> str:
    with tempfile.NamedTemporaryFile(suffix=f".{file_type.lower()}", delete=False) as tmp:
        tmp.write(file_obj.getvalue())
        path = tmp.name
    try: 
        return extract_text(path, file_type)
    finally:
        if os.path.exists(path): 
            try:
                os.remove(path)
            except Exception:
                pass


class TextExtractionService:
    """Shërbimi qendror i nxjerrjes së tekstit dhe OCR-it."""
    
    @staticmethod
    def extract_text(file_path: Union[str, bytes, os.PathLike], mime_type: str = "") -> str:
        return extract_text(file_path, mime_type)

    @staticmethod
    def extract_text_from_file(file_obj: io.BytesIO, file_type: str = "PDF") -> str:
        return extract_text_from_file(file_obj, file_type)

    def __call__(self, file_path: Union[str, bytes, os.PathLike], mime_type: str = "") -> str:
        return extract_text(file_path, mime_type)


text_extraction_service = TextExtractionService()