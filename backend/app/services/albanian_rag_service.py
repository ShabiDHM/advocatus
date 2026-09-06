# FILE: backend/app/services/albanian_rag_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI DOKTRINAR RAG V261.0 (INTEGRAL 31-DOC DOSSIER INGESTION FOR CASE ANALYSIS)
# 100% I PLOTË • ZERO TRUNCATION • GJUHË E PAZTËR JURIDIKE SHQIPE • ZERO TS/PYTHON WARNINGS

import os
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings

# Modulet RAG
from app.services.rag.intent_detector import IntentDetector
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.response_generator import ResponseGenerator
from app.services.pillars.base_pillar_service import BasePillarService

# Importimi i Shtyllave Kryesore Elitare
from app.services.pillars.forensic_audit_service import ForensicAuditService
from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.comprehensive_analysis_service import ComprehensiveAnalysisService

logger = logging.getLogger(__name__)

MANDATORY_LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n"
    "*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Juristi AI për qëllime informative, "
    "kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i "
    "Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin "
    "pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*"
)

ANTI_HALLUCINATION_INSTRUCTION = """
RREGULLAT E HEKURTA TË DOKTRINËS DHE HARTIMIT:
1. CITO NENET me saktësi absolute neni-për-nen duke u mbështetur në shkresat e fashikullit dhe ligjet e Kosovës.
2. MOS shpik fakte, data apo shuma që nuk figurojnë në fashikull.
3. Përpilo dhe harto gjithmonë aktin e kërkuar procedural duke shfrytëzuar të gjitha provat e administruara në dosje.
4. Përdor ligjet pozitive të Kosovës: LPK Nr. 03/L-006, LMD Nr. 04/L-077, KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LSHT Nr. 06/L-016, Ligji për Gjykatën Komerciale Nr. 08/L-015, Ligji për PSRK Nr. 03/L-052.
"""


def is_valid_legal_report(text: str) -> bool:
    """Verifikon që përgjigja është një raport i vërtetë gjyqësor dhe JO një gabim teknik."""
    if not text or len(text.strip()) < 150:
        return False
    
    lower_text = text.lower()
    error_markers = [
        "përkohësisht i ngarkuar",
        "error code:",
        "context_length_exceeded",
        "not a valid model",
        "no endpoints found",
        "gabim teknik"
    ]
    for marker in error_markers:
        if marker in lower_text:
            return False
            
    return True


def detect_requested_pillar(query_lower: str) -> Optional[str]:
    """Identifikon saktë cilën shtjellë po kërkon përdoruesi nga prompt-i."""
    if "shtjella 1" in query_lower or "shtjella_1" in query_lower or "ekzaminimi" in query_lower or "fakti" in query_lower:
        return "PILLAR_1"
    if "shtjella 2" in query_lower or "shtjella_2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower:
        return "PILLAR_2"
    if "shtjella 3" in query_lower or "shtjella_3" in query_lower or "kundërshtimet" in query_lower or "plani" in query_lower:
        return "PILLAR_3"
    return None


class AlbanianRAGService:
    """Shërbimi Kryesor RAG — V261.0 me Ngarkim Integral të të Gjitha Shkresave të Lëndës."""

    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info("✅ [RAG] Juristi AI Service V261.0 Initialized.")

    def _optimize_query(self, query: str) -> str:
        cleaned = query.strip()
        preambles = [
            r"^\s*më\s+trego\s+rreth\s+",
            r"^\s*më\s+trego\s+për\s+",
            r"^\s*a\s+mund\s+të\s+më\s+ndihmosh\s+me\s+",
            r"^\s*ju\s+lutem\s+më\s+gjej\s+",
            r"^\s*kërko\s+për\s+",
            r"^\s*gjej\s+nenin\s+",
        ]
        for preamble in preambles:
            cleaned = re.sub(preamble, "", cleaned, flags=re.IGNORECASE)
        
        abbreviations = {
            r"\bLMD\b": "Ligji për Marrëdhëniet e Detyrimeve",
            r"\bLSHT\b": "Ligji për Shoqëritë Tregtare",
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            r"\bKPPRK\b": "Kodi i Procedurës Penale të Kosovës",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLFK\b": "Ligji për Familjen i Kosovës",
            r"\bPSRK\b": "Prokuroria Speciale e Republikës së Kosovës",
        }
        for abbr, expansion in abbreviations.items():
            cleaned = re.sub(abbr, f"{abbr} ({expansion})", cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    async def chat(
        self,
        query: str,
        user_id: str,
        case_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        jurisdiction: str = 'ks',
        history: Optional[List[Dict[str, Any]]] = None,
        domain: Optional[str] = 'automatic'
    ) -> AsyncGenerator[str, None]:
        
        current_date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

        client_position = "PALË NË PROCEDURË"
        client_name = "Klienti / Parashtruesi"
        case_title = "Lënda Ligjore"
        db_documents = []
        case_doc = None
        c_oid = None

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    case_title = case_doc.get("title") or case_doc.get("case_name") or case_title

                # Ngarkojmë shkresat sipas kërkesës
                doc_filter: Dict[str, Any] = {
                    "$or": [{"case_id": case_id}, {"case_id": c_oid}],
                    "status": {"$ne": "DELETED"}
                }

                if document_ids and len(document_ids) > 0:
                    doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                    doc_strs = [str(did) for did in document_ids]
                    doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                db_documents = list(self.db.documents.find(doc_filter).sort([("created_at", 1), ("date", 1)]))
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        # Dokument i vetëm është VETËM nëse përdoruesi ka specifikuar 1 documentId
        single_doc_obj = db_documents[0] if (document_ids and len(document_ids) == 1 and db_documents) else None

        from app.services import vector_store_service
        query_lower = query.lower()
        optimized_query = self._optimize_query(query)
        req_pillar = detect_requested_pillar(query_lower)

        # =========================================================================
        # 🎯 PHOENIX CLASSIFIER: IDENTIFIKIMI I SAKTË I ANALIZËS SË RASTIT
        # =========================================================================
        is_case_wide_request = any(kw in query_lower for kw in [
            "analizo rastin", "analizë e rastit", "analizë standarde e rastit",
            "pasqyra ekzekutive e lëndës", "pasqyra e lëndës", "raportin master",
            "autopsi e plotë", "fashikull", "gjithë fashikullit"
        ])

        if single_doc_obj is not None and not is_case_wide_request:
            user_intent = "FORENSIC_AUDIT"
        elif is_case_wide_request:
            user_intent = "COMPREHENSIVE_ANALYSIS"
            single_doc_obj = None  # Sigurojmë që të përfshihet i gjithë fashikulli me të 31 shkresat
        else:
            user_intent = IntentDetector.detect(query)

        sample_text = ""
        if single_doc_obj:
            sample_text = (single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or "")[:5000]
        elif db_documents:
            sample_text = " ".join([(d.get("content") or d.get("extracted_text") or "")[:1500] for d in db_documents[:5]])

        detected_domain = BasePillarService.detect_case_domain(
            case_title=case_title,
            context_str=sample_text,
            manifest_str=""
        )

        # =========================================================================
        # ⚡ SMART CACHE CHECK (0ms VETËM NËSE KA CACHE EKZISTUES)
        # =========================================================================

        # 1. KONTROLLI I SHTJELLËS SË DOKUMENTIT TË VETËM
        if user_intent == "FORENSIC_AUDIT" and single_doc_obj:
            doc_pillars = single_doc_obj.get("forensic_pillars") or {}
            
            if req_pillar and doc_pillars.get(req_pillar):
                cached_text = doc_pillars[req_pillar]
                if is_valid_legal_report(cached_text):
                    logger.info(f"⚡ [Smart Cache HIT - 0ms] Kthehet {req_pillar} për dokumentin: {single_doc_obj.get('file_name', single_doc_obj.get('_id'))}")
                    yield cached_text
                    yield MANDATORY_LEGAL_DISCLAIMER
                    return
            elif not req_pillar:
                cached_doc_audit = single_doc_obj.get("latest_analysis") or single_doc_obj.get("latest_forensic_audit")
                if cached_doc_audit and is_valid_legal_report(cached_doc_audit):
                    logger.info(f"⚡ [Smart Cache HIT - 0ms] Kthehet latest_analysis për dokumentin: {single_doc_obj.get('file_name', single_doc_obj.get('_id'))}")
                    yield cached_doc_audit
                    yield MANDATORY_LEGAL_DISCLAIMER
                    return

        # 2. KONTROLLI I SHTJELLËS SË LËNDËS (VETËM KUR KËRKOHET NGA ZYRA FORENZIKE)
        elif user_intent == "COMPREHENSIVE_ANALYSIS" and case_doc and not single_doc_obj:
            is_dirty = case_doc.get("analysis_dirty", False)
            forensic_pillars = case_doc.get("forensic_pillars") or {}

            # Vetëm nëse kërkohet shtjellë specifike forenzike me Sonnet
            if not is_dirty and req_pillar and forensic_pillars.get(req_pillar):
                cached_pillar = forensic_pillars[req_pillar]
                if is_valid_legal_report(cached_pillar):
                    logger.info(f"⚡ [Smart Cache HIT - 0ms] Kthehet {req_pillar} për lëndën {case_id}.")
                    yield cached_pillar
                    yield MANDATORY_LEGAL_DISCLAIMER
                    return

        # =========================================================================
        # 🔍 FILLON GJENERIMI I RI NGA AI
        # =========================================================================
        exec_query = optimized_query
        system_prompt = ""

        if user_intent == "FORENSIC_AUDIT":
            doc_text = ""
            if single_doc_obj:
                doc_text = single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or ""
            
            if not doc_text and db_documents:
                doc_text = db_documents[0].get("content") or db_documents[0].get("extracted_text") or ""

            doc_name = single_doc_obj.get('file_name', 'Dokument Gjyqësor') if single_doc_obj else 'Dokument'
            manifest_str = f"Dokumenti në Audit: {doc_name}"
            
            base_prompt = ForensicAuditService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=doc_text,
                document_text=doc_text,
                manifest_str=manifest_str,
                case_domain=detected_domain,
                query_text=optimized_query,
                db=self.db,
                user_id=user_id,
                case_id=""
            )
            system_prompt = base_prompt
            exec_query = optimized_query

        elif user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            # INTEGRIMI I TË GJITHA 31 SHKRESAVE TË FASHIKULLIT
            dossier_blocks = []
            manifest_lines = []

            for idx, doc in enumerate(db_documents, 1):
                doc_title = doc.get("file_name") or doc.get("title") or f"Dokumenti #{idx}"
                doc_text = (doc.get("content") or doc.get("extracted_text") or doc.get("text") or "").strip()
                doc_date = doc.get("document_date") or doc.get("created_at") or ""
                if hasattr(doc_date, "strftime"):
                    doc_date = doc_date.strftime("%d.%m.%Y")
                
                manifest_lines.append(f"{idx}. {doc_title} (Data/Ref: {doc_date})")
                dossier_blocks.append(
                    f"======================================================================\n"
                    f"SHKRESA #{idx} NË FASHIKULL: {doc_title} | DATA: {doc_date}\n"
                    f"======================================================================\n"
                    f"{doc_text}\n"
                )

            if dossier_blocks:
                integral_context_str = "\n".join(dossier_blocks)
                manifest_str = "\n".join(manifest_lines)
            else:
                case_docs = vector_store_service.query_case_knowledge_base(
                    user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=25
                )
                global_docs = vector_store_service.query_global_knowledge_base(
                    query_text=optimized_query, n_results=15
                )
                manifest_str, integral_context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            base_prompt = ComprehensiveAnalysisService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=integral_context_str,
                case_domain=detected_domain,
                db=self.db,
                query_text=optimized_query,
                user_id=user_id,
                case_id=case_id
            )
            system_prompt = base_prompt
            exec_query = optimized_query

        elif user_intent == "DRAFTING":
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=15
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            base_prompt = LegalDraftingService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str,
                query=optimized_query,
                case_domain=detected_domain,
                db=self.db,
                user_id=user_id,
                case_id=case_id
            )
            system_prompt = base_prompt
            exec_query = f"Harto aktin e plotë procedural të kërkuar ({optimized_query}) me strukturë solemne gjyqësore."
        else:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=15
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor Inteligjent dhe Eksperti Kryesor i Doktrinës Ligjore në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {ANTI_HALLUCINATION_INSTRUCTION}

            DOKUMENTET DHE PROVAT E FASHIKULLIT:
            {manifest_str}
            {context_str}
            """

        # Gjenerimi i Përgjigjes me Stream
        full_generated_response = ""
        async for content in self.response_generator.generate_stream(system_prompt, exec_query, context=""):
            full_generated_response += content
            yield content

        # =========================================================================
        # 💾 RUAJTJA AUTOMATIKE PAS GJENERIMIT
        # =========================================================================
        if is_valid_legal_report(full_generated_response):
            if single_doc_obj and self.db is not None:
                save_doc_key = req_pillar or "PILLAR_1"
                try:
                    self.db.documents.update_one(
                        {"_id": single_doc_obj["_id"]},
                        {"$set": {
                            f"forensic_pillars.{save_doc_key}": full_generated_response.strip(),
                            "latest_analysis": full_generated_response.strip(),
                            "latest_forensic_audit": full_generated_response.strip(),
                            "last_audited_at": datetime.now(timezone.utc)
                        }}
                    )
                    logger.info(f"💾 [Auto-Cache SUCCESS] U ruajt forensic_pillars.{save_doc_key} për dokumentin {single_doc_obj.get('_id')}!")
                except Exception as save_err:
                    logger.warning(f"Could not cache doc pillar: {save_err}")

            elif user_intent == "COMPREHENSIVE_ANALYSIS" and c_oid and self.db is not None and not single_doc_obj:
                save_case_key = req_pillar or "PILLAR_1"
                try:
                    self.db.cases.update_one(
                        {"_id": c_oid},
                        {"$set": {
                            f"forensic_pillars.{save_case_key}": full_generated_response.strip(),
                            "latest_deep_analysis": full_generated_response.strip(),
                            "analysis_dirty": False,
                            "last_analyzed_at": datetime.now(timezone.utc)
                        }}
                    )
                    logger.info(f"💾 [Auto-Cache SUCCESS] U ruajt forensic_pillars.{save_case_key} në MongoDB për lëndën {case_id}!")
                except Exception as save_err:
                    logger.warning(f"Could not cache case pillar: {save_err}")

        yield MANDATORY_LEGAL_DISCLAIMER