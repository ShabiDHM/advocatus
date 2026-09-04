# FILE: backend/app/services/report_service/__init__.py
# PHOENIX PROTOCOL - REPORT SERVICE PACKAGE INITIALIZER (CLEAN MODULAR EXPORTS)

from .forensic_report import create_pdf_from_text
from .helpers import clean_text_for_pdf

try:
    from .invoice_report import generate_invoice_pdf
except ImportError:
    generate_invoice_pdf = None

__all__ = [
    "create_pdf_from_text",
    "generate_invoice_pdf",
    "clean_text_for_pdf"
]