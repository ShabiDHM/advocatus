# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - MODULAR RAG SERVICE V132.0 (CHUNKED PROCESSING ENABLED)

import os
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings

# PHOENIX FIX: Importi i moduleve të reja
from app.services.rag.intent_detector import IntentDetector
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.response_generator import ResponseGenerator

# Importimi i 6 Moduleve të Pavarura (Pillars)
from app.services.pillars.pillar_1_strategy import Pillar1StrategyService
from app.services.pillars.pillar_2_statutes import Pillar2StatutesService
from app.services.pillars.pillar_3_questions import Pillar3QuestionsService
from app.services.pillars.pillar_4_damages import Pillar4DamagesService
from app.services.pillars.forensic_audit_service import ForensicAuditService
from app.services.pillars.legal_drafting_service import LegalDraftingService

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MANDATORY_LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n"
    "*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Sokrati (Juristi AI) për qëllime informative, "
    "kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i "
    "Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin "
    "pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*"
)


class AlbanianRAGService:
    """
    Shërbimi Kryesor RAG — V132.0 Modular me Chunked Processing:
    - IntentDetector: Zbulon çfarë kërkon përdoruesi
    - ContextBuilder: Ndërton kontekstin nga dokumentet
    - ResponseGenerator: Thërret LLM + Filtron halucinacionet + Chunked Processing
    """

    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info("✅ [RAG] Modular Service V132.0 initialized.")

    def _optimize_query(self, query: str) -> str:
        """Pastron query-n nga fjalë hyrëse dhe zgjeron shkurtesat."""
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

    def _determine_remaining_pills(self, query: str, history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Kthen sugjerimet për kartelat e mbetura."""
        all_pillars = [
            "Duke u bazuar në të gjithë fashikullin e lëndës, analizo dhe ndërto të gjitha shtyllat strategjike të kërkesëpadisë/kallëzimit tonë.",
            "Analizo të gjithë fashikullin: nxirr bazën e plotë ligjore dhe audito lapsuset me precedentët e Gjykatës Supreme.",
            "Gjenero pyetësorin taktik të ballafaqimit për të zbuluar të pavërtetat e palës kundërshtare.",
            "Llogarit dëmet materiale e jomateriale sipas LMD-së me kamatën 8% dhe masat emergjente."
        ]

        past_texts = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    raw = str(msg.get("content", ""))
                    if not raw.startswith("[DIREKTIVË"):
                        past_texts.append(raw.lower())

        current_q = query.lower()
        if not current_q.startswith("[direktivë"):
            past_texts.append(current_q)

        combined = " ".join(past_texts)
        remaining = []

        if "shtyllat strategjike" not in combined and "strategjia dhe matrica" not in combined:
            remaining.append(all_pillars[0])
        if "nxirr bazën e plotë ligjore" not in combined and "baza statutore" not in combined:
            remaining.append(all_pillars[1])
        if "pyetësorin taktik" not in combined and "pyetjet taktike" not in combined:
            remaining.append(all_pillars[2])
        if "llogarit dëmet" not in combined and "kamatën ligjore" not in combined:
            remaining.append(all_pillars[3])

        return remaining

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

        # 1. Lexo të dhënat e çështjes
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

        # 2. Zbulo qëllimin e përdoruesit
        from app.services import vector_store_service
        user_intent = IntentDetector.detect(query)
        optimized_query = self._optimize_query(query)

        # 3. Kërko në RAG
        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=30
        )
        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=optimized_query, n_results=16
        )

        # 4. Ndërto kontekstin
        manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)
        remaining_pills = self._determine_remaining_pills(query=query, history=history)

        # 5. Ndërto prompt-in sipas qëllimit
        if user_intent == "FORENSIC_AUDIT":
            system_prompt = ForensicAuditService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=context_str
            )
        elif user_intent == "DRAFTING":
            system_prompt = LegalDraftingService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str,
                query=optimized_query
            )
        elif user_intent == "PILLAR_STRATEGY":
            system_prompt = Pillar1StrategyService.build_prompt(
                case_title, client_name, client_position, current_date_str, manifest_str, context_str
            )
        elif user_intent == "PILLAR_STATUTES":
            system_prompt = Pillar2StatutesService.build_prompt(
                case_title, client_name, client_position, current_date_str, manifest_str, context_str
            )
        elif user_intent == "PILLAR_QUESTIONS":
            system_prompt = Pillar3QuestionsService.build_prompt(
                case_title, client_name, client_position, current_date_str, manifest_str, context_str
            )
        elif user_intent == "PILLAR_DAMAGES":
            system_prompt = Pillar4DamagesService.build_prompt(
                case_title, client_name, client_position, current_date_str, manifest_str, context_str
            )
        else:
            system_prompt = f"""
            Ti je "Sokrati - Asistenti Ligjor Inteligjent dhe Avokati Kryesor në Kosovë".
            LËNDA: **{case_title}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            DOKUMENTET E LËNDËS:
            {manifest_str}
            {context_str}
            """

        # 6. PHOENIX FIX: Gjenero përgjigjen me chunked processing
        async for content in self.response_generator.generate_stream(system_prompt, optimized_query, context_str):
            yield content

        # 7. Sugjerimet interaktive
        if user_intent in ["FORENSIC_AUDIT", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"] and remaining_pills:
            pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
            yield pills_block

        # 8. Klauzola e detyrueshme
        yield MANDATORY_LEGAL_DISCLAIMER