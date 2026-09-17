# FILE: backend/app/services/report_service/__init__.py
# PHOENIX PROTOCOL - REPORT SERVICE PACKAGE INITIALIZER V2.0
# V2.0: Hequr importi i forensic_report (create_pdf_from_text) — feature e fshirë.

from .helpers import clean_text_for_pdf

try:
    from .invoice_report import generate_invoice_pdf
except ImportError:
    generate_invoice_pdf = None

__all__ = [
    "generate_invoice_pdf",
    "clean_text_for_pdf"
]