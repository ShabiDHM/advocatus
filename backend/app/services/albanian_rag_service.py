# FILE: backend/app/services/albanian_rag_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI DOKTRINAR RAG V269.0 (FULL 31-DOC DOSSIER & 147-PAGE VERBATIM ENGINE)
# 100% I PLOTË • ZERO ARTIFICIAL LIMITS • EXCLUSIVE DEEPSEEK CORE • MONGO ATLAS ATOMIC SYNC

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

# Shtyllat e Pavarura
from app.services.pillars.forensic_audit_service import ForensicAuditService
from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.statutory_verification_service import StatutoryVerificationService

logger = logging.getLogger(__name__)

CASE_CHAT_HISTORY_COLLECTION = "case_chat_history"

MANDATORY_LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n"
    "*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Juristi AI për qëllime informative, "
    "kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i "
    "Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin "
    "pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*"
)

# 🛑 PHOENIX: RREGULLA TË PRERA PËR DEEPSEEK NË FASHIKULLIN E PLOTË
ANTI_HALLUCINATION_INSTRUCTION = """
RREGULLAT E HEKURTA TË DOKTRINËS DHE KONSULENCËS (KUSHTE ABSOLUTE):
1. QASJE E PLOTË NË TË GJITHË FASHIKULLIN:
   Para syve tuaj ndodhet I GJITHË FASHIKULLI I LËNDËS (të gjitha shkresat dhe faqet e zbardhura fjalë për fjalë). NDALOHET kategorikisht të thoni "kam vetëm fragmente" ose "nuk më jepen faqet e brendshme", sepse e keni të gjithë materialin më poshtë!
2. CITIM VERBATIM ME NUMËR FAQEJE:
   Citoni me thonjëza deklarimet ekzakte të palëve, ekspertëve dhe dëshmitarëve, duke treguar emrin e shkresës dhe faqen përkatëse.
3. PËRGJIGJE DIREKTE PA MARKETING:
   MOS shkruaj konfirmime si "E kuptova", "Jam gati", "Keni të drejtë". Fillo direkt me thelbin e analizës juridike.
4. MBROJTJA E INTERESIT TË KLIENTIT:
   Cito nenet neni-për-nen sipas ligjeve pozitive të Kosovës: LPK Nr. 03/L-006, LMD Nr. 04/L-077, KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LSHT Nr. 06/L-016.
"""

def is_valid_legal_report(text: str) -> bool:
    if not text or len(text.strip()) < 150:
        return False
    
    lower_text = text.lower()
    error_markers = [
        "përkohësisht i ngarkuar",
        "error code:",
        "context_length_exceeded",
        "max_num_tokens",
        "upstream error",
        "not a valid model",
        "no endpoints found",
        "gabim teknik"
    ]
    for marker in error_markers:
        if marker in lower_text:
            return False
            
    return True


def detect_requested_pillar(query_lower: str) -> Optional[str]:
    if "shtjella 1" in query_lower or "shtjella_1" in query_lower or "ekzaminimi" in query_lower or "fakti" in query_lower:
        return "PILLAR_1"
    if "shtjella 2" in query_lower or "shtjella_2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower:
        return "PILLAR_2"
    if "shtjella 3" in query_lower or "shtjella_3" in query_lower or "kundërshtimet" in query_lower or "plani" in query_lower:
        return "PILLAR_3"
    return None


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info("✅ [RAG] Juristi AI Full-Dossier Service V269.0 Initialized.")

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

                doc_filter: Dict[str, Any] = {
                    "$or": [{"case_id": case_id}, {"case_id": c_oid}],
                    "status": {"$ne": "DELETED"}
                }

                if document_ids and len(document_ids) > 0:
                    doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                    doc_strs = [str(did) for did in document_ids]
                    doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                # TËRHIQEN TË GJITHA SHKRESAT PA KUFIZIM
                db_documents = list(self.db.documents.find(doc_filter).sort([("created_at", 1), ("_id", 1)]))
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        # Historiku i bisedës
        if history is None and self.db is not None and case_id and user_id:
            try:
                past_cursor = self.db[CASE_CHAT_HISTORY_COLLECTION].find({
                    "user_id": str(user_id),
                    "case_id": str(case_id)
                }).sort("created_at", -1).limit(10)
                
                raw_hist = list(past_cursor)
                raw_hist.reverse()

                history = []
                for h in raw_hist:
                    history.append({
                        "role": h.get("role", "user"),
                        "content": h.get("content", "")
                    })
            except Exception as e:
                logger.warning(f"Could not load case chat history: {e}")
                history = []

        single_doc_obj = db_documents[0] if (document_ids and len(document_ids) == 1 and db_documents) else None

        from app.services import vector_store_service
        query_lower = query.lower()
        optimized_query = self._optimize_query(query)
        req_pillar = detect_requested_pillar(query_lower)

        is_case_wide_request = any(kw in query_lower for kw in [
            "analizo rastin", "analizë e rastit", "analizë standarde e rastit",
            "pasqyra ekzekutive e lëndës", "pasqyra e lëndës", "raportin master",
            "autopsi e plotë", "fashikull", "gjithë fashikullit", "shkeljet", "kronologjia"
        ])

        is_statutory_verification = any(kw in query_lower for kw in [
            "verifiko nenet", "a janë të sakta nenet", "referencat ligjore", 
            "baza ligjore", "nenet e ligjit", "nxirr nenet", "kontrollo nenet"
        ])

        if single_doc_obj and not is_case_wide_request and not is_statutory_verification:
            user_intent = "FORENSIC_AUDIT"
        elif is_case_wide_request:
            user_intent = "COMPREHENSIVE_ANALYSIS"
            single_doc_obj = None
        elif is_statutory_verification:
            user_intent = "STATUTORY_VERIFICATION"
        else:
            user_intent = IntentDetector.detect(query)

        # Shembull konteksti i lëndës nga të gjitha shkresat
        sample_text = ""
        if single_doc_obj:
            sample_text = (single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or "")[:10000]
        elif db_documents:
            sample_text = " ".join([(d.get("content") or d.get("extracted_text") or "")[:2000] for d in db_documents])

        detected_domain = BasePillarService.detect_case_domain(
            case_title=case_title,
            context_str=sample_text,
            manifest_str=""
        )

        # Smart Cache
        if user_intent == "FORENSIC_AUDIT" and single_doc_obj:
            doc_pillars = single_doc_obj.get("forensic_pillars") or {}
            if req_pillar and doc_pillars.get(req_pillar):
                cached_text = doc_pillars[req_pillar]
                if is_valid_legal_report(cached_text):
                    logger.info(f"⚡ [Smart Cache HIT - 0ms] Kthehet {req_pillar} për dokumentin.")
                    if self.db is not None and case_id and user_id:
                        self.db[CASE_CHAT_HISTORY_COLLECTION].insert_many([
                            {"user_id": str(user_id), "case_id": str(case_id), "role": "user", "content": query, "created_at": datetime.now(timezone.utc)},
                            {"user_id": str(user_id), "case_id": str(case_id), "role": "assistant", "content": cached_text, "created_at": datetime.now(timezone.utc)}
                        ])
                    yield cached_text
                    yield MANDATORY_LEGAL_DISCLAIMER
                    return

        elif user_intent == "COMPREHENSIVE_ANALYSIS" and case_doc and not single_doc_obj:
            is_dirty = case_doc.get("analysis_dirty", False)
            forensic_pillars = case_doc.get("forensic_pillars") or {}
            if not is_dirty and req_pillar and forensic_pillars.get(req_pillar):
                cached_pillar = forensic_pillars[req_pillar]
                if is_valid_legal_report(cached_pillar):
                    logger.info(f"⚡ [Smart Cache HIT - 0ms] Kthehet {req_pillar} për lëndën {case_id}.")
                    if self.db is not None and case_id and user_id:
                        self.db[CASE_CHAT_HISTORY_COLLECTION].insert_many([
                            {"user_id": str(user_id), "case_id": str(case_id), "role": "user", "content": query, "created_at": datetime.now(timezone.utc)},
                            {"user_id": str(user_id), "case_id": str(case_id), "role": "assistant", "content": cached_pillar, "created_at": datetime.now(timezone.utc)}
                        ])
                    yield cached_pillar
                    yield MANDATORY_LEGAL_DISCLAIMER
                    return

        # =========================================================================
        # 🔍 FILLON GJENERIMI ME DOKTRINË DHE FASHIKULL TË PLOTË (147 FAQE)
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
            manifest_str = f"Dokumenti në Fokus: {doc_name}"
            
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
            system_prompt = base_prompt + "\n\n" + ANTI_HALLUCINATION_INSTRUCTION

        elif user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=35
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor Inteligjent dhe Eksperti Kryesor i Doktrinës Ligjore në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {ANTI_HALLUCINATION_INSTRUCTION}

            FASHIKULLI INTEGRAL I TË GJITHA {len(db_documents)} SHKRESAVE TË LËNDËS:
            {manifest_str}
            {context_str}
            """

        elif user_intent == "STATUTORY_VERIFICATION":
            dossier_blocks = []
            # PËRFSHIHEN TË GJITHA SHKRESAT PA LIMIT
            for idx, doc in enumerate(db_documents, 1):
                doc_title = doc.get("file_name") or f"Dokumenti #{idx}"
                raw_text = (doc.get("content") or doc.get("extracted_text") or "").strip()
                p_count = doc.get("page_count", "1")
                dossier_blocks.append(f"SHKRESA #{idx}: {doc_title} (Faqe: {p_count})\n{raw_text}\n")

            context_docs = "\n".join(dossier_blocks)
            base_prompt = StatutoryVerificationService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=context_docs,
                manifest_str="",
                case_domain=detected_domain,
                query_text=optimized_query,
                user_id=user_id,
                case_id=case_id,
                db=self.db
            )
            system_prompt = base_prompt + "\n\n" + ANTI_HALLUCINATION_INSTRUCTION

        elif user_intent == "DRAFTING":
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=25
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
            system_prompt = base_prompt + "\n\n" + ANTI_HALLUCINATION_INSTRUCTION
            exec_query = f"Harto aktin e plotë procedural të kërkuar ({optimized_query}) me strukturë solemne gjyqësore."
        else:
            # CHAT UNIVERSAL I KLIENTIT ME TË GJITHA 31 SHKRESAT
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=25
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor Inteligjent dhe Eksperti Kryesor i Doktrinës Ligjore në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {ANTI_HALLUCINATION_INSTRUCTION}

            FASHIKULLI INTEGRAL I TË GJITHA {len(db_documents)} SHKRESAVE TË LËNDËS:
            {manifest_str}
            {context_str}
            """

        # Ruhet pyetja e përdoruesit në koleksion
        if self.db is not None and case_id and user_id:
            try:
                self.db[CASE_CHAT_HISTORY_COLLECTION].insert_one({
                    "user_id": str(user_id),
                    "case_id": str(case_id),
                    "role": "user",
                    "content": query,
                    "created_at": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"Could not save user chat message: {e}")

        # GJENERIMI ME DEEPSEEK
        full_generated_response = ""
        async for content in self.response_generator.generate_stream(system_prompt, exec_query, context="", history=history):
            full_generated_response += content
            yield content

        # Ruhet përgjigja e plotë e AI në koleksion menjëherë sapo mbyllet stream-i
        if self.db is not None and case_id and user_id and full_generated_response.strip():
            try:
                self.db[CASE_CHAT_HISTORY_COLLECTION].insert_one({
                    "user_id": str(user_id),
                    "case_id": str(case_id),
                    "role": "assistant",
                    "content": full_generated_response.strip(),
                    "created_at": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"Could not save assistant chat message: {e}")

        # Caching për shtyllat e lëndës
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
                except Exception as save_err:
                    logger.warning(f"Could not cache case pillar: {save_err}")

        yield MANDATORY_LEGAL_DISCLAIMER