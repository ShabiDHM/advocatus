# FILE: backend/app/services/report_service/__init__.py
# PHOENIX PROTOCOL - REPORT SERVICE PACKAGE REGISTRY

from .helpers import clean_text_for_pdf, _get_text, _get_branding
from .strategy_report import create_pdf_from_text, generate_legal_strategy_report
from .invoice_report import generate_invoice_pdf
from .evidence_map_report import generate_evidence_map_report

__all__ = [
    "clean_text_for_pdf",
    "_get_text",
    "_get_branding",
    "create_pdf_from_text",
    "generate_legal_strategy_report",
    "generate_invoice_pdf",
    "generate_evidence_map_report"
]