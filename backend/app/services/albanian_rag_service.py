# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - 100% DYNAMIC & DOMAIN-AGNOSTIC ROUTER V121.0 (ZERO HARDCODED NAMES)

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

# Importimi i 4 Moduleve të Izoluara të Kartave
from app.services.pillars.pillar_1_strategy import Pillar1StrategyService
from app.services.pillars.pillar_2_statutes import Pillar2StatutesService
from app.services.pillars.pillar_3_questions import Pillar3QuestionsService
from app.services.pillars.pillar_4_damages import Pillar4DamagesService

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

API_KEY = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 90

AI_DISCLAIMER = "\n\n---\n*Kjo analizë ligjore është gjeneruar nga Juristi AI bazuar në shkresat e fashikullit dhe Jurisprudencën e Gjykatës Supreme të Kosovës, është për referencë dhe duhet të verifikohet.*"

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
            logger.info("✅ [RAG] Modular Multi-Agent Router V121.0 initialized (100% Pure Dynamic Extraction).")
        else:
            self.client = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

    def _detect_user_intent(self, query: str) -> str:
        q = query.lower()
        
        # 1. HARTIM I AKTEVE ZYRTARE (DRAFTING)
        explicit_draft_triggers = [
            "ma harto", "ma gjenero", "shkruaj aktin", "përpilo aktin", 
            "përgatit shkresën zyrtare", "harto padinë", "harto kërkesëpadinë",
            "harto kallëzimin penal", "harto prapësimin", "harto ankesën", "harto kontratën",
            "harto një kallxim penal", "harto kallxim penal", "harto një padi", "harto padi"
        ]
        if any(k in q for k in explicit_draft_triggers):
            return "DRAFTING"
        
        # 2. AUDITIM FORENZIK I NJË DOKUMENTI
        audit_keywords = [
            "direktivë e forenzikës ligjore", "direktivë e detyrueshme forenzike", 
            "paralajmërime & sugjerime", "lapsuseve", "shkelje procedurale"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"
        
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
            "nxirr bazën e plotë ligjore", "baza statutore", "baza ligjore", 
            "jurisprudenca", "lapsuse në shkresa", "precedentët", "nenet e ligjit", "kushtetutën dhe konventat"
        ]):
            return "PILLAR_STATUTES"

        # 6. KARTA 1: STRATEGJIA DHE MATRICA
        if any(k in q for k in [
            "shtyllat strategjike", "strategjia dhe matrica", "shtyllat kryesore", 
            "qëndrueshmërinë e lëndës", "gjendjen e lëndës", "mbështetet kërkesëpadia", 
            "faktet shfajësuese", "matricën e provave", "matricën e plotë të provave"
        ]):
            return "PILLAR_STRATEGY"

        # 7. CHAT I LIRË
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

    def _get_role_adapted_pillars(self, position: str) -> List[Tuple[str, str]]:
        pos = position.upper()
        if pos == "PLAINTIFF":
            p1 = "Identifiko të gjitha shtyllat kryesore ku mbështetet kërkesëpadia/kallëzimi ynë dhe matricën e plotë të provave."
            p2 = "Analizo bazën ligjore të kërkesëpadisë, afatet procedurale dhe nenet përkatëse të ligjeve të Kosovës."
            p3 = "Gjenero pyetjet taktike për të ballafaquar palën kundërshtare dhe dëshmitarët e saj në seancë."
            p4 = "Llogarit dëmet e kërkuara sipas ligjit dhe përgatit përmbledhjen ekzekutive mbi ecurinë e procedurës."
        elif pos == "NEUTRAL":
            p1 = "Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara."
            p2 = "Vlerëso ligjshmërinë e pretendimeve të të dyja palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit."
            p3 = "Identifiko mospërputhjet thelbësore dhe gjenero pyetje neutrale sqaruese për vërtetimin e fakteve."
            p4 = "Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme."
        else:
            p1 = "Identifiko të gjitha shtyllat kryesore strategjike të mbrojtjes dhe çmontimit të pretendimeve kundërshtare."
            p2 = "Nxirr bazën e plotë ligjore, shkeljet procedurale në dëm të klientit dhe precedentët e Gjykatës Supreme."
            p3 = "Gjenero pyetjet taktike të ballafaqimit për të zbuluar kontradiktat e palës kundërshtare dhe dëshmitarëve."
            p4 = "Llogarit dëmet materiale/jomateriale sipas LMD-së dhe arsyeto masat e menjëhershme mbrojtëse."

        return [
            ("PILLAR_1", p1),
            ("PILLAR_2", p2),
            ("PILLAR_3", p3),
            ("PILLAR_4", p4)
        ]

    def _determine_remaining_pills(self, query: str, position: str, history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        pillars = self._get_role_adapted_pillars(position)

        all_past_user_messages = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    all_past_user_messages.append(str(msg.get("content", "")).lower())
        all_past_user_messages.append(query.lower())
        combined_text = " ".join(all_past_user_messages)

        remaining = []

        # MATCH PILLAR 1
        p1_triggers = [
            "shtyllat strategjike", "strategjia dhe matrica", "shtyllat kryesore", 
            "qëndrueshmërinë e lëndës", "gjendjen e lëndës", "mbështetet kërkesëpadia", 
            "faktet shfajësuese", "matricën e provave", "matricën e plotë të provave", "prapësimet kryesore"
        ]
        if not any(k in combined_text for k in p1_triggers):
            remaining.append(pillars[0][1])

        # MATCH PILLAR 2
        p2_triggers = [
            "nxirr bazën e plotë ligjore", "baza statutore", "baza ligjore", 
            "bazën ligjore të kërkesëpadisë", "bazën ligjore të prapësimeve", 
            "lapsuse në shkresa", "ligjshmërinë e pretendimeve", "precedentët dhe qëndrimet", "precedentët"
        ]
        if not any(k in combined_text for k in p2_triggers):
            remaining.append(pillars[1][1])

        # MATCH PILLAR 3
        p3_triggers = [
            "pyetësorin taktik", "pyetësori taktik", "pyetjet taktike", 
            "pyetjet taktike të ballafaqimit", "kundër-pyetjet", "marrja në pyetje", 
            "dëgjimin e dëshmitarëve", "mospërputhjet thelbësore"
        ]
        if not any(k in combined_text for k in p3_triggers):
            remaining.append(pillars[2][1])

        # MATCH PILLAR 4
        p4_triggers = [
            "llogarit dëmet", "llogaritja e dëmit", "dëmet materiale e jomateriale", 
            "kamatën ligjore vonesore", "masat emergjente", "masat emergjente mbrojtëse", 
            "sigurimin e kërkesëpadisë", "memorandumin objektiv"
        ]
        if not any(k in combined_text for k in p4_triggers):
            remaining.append(pillars[3][1])

        return remaining

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            yield AI_DISCLAIMER
            return

        from app.services import vector_store_service, llm_service

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
        # 🔀 DELEGIMI TE MODULI I SPECIALIZUAR SIPAS KARTAVE OSE TE CHAT-I I LIRË
        # =========================================================================

        if user_intent == "PILLAR_STRATEGY":
            system_prompt = Pillar1StrategyService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str
            )

        elif user_intent == "PILLAR_STATUTES":
            system_prompt = Pillar2StatutesService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str
            )

        elif user_intent == "PILLAR_QUESTIONS":
            system_prompt = Pillar3QuestionsService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str
            )

        elif user_intent == "PILLAR_DAMAGES":
            system_prompt = Pillar4DamagesService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str
            )

        elif user_intent == "DRAFTING":
            # 🏛️ HARTIM UNIVERSAL I BLINDUAR ME BESNIKËRI NDAJ KLIENTIT
            system_prompt = f"""
            Ti je Avokati Senior Elitar në Republikën e Kosovës në përfaqësim ekskluziv të: **{client_name}**.
            LËNDA: **{case_title}** | DATA: {current_date_str}

            RREGULLA SUPREME E HARTIMIT:
            1. PARASHTRUESI / PADITËSI I KËTIJ AKTI ËSHTË VETËM: **{client_name}** (ose Avokati i autorizuar nga {client_name}).
            2. TË DYSHUARIT / PALA KUNDËRSHTARE: Janë personat, subjektet apo institucionet përgjegjëse të identifikuara nga dokumentet e fashikullit, të ngarkuara me shkeljet konkrete.
            3. NDALOHET KATEGORIKISHT të hartohet akt apo kallëzim penal KUNDËR {client_name}! {client_name} është PALA QË KËRKON DREJTËSI / PARASHTRUESI.

            STRUKTURA E DETYRUESHME E SHKRESËS (FORMAT GJYQËSOR FORMAL):
            DREJTUAR:
            PROKURORISË / GJYKATËS KOMPETENTE NË REPUBLIKËN E KOSOVËS

            PARASHTRUESI:
            {client_name}, në cilësinë procedurale përkatëse

            LËNDA: (Titulli i saktë i aktit: KALLËZIM PENAL / KËRKESËPADI / PRAPËSIM / ANKESË)
            (Baza Statutare sipas legjislacionit në fuqi të Kosovës)

            KUNDËR:
            (Rendit të gjithë personat/subjektet përgjegjëse të nxjerra nga dokumentet)

            S E P S E (DISPOZITIVI ME PIKA PËR SECILËN SHKELJE)
            P R O P O Z O J (KËRKESA PROCEDURALE DHE PETITUMI)
            A R S Y E T I M I (ARSYETIMI FAKTIQ DHE JURISPRUDENCA E GJYKATËS SUPREME)
            INVENTARI I PROVAVE MATERIALE DHE SHKENCORE (CORPUS DELICTI)

            PARASHTRUESI:
            {client_name}
            Prishtinë, Republika e Kosovës

            DOKUMENTET E LËNDËS:
            {manifest_str}
            {context_str}
            """

        elif user_intent == "FORENSIC_AUDIT":
            system_prompt = f"""
            ROLI YT: Auditor i Forenzikës Ligjore dhe Gjyqtar i Kolegjit Suprem të Kosovës.
            LËNDA: **{case_title}** | PËRFAQËSIMI: {client_name}
            MISIONI: Kryej auditimin e plotë forenzik ligjor mbi dokumentin e ngarkuar në mënyrë të izoluar.

            DOKUMENTI I IZOLUAR PËR AUDITIM:
            {context_str}

            STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK ME 5 SEKSIONE:
            ### 1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
            ### 2. BAZA STATUTARE DHE NENET E SAKTA TË LIGJEVE TË KOSOVËS
            ### 3. ⚠️ AUDITIMI I SHKELJEVE PROCEDURALE DHE KONTRASTET NË VENDIM
            ### 4. 🏛️ VENDIMET PARIMORE TË GJYKATËS SUPREME TË KOSOVËS
            ### 5. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM PROCEDURALË
            """

        else:
            system_prompt = f"""
            Ti je "Sokrati - Asistenti Ligjor Inteligjent dhe Avokati Kryesor në Kosovë".
            LËNDA: **{case_title}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            MISIONI:
            Përgjigju në mënyrë të drejtpërdrejtë, të saktë dhe profesionale pyetjes së avokatit/përdoruesit duke u bazuar në ligjet e Kosovës dhe shkresat e fashikullit.

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

            if user_intent in ["PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"] and remaining_pills and len(remaining_pills) > 0:
                pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
                yield pills_block

            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: Motori i Inteligjencës Artificiale tejkaloi kapacitetin. Ju lutem provoni përsëri.]"
            yield AI_DISCLAIMER