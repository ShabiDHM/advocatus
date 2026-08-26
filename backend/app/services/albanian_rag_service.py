# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - UNIVERSAL AUTONOMOUS LEGAL ENGINE V107.0 (DYNAMIC SITUATIONAL DECISION TREE & ADVISORY)

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

API_KEY = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 90

AI_DISCLAIMER = "\n\n---\n*Kjo analizë ligjore është gjeneruar nga Juristi AI bazuar në shkresat e fashikullit dhe Jurisprudencën e Gjykatës Supreme të Kosovës, është për referencë dhe duhet të verifikohet.*"

MAX_CONTEXT_CHARS = 110_000 


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        
        if API_KEY:
            self.client = AsyncOpenAI(
                api_key=API_KEY,
                base_url=OPENROUTER_BASE_URL,
                timeout=LLM_TIMEOUT
            )
            logger.info("✅ [RAG] Universal Autonomous Legal Engine V107.0 initialized.")
        else:
            self.client = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

    def _detect_user_intent(self, query: str) -> str:
        q = query.lower()
        
        explicit_draft_triggers = [
            "ma harto", "ma gjenero", "shkruaj aktin", "përpilo aktin", 
            "përgatit shkresën zyrtare", "harto padinë", "harto kërkesëpadinë",
            "harto kallëzimin penal", "harto prapësimin", "harto ankesën", "harto kontratën"
        ]
        if any(k in q for k in explicit_draft_triggers):
            return "DRAFTING"
        
        audit_keywords = [
            "direktivë e forenzikës ligjore", "direktivë e detyrueshme forenzike", 
            "paralajmërime & sugjerime", "lapsuseve", "shkelje procedurale"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"
        
        return "ANALYSIS"

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
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës",
            r"\bKPPRK\b": "Kodi i Procedurës Penale",
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
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE ME LINKE TË KLIKUESHME (PËRDOR KËTO FORMATE) >>>\n"]
        context_blocks = []
        
        if db_documents:
            doc_budget = int((MAX_CONTEXT_CHARS * 0.65) / max(len(db_documents), 1))
            
            for idx, doc in enumerate(db_documents, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or "Dokument.pdf"
                
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"
                manifest_lines.append(f"- {doc_clickable_link}")

                raw_t = (
                    doc.get("extracted_text") or 
                    doc.get("text_content") or 
                    doc.get("text") or 
                    doc.get("content") or 
                    doc.get("summary") or 
                    ""
                )
                summ = doc.get("summary") or ""
                if summ == "Sinteza...":
                    summ = ""

                clamped_raw_t = raw_t[:doc_budget] if len(raw_t) > doc_budget else raw_t

                if clamped_raw_t and summ:
                    text_content = f"PËRMBLEDHJE: {summ}\nPËRMBAJTJA:\n{clamped_raw_t}"
                elif clamped_raw_t:
                    text_content = f"PËRMBAJTJA:\n{clamped_raw_t}"
                elif summ:
                    text_content = f"PËRMBLEDHJE: {summ}"
                else:
                    text_content = "Dokument i administruar në fashikull."

                context_blocks.append(f"\n--- SHKRESA: {doc_clickable_link} ---\n{text_content}\n")
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        context_blocks.append("\n<<< PARAGRAFET SELEKTIVE NGA KËRKIMI SEMANTIK I LËNDËS >>>\n")
        for d in case_docs:
            context_blocks.append(f"[{d.get('source') or 'Dokument'}, FAQJA: {d.get('page') or 'N/A'}]: {self._get_expanded_text(d)}\n")

        context_blocks.append("\n<<< BAZA STATUTARE DHE JURISPRUDENCA PARIMORE E GJYKATËS SUPREME >>>\n")
        for d in global_docs:
            source_tag = d.get('source') or 'Burim Juridik'
            context_blocks.append(f"BURIMI: {source_tag}\nPËRMBAJTJA: {self._get_expanded_text(d)}\n")

        full_context = "".join(context_blocks)
        
        if len(full_context) > MAX_CONTEXT_CHARS:
            logger.warning(f"⚠️ Context exceeded ceiling ({len(full_context)} chars). Truncating to {MAX_CONTEXT_CHARS}.")
            full_context = full_context[:MAX_CONTEXT_CHARS] + "\n[TË DHËNA TË PRERA PËR SHKAK TË MADHËSISË SË FASHIKULLIT]"

        return "\n".join(manifest_lines), full_context

    def _get_role_adapted_pillars(self, position: str) -> List[Tuple[str, str]]:
        pos = position.upper()
        if pos == "PLAINTIFF":
            p1 = "Identifiko të gjitha shtyllat kryesore ku mbështetet kërkesëpadia/kallëzimi ynë dhe matricën e plotë të provave."
            p2 = "Analizo bazën ligjore të kërkesëpadisë, afatet procedurale dhe nenet përkatëse të ligjeve të Kosovës."
            p3 = "Gjenero pyetjet taktike për të ballafaquar të paditurin dhe dëshmitarët e tij në seancë."
            p4 = "Llogarit dëmet e kërkuara sipas ligjit dhe përgatit përmbledhjen ekzekutive mbi ecurinë e padisë."
        elif pos == "NEUTRAL":
            p1 = "Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara."
            p2 = "Vlerëso ligjshmërinë e pretendimeve të të dyja palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit."
            p3 = "Identifiko mospërputhjet thelbësore dhe gjenero pyetje neutrale sqaruese për vërtetimin e fakteve."
            p4 = "Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme."
        else:
            p1 = "Analizo të gjitha prapësimet kryesore të mbrojtjes, mungesën e provave të paditësit dhe faktet shfajësuese në fashikull."
            p2 = "Analizo bazën ligjore të prapësimeve, parashkrimin e afateve dhe nenet përkatëse për rrëzimin e padisë."
            p3 = "Gjenero kundër-pyetjet taktike për të zbuluar kontradiktat e paditësit dhe dëshmitarëve të tij në seancë."
            p4 = "Përgatit përmbledhjen ekzekutive mbi rreziqet ligjore, shanset e mbrojtjes dhe hapat e mëtejshëm."

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

        if not any(k in combined_text for k in ["shtyllat kryesore", "prapësimet kryesore", "gjendjen e lëndës", "mbështetet kërkesëpadia", "faktet shfajësuese", "matricën e provave"]):
            remaining.append(pillars[0][1])

        if not any(k in combined_text for k in ["bazën ligjore të kërkesëpadisë", "bazën ligjore të prapësimeve", "ligjshmërinë e pretendimeve", "baza statutore"]):
            remaining.append(pillars[1][1])

        if not any(k in combined_text for k in ["pyetjet taktike për të ballafaquar", "kundër-pyetjet taktike", "pyetjet për zbardhjen", "mospërputhjet thelbësore", "dëgjimin e dëshmitarëve"]):
            remaining.append(pillars[2][1])

        if not any(k in combined_text for k in ["llogarit dëmet", "rreziqet dhe raporti", "memorandumin objektiv", "përmbledhjen ekzekutive", "shanset e mbrojtjes"]):
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
        client_name = "Pala Kliente"
        opposing_name = "Pala Kundërshtare"
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
                    opposing_name = case_doc.get("opposing_party") or case_doc.get("opponent") or opposing_name
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

        identity_header = llm_service.build_dynamic_identity_header(
            client_name=client_name, 
            opposing_name=opposing_name, 
            position=client_position
        )

        user_intent = self._detect_user_intent(query)
        optimized_query = self._optimize_query(query)
        sanitized_query = llm_service._sanitize_and_disambiguate_prompt(optimized_query, opposing_name=opposing_name)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=sanitized_query, case_context_id=case_id, n_results=16
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=sanitized_query, n_results=14
        )

        manifest_str, context_str = self._build_context(case_docs, global_docs, db_documents)
        remaining_pills = self._determine_remaining_pills(query=query, position=client_position, history=history)

        # =========================================================================
        # 🏛️ MOTORI I VENDIMMARRJES SË VETËDIJSHME SITUACIONALE (ZERO HARDCODING)
        # =========================================================================

        dynamic_situational_mandate = f"""
        DATA E SOTME: **{current_date_str}**

        METODOLOGJIA E VETËDIJSHME STRATEGJIKE (PËRSHTATJE DINAMIKE SIPAS SITUATËS SË LËNDËS):
        Analizo me kujdes natyrën e lëndës, shkresat dhe datat e administruara, dhe zbato këtë pemë vendimmarrëse:

        1. VLERËSIMI I AFATEVE TË ANKESËS NË RAPORT ME DATËN E SOTME ({current_date_str}):
           - NËSE AFATI I ANKESËS SË RREGULLT (15 ditë) ËSHTË ENDE AKTIV:
             * Propozo ANKESËN E RREGULLT NË GJYKATËN E APELIT (duke theksuar shkeljet procedurale, faktet dhe ligjin material).
             * Dhe NËSE shkresat zbulojnë gjithashtu veprime kriminale (falsifikim, dëshmi të rreme), propozo PARALELISHT edhe NDJEKJEN PENALE.
           - NËSE AFATI I ANKESËS SË RREGULLT KA SKADUAR (Vendimi ka marrë formë të prerë):
             * Konstato skadimin e afatit të rregullt.
             * NËSE zbulohen vepra penale gjyqësore/mjekësore (falsifikim, ekspertizë e rreme) ➔ Propozo NDJEKJEN PENALE dhe PËRSËRITJEN E PROCEDURËS CIVILE sipas Nenit 232 të LPK-së.
             * Përndryshe ➔ Propozo Kërkesën për Mbrojtje të Ligjshmërisë në Gjykatën Supreme.

        2. PËRSHKRIMI DHE NATYRA E LËNDËS:
           - Nëse lënda është kontest i thjeshtë civil/kontraktual pa vepër penale (p.sh. borxh, qira, punë) ➔ Propozo VETËM mjetet përkatëse civile/përmbarimore pa ngritur kallëzime penale pa shkak.
           - Nëse lënda përmban vepra penale (mashtrim, dhunë, korrupsion, falsifikim) ➔ Formulo strategjinë e plotë të ndjekjes penale dhe masave emergjente.

        3. ZBATIMI I JURISPRUDENCËS SË GJYKATËS SUPREME:
           - Zbato precedentët parimorë të Gjykatës Supreme (të shënuara me '🔨 Praktika Gjyqësore') mbi provat konkrete të këtij fashikulli.
        """

        if user_intent == "DRAFTING":
            system_prompt = f"""
            {identity_header}

            ROLI YT: Avokat Senior dhe Përfaqësues Procedural Elitar në Republikën e Kosovës.
            MISIONI: Përdoruesi kërkon të HARTOSH një akt zyrtar gjyqësor të plotë dhe shterues (Kallëzim Penal, Kërkesëpadi, Prapësim, Kundërpadi, Ankesë apo Kontratë).

            {dynamic_situational_mandate}

            STANDARDI I ARSYETIMIT JURIDIK:
            - Nëse fashikulli ka vetëm shkresa bazë (kontrata, fatura, komunikime, procesverbale), nxirr faktet nga ato dhe ndërto shkresën nga e para.
            - Zbato drejtpërdrejt parimet e Gjykatës Supreme të Kosovës (të shënuara me '🔨 Praktika Gjyqësore') për të arsyetuar kërkesëpadinë apo fajësinë.
            - Shkruaj aktin e plotë nga kryerreshti deri te nënshkrimi përfundimtar pa u ndërprerë në mes.

            STRUKTURA E SHKRESËS ZYRTARE:
            - Organi Marrës | Palët e Plota | Titulli | Baza Statutare | Dispozitivi (SEPSE) me të gjithë personat/shkeljet | Arsyetimi Faktiq & Doktrinar | Petitumi/Kërkesa Procedurale | Inventari i Provave | Rezervimi i Dëmit | Data dhe Nënshkrimi.

            DOKUMENTET E NGARKUARA NË KONTEKST:
            {context_str}
            """
        elif user_intent == "FORENSIC_AUDIT":
            system_prompt = f"""
            {identity_header}

            ROLI YT: Auditor i Forenzikës Ligjore dhe Gjyqtar i Kolegjit të Gjykatës Supreme të Kosovës.
            MISIONI: Kryej auditimin e plotë forenzik ligjor dhe procedural EKSKLUZIVISHT mbi dokumentin e ngarkuar në kontekst më poshtë.

            {dynamic_situational_mandate}

            RREGULLA ABSOLUTE E IZOLIMIT DHE SAKTËSISË:
            1. Përdor VETËM të dhënat që gjenden brenda këtij dokumenti specifik. MOS fut të dhëna nga lëndë të tjera nëse nuk përmenden tekstualisht këtu.

            STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK ME 5 SEKSIONE:
            ### 1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
            ### 2. BAZA STATUTARE DHE NENET E LIDHURA
            ### 3. ⚠️ AUDITIMI I SHKELJEVE PROCEDURALE DHE KONTRASTET NË VENDIM
            ### 4. 🏛️ VENDIMET PARIMORE TË GJYKATËS SUPREME TË KOSOVËS
            ### 5. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM PROCEDURALË (Përshtatur sipas afatit dhe natyrës së lëndës)

            DOKUMENTI I IZOLUAR PËR AUDITIM:
            {context_str}
            """
        else:
            if client_position == "PLAINTIFF":
                role_instructions = f"PERSPEKTIVA JURIDIKE: **PADITËS / KALLËZUES (Përfaqësuesi i {client_name}).**"
            elif client_position == "NEUTRAL":
                role_instructions = "PERSPEKTIVA JURIDIKE: **NEUTRAL (Auditor / Kolegji Gjyqësor).**"
            else:
                role_instructions = f"PERSPEKTIVA JURIDIKE: **I PADITUR / I DENONCUAR (Mbrojtësi i {client_name}).**"

            system_prompt = f"""
            {identity_header}

            Ti je "Sokrati - Krye-Strategu dhe Gjyqtari Suprem i Drejtësisë në Kosovë".
            METADATAT E LËNDËS: **{case_title}** | Palët: **{client_name}** vs. **{opposing_name}** ({client_position})
            {role_instructions}

            {dynamic_situational_mandate}

            REGJISTRI I SKEDARËVE:
            {manifest_str}

            DOKUMENTET E FASHIKULLIT DHE JURISPRUDENCA:
            {context_str}

            UDHËZIME PËR ANALIZËN DOKTRINARE TË KARTAVE:
            1. Përgjigju me thellësi maksimale pyetjes strategjike të avokatit duke përfshirë TË GJITHA SHTYLLAT E PROVAVE të fashikullit.
            2. PËRSHTAT REKOMANDIMIN SIPAS SITUATËS REALE: Vlerëso afatin e ankesës në raport me datën e sotme, shkeljet e ligjit dhe nëse duhet ankesë e rregullt, ndjekje penale apo përsëritje e procedurës civile.
            3. Zbato precedentët dhe vendimet parimore të Gjykatës Supreme (të shënuara me '🔨 Praktika Gjyqësore').
            4. MOS vendos kryerresht formal gjykate kur pyetja është për analizë strategjike.

            STRUKTURA E PËRGJIGJES:
            ### 1. SHTYLLAT KRYESORE STRATEGJIKE DHE MATRICA E PROVAVE
            ### 2. BAZA STATUTARE DHE JURISPRUDENCA E GJYKATËS SUPREME
            ### 3. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM (Përshtatur në mënyrë të zgjuar sipas situatës faktike)
            """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": sanitized_query}
                ],
                temperature=0.1,
                stream=True,
                max_tokens=8192
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            if user_intent == "ANALYSIS" and remaining_pills and len(remaining_pills) > 0:
                pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
                yield pills_block

            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: Motori i Inteligjencës Artificiale tejkaloi kapacitetin. Ju lutem provoni përsëri.]"
            yield AI_DISCLAIMER