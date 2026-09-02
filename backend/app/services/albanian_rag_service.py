# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - MODULAR RAG SERVICE V190.0 (HARMONIZED WITH NATIVE DB SCHEMAS: latest_deep_analysis & latest_analysis)

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

# Importimi i Shtyllave Kryesore Elitare
from app.services.pillars.forensic_audit_service import ForensicAuditService
from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.comprehensive_analysis_service import ComprehensiveAnalysisService

logger = logging.getLogger(__name__)

MANDATORY_LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n"
    "*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Sokrati (Juristi AI) për qëllime informative, "
    "kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i "
    "Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin "
    "pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*"
)

ANTI_HALLUCINATION_INSTRUCTION = """
RREGULLAT E HEKURTA KUNDËR HALUCINACIONEVE:
1. CITO NENET VETËM NËSE i sheh në kontekstin e dhënë ose i di me siguri absolute nga ligjet e Kosovës.
2. NËSE nuk je 100% i sigurt për numrin e nenit, SHKRUAJ "Neni [verifiko manualisht]" në vend që të improvizosh.
3. MOS shpik asnjë ligj, nen, precedent, datë, apo fakt.
4. Nëse konteksti nuk përmban informacion të mjaftueshëm për pyetjen, THUAJ QARTË: "Nuk kam informacion të mjaftueshëm në fashikull për këtë pyetje."
5. Përdor VETËM ligjet pozitive të Kosovës: KPRK, KPPRK, LPK, LMD, Ligji për Familjen.
"""


class AlbanianRAGService:
    """
    Shërbimi Kryesor RAG — V190.0 i Sinkronizuar me fushat origjinale MongoDB.
    """

    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info("✅ [RAG] Modular Service V190.0 initialized.")

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
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            r"\bKPPRK\b": "Kodi i Procedurës Penale të Kosovës",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLFK\b": "Ligji për Familjen i Kosovës",
        }
        for abbr, expansion in abbreviations.items():
            cleaned = re.sub(abbr, f"{abbr} ({expansion})", cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def _get_tactical_clickable_pills(self, user_intent: str) -> List[str]:
        if user_intent == "FORENSIC_AUDIT":
            return [
                "Harto Kallëzimin Penal — Gjenero aktin zyrtar bazuar në shkeljet e gjetura",
                "Pyetësori Taktik për Seancë — Pyetje kirurgjike për ballafaqimin e dëshmitarit/ekspertit",
                "Matrica Contra Legem — Tabela përmbledhëse vetëm me shkeljet ligjore"
            ]
        elif user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY"]:
            return [
                "Harto Kallëzimin Penal në PSRK — Nenet 414 & 425 të Kodit Penal",
                "Llogarit Dëmin & Kamatën — Dëmi material & jomaterial sipas LMD-së",
                "Pyetësori Taktik për Seancë — Përgatit pyetjet për shqyrtim kryesor"
            ]
        elif user_intent == "DRAFTING":
            return [
                "Audito këtë Draft Ligjor — Kontrolli nen-për-nen para nënshkrimit",
                "Analizo Prapësimet e Mundshme — Çfarë mund të pretendojë pala tjetër",
                "Verifiko Afatet Prekluzive — Afatet e dorëzimit në gjykatë/prokurori"
            ]
        else:
            return [
                "Harto Aktin Gjyqësor — Padi, Kallëzim Penal ose Ankesë",
                "Baza Statutore — Nenet e ligjit të Kosovës që më mbrojnë",
                "Pyetësori Taktik — Pyetjet për seancë gjyqësore"
            ]

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

        client_position = "DEFENDANT"
        client_name = "Klienti"
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

                db_documents = list(self.db.documents.find(doc_filter))
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        from app.services import vector_store_service
        user_intent = IntentDetector.detect(query)
        optimized_query = self._optimize_query(query)

        # =========================================================================
        # ⚡ SMART CACHE CHECK (latest_deep_analysis & latest_analysis)
        # =========================================================================
        
        # 1. Kontrolli për "ANALIZO RASTIN" (latest_deep_analysis)
        if user_intent == "COMPREHENSIVE_ANALYSIS" and case_doc:
            is_dirty = case_doc.get("analysis_dirty", False)
            cached_analysis = case_doc.get("latest_deep_analysis") or case_doc.get("latest_comprehensive_analysis")

            if not is_dirty and cached_analysis and len(cached_analysis.strip()) > 100:
                logger.info(f"⚡ [Smart Cache HIT] Kthehet latest_deep_analysis për lëndën {case_id} (0.00$ API).")
                yield cached_analysis
                clickable_pills = self._get_tactical_clickable_pills(user_intent)
                if clickable_pills:
                    pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(clickable_pills)])
                    yield pills_block
                yield MANDATORY_LEGAL_DISCLAIMER
                return

        # 2. Kontrolli për "FORENZIKË E DOKUMENTIT" (latest_analysis te dokumenti)
        single_doc_obj = db_documents[0] if (document_ids and len(document_ids) == 1 and db_documents) else None
        if user_intent == "FORENSIC_AUDIT" and single_doc_obj:
            cached_doc_audit = single_doc_obj.get("latest_analysis") or single_doc_obj.get("latest_forensic_audit")
            if cached_doc_audit and len(cached_doc_audit.strip()) > 100:
                logger.info(f"⚡ [Smart Cache HIT] Kthehet latest_analysis për dokumentin {single_doc_obj.get('_id')} (0.00$ API).")
                yield cached_doc_audit
                clickable_pills = self._get_tactical_clickable_pills(user_intent)
                if clickable_pills:
                    pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(clickable_pills)])
                    yield pills_block
                yield MANDATORY_LEGAL_DISCLAIMER
                return

        # Kërkimi me RAG
        if user_intent == "GENERAL_CHAT":
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=10
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=20
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)
        elif user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=35
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=20
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)
        else:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=20
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

        # Urdhri i Ekzekutimit Suprem
        exec_query = optimized_query

        if user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            system_prompt = ComprehensiveAnalysisService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str,
                db=self.db,
                query_text=optimized_query,
                user_id=user_id,
                case_id=case_id
            )
            exec_query = "Gjenero Raportin Master të Plotë dhe Gjithëpërfshirës të Gjykatës Supreme për të gjithë fashikullin e lëndës, duke zbërthyer në thellësi maksimale doktrinare të 8 seksionet e detyrueshme pa asnjë shkurtim."

        elif user_intent == "FORENSIC_AUDIT":
            system_prompt = ForensicAuditService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=context_str,
                manifest_str=manifest_str,
                db=self.db,
                user_id=user_id,
                case_id=case_id
            )
            exec_query = "Kryej Auditimin Suprem Forenzik të dokumentit sipas të gjitha 8 seksioneve të plota doktrinare (Pasaporta formale, analiza e aktorëve, kryqëzimi i provave, tabela statutore nen-për-nen, shkeljet Contra Legem, auditimi i petitumit, draft-remediimi dhe master plani i veprimit)."

        elif user_intent == "DRAFTING":
            system_prompt = LegalDraftingService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str,
                query=optimized_query,
                db=self.db,
                user_id=user_id,
                case_id=case_id
            )
        else:
            system_prompt = f"""
            Ti je "Sokrati - Asistenti Ligjor Inteligjent dhe Avokati Kryesor në Kosovë".
            LËNDA: **{case_title}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {ANTI_HALLUCINATION_INSTRUCTION}

            DOKUMENTET E LËNDËS:
            {manifest_str}
            {context_str}
            """

        full_generated_response = ""
        async for content in self.response_generator.generate_stream(system_prompt, exec_query, context_str):
            full_generated_response += content
            yield content

        # =========================================================================
        # 💾 RUAJTJA NË MONGODB TE FUSHAT ORIGJINALE
        # =========================================================================
        
        # 1. Ruaj në Case te `latest_deep_analysis`
        if user_intent == "COMPREHENSIVE_ANALYSIS" and c_oid and self.db is not None and len(full_generated_response.strip()) > 100:
            try:
                self.db.cases.update_one(
                    {"_id": c_oid},
                    {"$set": {
                        "latest_deep_analysis": full_generated_response.strip(),
                        "latest_comprehensive_analysis": full_generated_response.strip(),
                        "analysis_dirty": False,
                        "last_analyzed_at": datetime.now(timezone.utc)
                    }}
                )
                logger.info(f"💾 [Smart Cache SAVED] latest_deep_analysis u ruajt për lëndën {case_id}.")
            except Exception as save_err:
                logger.warning(f"Could not cache case analysis: {save_err}")

        # 2. Ruaj në Document te `latest_analysis`
        if user_intent == "FORENSIC_AUDIT" and single_doc_obj and self.db is not None and len(full_generated_response.strip()) > 100:
            try:
                self.db.documents.update_one(
                    {"_id": single_doc_obj["_id"]},
                    {"$set": {
                        "latest_analysis": full_generated_response.strip(),
                        "latest_forensic_audit": full_generated_response.strip(),
                        "last_audited_at": datetime.now(timezone.utc)
                    }}
                )
                logger.info(f"💾 [Smart Cache SAVED] latest_analysis u ruajt për dokumentin {single_doc_obj['_id']}.")
            except Exception as save_err:
                logger.warning(f"Could not cache doc audit: {save_err}")

        # Butonat e Klikueshëm
        clickable_pills = self._get_tactical_clickable_pills(user_intent)
        if clickable_pills:
            pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(clickable_pills)])
            yield pills_block

        yield MANDATORY_LEGAL_DISCLAIMER