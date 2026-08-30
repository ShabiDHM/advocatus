# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - SEAMLESS 4->3->2->1->0 PROGRESSIVE PILLAR REDUCTION & MANDATORY UNIVERSAL DISCLAIMER V128.0

import os
import sys
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from openai import AsyncOpenAI
from app.core.config import settings

# Importimi i 6 Moduleve të Pavarura
from app.services.pillars.pillar_1_strategy import Pillar1StrategyService
from app.services.pillars.pillar_2_statutes import Pillar2StatutesService
from app.services.pillars.pillar_3_questions import Pillar3QuestionsService
from app.services.pillars.pillar_4_damages import Pillar4DamagesService
from app.services.pillars.forensic_audit_service import ForensicAuditService
from app.services.pillars.legal_drafting_service import LegalDraftingService

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

API_KEY = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 90

MANDATORY_LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n"
    "*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Sokrati (Juristi AI) për qëllime informative, "
    "kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i "
    "Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin "
    "pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*"
)

MAX_CONTEXT_CHARS = 140_000 


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        
        if API_KEY:
            self.client = AsyncOpenAI(
                api_key=API_KEY,
                base_url=OPENROUTER_BASE_URL,
                timeout=LLM_TIMEOUT
            )
            logger.info("✅ [RAG] Progressive Flow Engine V128.0 initialized.")
        else:
            self.client = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

    def _detect_user_intent(self, query: str) -> str:
        q = query.lower()
        
        # 1. FORENZIKA LIGJORE E DOKUMENTIT (BUTONI ⚖️)
        audit_keywords = [
            "direktivë forenzike e gjykatës supreme", "direktivë e forenzikës ligjore", 
            "direktivë e detyrueshme forenzike", "auditimin e plotë forenzik ligjor", 
            "paralajmërime & sugjerime statutare"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"

        # 2. HARTIM I AKTEVE ZYRTARE (DRAFTING)
        explicit_draft_triggers = [
            "ma harto", "ma gjenero", "shkruaj aktin", "përpilo aktin", 
            "përgatit shkresën zyrtare", "harto padinë", "harto kërkesëpadinë",
            "harto kallëzimin penal", "harto prapësimin", "harto ankesën", "harto kontratën",
            "harto një kallxim penal", "harto kallxim penal", "harto një padi", "harto padi"
        ]
        if any(k in q for k in explicit_draft_triggers):
            return "DRAFTING"
        
        # 3. KARTA 3: PYETËSORI TAKTIK
        if any(k in q for k in [
            "pyetësorin taktik", "pyetësor", "pyetje taktike", "ballafaqim", 
            "dëshmitarët", "marrja në pyetje", "seancë", "kundër-pyetje", "pyetjet taktike të ballafaqimit"
        ]):
            return "PILLAR_QUESTIONS"
        
        # 4. KARTA 4: DËMET DHE MASAT
        if any(k in q for k in [
            "llogarit dëmet", "llogaritja e dëmit", "lmd", "kamatën ligjore", 
            "masat emergjente", "dëmit material", "dëmet materiale e jomateriale", "sigurimin e kërkesëpadisë"
        ]):
            return "PILLAR_DAMAGES"

        # 5. KARTA 2: BAZA STATUTARE
        if any(k in q for k in [
            "nxirr bazën e plotë ligjore", "baza statutore dhe jurisprudenca", 
            "lapsuse në shkresa", "precedentët dhe qëndrimet e gjykatës supreme"
        ]):
            return "PILLAR_STATUTES"

        # 6. KARTA 1: STRATEGJIA DHE MATRICA
        if any(k in q for k in [
            "shtyllat strategjike të kërkesëpadisë", "strategjia dhe matrica e provave", 
            "qëndrueshmërinë e lëndës", "gjendjen e lëndës", "mbështetet kërkesëpadia"
        ]):
            return "PILLAR_STRATEGY"

        return "GENERAL_CHAT"

    def _optimize_query(self, query: str) -> str:
        cleaned = query.strip()
        preambles = [
            r"^\s*më\s+trego\s+rreth\s+",
            r"^\s*më\s+trego\s+për\s+",
            r"^\s*a\s+mund\s+të\s+më\s+ndihmosh\s+me\s+",
            r"^\s*ju\s+lutem\s+më\s+gjej\s+",
            r"^\s*kërko\s+për\s+",
            r"^\s*gjej\s+nenin\s+",
            r"^\s*shiko\s+nëse\s+",
            r"^\s*të\s+lutem\s+analizo\s+",
        ]
        for preamble in preambles:
            cleaned = re.sub(preamble, "", cleaned, flags=re.IGNORECASE)
        
        abbreviations = {
            r"\bLMD\b": "Ligji për Marrëdhëniet e Detyrimeve",
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            r"\bKPPRK\b": "Kodi i Procedurës Penale të Kosovës",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLFK\b": "Ligji për Familjen i Kosovës",
            r"\bLSHT\b": "Ligji për Shoqëritë Tregtare",
        }
        for abbr, expansion in abbreviations.items():
            cleaned = re.sub(abbr, f"{abbr} ({expansion})", cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def _get_expanded_text(self, d: Dict[str, Any]) -> str:
        metadata = d.get('metadata') or {}
        return (
            d.get('parent_text') or 
            metadata.get('parent_text') or 
            d.get('text') or 
            metadata.get('text') or 
            d.get('content') or 
            metadata.get('content') or 
            ""
        ).strip()

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict], db_documents: List[Dict]) -> Tuple[str, str]:
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE DHE PASAPORTA FORENZIKE E FASHIKULLIT >>>\n"]
        context_blocks = []
        
        if db_documents:
            doc_budget = int((MAX_CONTEXT_CHARS * 0.70) / max(len(db_documents), 1))
            doc_budget = max(doc_budget, 7_000)
            
            for idx, doc in enumerate(db_documents, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or f"Dokument_{idx}.pdf"
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"
                
                raw_t = (
                    doc.get("extracted_text") or 
                    doc.get("text_content") or 
                    doc.get("text") or 
                    doc.get("content") or 
                    ""
                ).strip()
                
                summ = (doc.get("summary") or "").strip()
                if summ == "Sinteza...":
                    summ = ""

                dense_passport = summ or raw_t[:1500] or "Shkresë e administruar në fashikull."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:400]}")
                
                if len(db_documents) <= 15 and raw_t:
                    context_blocks.append(f"\n--- TEKSTI I PLOTË I SHKRESËS: {doc_clickable_link} ---\n{raw_t[:doc_budget]}\n")
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        context_blocks.append("\n<<< PARAGRAFET FORENZIKE DHE PROVAT E GJETA NGA KËRKIMI SEMANTIK NË FASHIKULL >>>\n")
        for d in case_docs:
            src = d.get('source') or 'Dokument'
            page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
            context_blocks.append(f"[{src}{page_info}]:\n{self._get_expanded_text(d)}\n")

        context_blocks.append("\n<<< BAZA STATUTARE DHE JURISPRUDENCA PARIMORE E GJYKATËS SUPREME TË KOSOVËS >>>\n")
        for d in global_docs:
            source_tag = d.get('source') or 'Burim Juridik'
            context_blocks.append(f"BURIMI: {source_tag}\nPËRMBAJTJA: {self._get_expanded_text(d)}\n")

        full_context = "".join(context_blocks)
        
        if len(full_context) > MAX_CONTEXT_CHARS:
            full_context = full_context[:MAX_CONTEXT_CHARS] + "\n[TË DHËNA TË PRERA PËR SHKAK TË MADHËSISË SË FASHIKULLIT]"

        return "\n".join(manifest_lines), full_context

    def _determine_remaining_pills(self, query: str, position: str, history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        all_pillars = [
            ("PILLAR_1", "Duke u bazuar në të gjithë fashikullin e lëndës dhe në vendimet parimore të Gjykatës Supreme të Kosovës, analizo dhe ndërto të gjitha shtyllat strategjike të kërkesëpadisë/kallëzimit tonë, duke përfshirë çdo provë vendimtare materiale e shkencore të administruar, dhe jep vlerësimin doktrinar të Gjyqtarit Suprem mbi qëndrueshmërinë e lëndës."),
            ("PILLAR_2", "Analizo të gjithë fashikullin e lëndës: nxirr bazën e plotë ligjore (nenet, ligjet, Kushtetutën dhe Konventat), audito me saktësi nëse ka lapsuse në shkresa dhe lidhe çdo shkelje me precedentët dhe qëndrimet e Gjykatës Supreme të Kosovës."),
            ("PILLAR_3", "Duke u bazuar në kontradiktat e shkresave të fashikullit dhe standardin e vlerësimit të dëshmive të Gjykatës Supreme, gjenero pyetësorin taktik të ballafaqimit për të zbuluar të pavërtetat e palës kundërshtare dhe dëshmitarëve të saj në seancë."),
            ("PILLAR_4", "Analizo të gjithë fashikullin: llogarit dëmet materiale e jomateriale sipas LMD-së bashkë me kamatën ligjore vonesore 8%, arsyeto masat emergjente mbrojtëse / sigurimin e kërkesëpadisë dhe përgatit përmbledhjen ekzekutive për klientin.")
        ]

        past_user_texts = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    raw = str(msg.get("content", ""))
                    if not raw.startswith("[DIREKTIVË"):
                        past_user_texts.append(raw.lower())

        current_q = query.lower()
        if not current_q.startswith("[direktivë"):
            past_user_texts.append(current_q)

        combined_text = " ".join(past_user_texts)
        remaining = []

        if not ("shtyllat strategjike të kërkesëpadisë" in combined_text or "strategjia dhe matrica" in combined_text):
            remaining.append(all_pillars[0][1])

        if not ("nxirr bazën e plotë ligjore" in combined_text or "baza statutore dhe jurisprudenca" in combined_text):
            remaining.append(all_pillars[1][1])

        if not ("pyetësorin taktik" in combined_text or "pyetjet taktike të ballafaqimit" in combined_text):
            remaining.append(all_pillars[2][1])

        if not ("llogarit dëmet materiale" in combined_text or "kamatën ligjore vonesore 8%" in combined_text):
            remaining.append(all_pillars[3][1])

        return remaining

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            return

        current_date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

        client_position = "DEFENDANT"
        client_name = "Klienti"
        case_title = "Lënda Ligjore"
        case_desc = ""
        db_documents = []

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    case_title = case_doc.get("title") or case_doc.get("case_name") or case_title
                    case_desc = case_doc.get("description") or ""

                doc_filter: Dict[str, Any] = {
                    "$or": [{"case_id": case_id}, {"case_id": c_oid}], 
                    "status": {"$ne": "DELETED"}
                }

                if document_ids and len(document_ids) > 0:
                    doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                    doc_strs = [str(did) for did in document_ids]
                    doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                doc_cursor = self.db.documents.find(doc_filter)
                db_documents = list(doc_cursor)
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        from app.services import vector_store_service
        user_intent = self._detect_user_intent(query)
        optimized_query = self._optimize_query(query)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=30
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=optimized_query, n_results=16
        )

        manifest_str, context_str = self._build_context(case_docs, global_docs, db_documents)
        remaining_pills = self._determine_remaining_pills(query=query, position=client_position, history=history)

        # =========================================================================
        # 🔀 DELEGIMI I PLOTË TE MODU蕪AT E IZOLUARA (100% UNIVERSALE)
        # =========================================================================

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
            system_prompt = Pillar1StrategyService.build_prompt(case_title, client_name, client_position, current_date_str, manifest_str, context_str)
        elif user_intent == "PILLAR_STATUTES":
            system_prompt = Pillar2StatutesService.build_prompt(case_title, client_name, client_position, current_date_str, manifest_str, context_str)
        elif user_intent == "PILLAR_QUESTIONS":
            system_prompt = Pillar3QuestionsService.build_prompt(case_title, client_name, client_position, current_date_str, manifest_str, context_str)
        elif user_intent == "PILLAR_DAMAGES":
            system_prompt = Pillar4DamagesService.build_prompt(case_title, client_name, client_position, current_date_str, manifest_str, context_str)
        else:
            system_prompt = f"""
            Ti je "Sokrati - Asistenti Ligjor Inteligjent dhe Avokati Kryesor në Kosovë".
            LËNDA: **{case_title}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            DOKUMENTET E LËNDËS:
            {manifest_str}
            {context_str}
            """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": optimized_query}
                ],
                temperature=0.1,
                stream=True,
                max_tokens=8192
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            # SUGJERIMET INTERAKTIVE (1-4)
            if user_intent in ["FORENSIC_AUDIT", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"] and remaining_pills and len(remaining_pills) > 0:
                pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
                yield pills_block

            # KLAUZOLA E DETYRUESHME LIGJORE (SHFAQET NË 100% TË RASTEVE)
            yield MANDATORY_LEGAL_DISCLAIMER

        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: Motori i Inteligjencës Artificiale tejkaloi kapacitetin. Ju lutem provoni përsëri.]"