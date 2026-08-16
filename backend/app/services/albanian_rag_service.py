# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V70.0 (ROLE-ADAPTIVE 4-PILLAR PROGRESSIVE INTELLIGENCE)

import os
import sys
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from bson import ObjectId
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

API_KEY = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 60

AI_DISCLAIMER = "\n\n---\n*Kjo analizë ligjore është gjeneruar nga Juristi AI bazuar në shkresat e administruara të fashikullit. Për përdorim profesional.*"

class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.citation_map: Dict[Tuple[str, str], str] = {}
        self.law_number_map: Dict[Tuple[str, str], str] = {}
        
        if API_KEY:
            self.client = AsyncOpenAI(
                api_key=API_KEY,
                base_url=OPENROUTER_BASE_URL,
                timeout=LLM_TIMEOUT
            )
            logger.info("✅ [RAG] AI Engine initialized with direct AsyncOpenAI client.")
        else:
            self.client = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

    def _normalize_law_title(self, title: str) -> str:
        return ' '.join(title.strip().split())

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
        manifest_lines = ["\n<<< REGJISTRI ZYRTAR I DOKUMENTEVE TË LËNDËS (PËR CITIM ME LINKE) >>>\n"]
        context = "\n<<< FASHIKULLI I PROVEVE DHE PËRMBAJTJA E TYRE >>>\n"
        
        if db_documents:
            for idx, doc in enumerate(db_documents, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or "Dokument.pdf"
                
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"
                manifest_lines.append(f"{idx}. {doc_clickable_link}")

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

                if raw_t and summ:
                    text_content = f"PËRMBLEDHJE: {summ}\nPËRMBAJTJA TEKSTUALE:\n{raw_t[:12000]}"
                elif raw_t:
                    text_content = f"PËRMBAJTJA TEKSTUALE:\n{raw_t[:14000]}"
                elif summ:
                    text_content = f"PËRMBLEDHJE: {summ}"
                else:
                    text_content = "Dokument i administruar në fashikull."

                context += f"\n==================== DOKUMENTI #{idx} ====================\n"
                context += f"CITIMI ZYRTAR: {doc_clickable_link}\n"
                context += f"{text_content}\n"
                context += f"===========================================================\n"
        else:
            context += "Nuk ka dokumente të bashkangjitura në fashikull.\n\n"

        context += "\n<<< PARAGRAFET SELEKTIVE TË KËRKIMIT SEMANTIK >>>\n"
        for idx, d in enumerate(case_docs):
            text_content = self._get_expanded_text(d)
            context += f"[{d.get('source') or 'Dokument'}, FAQJA: {d.get('page') or 'N/A'}]: {text_content}\n"

        context += "\n<<< BAZA LIGJORE STATUTORE E KOSOVËS >>>\n"
        for d in global_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number', 'N/A')
            text_content = self._get_expanded_text(d)
            context += f"LIGJI: {law_title}, Neni {article_num}\nPËRMBAJTJA: {text_content}\n"

        return "\n".join(manifest_lines), context

    def _get_role_adapted_pillars(self, position: str) -> List[Tuple[str, str]]:
        """Përcakton 4 pyetjet startuese në mënyrë 100% të përshtatur sipas Pozicionit."""
        pos = position.upper()
        if pos == "DEFENDANT":
            return [
                ("STRATEGJIA", "Identifiko 3 pikat kryesore për rrëzimin e padisë dhe provat shfajësuese në fashikull."),
                ("BAZA_LIGJORE", "Analizo shkeljet procedurale të paditësit, parashkrimin e afateve dhe prapësimet sipas LPK."),
                ("PYETESORI", "Gjenero pyetjet kurth për të rrëzuar dëshmitarët e paditësit dhe zbuluar kontradiktat në seancë."),
                ("RAPORTI", "Përgatit një përmbledhje ekzekutive mbi rreziqet e padisë, prapësimet kryesore dhe hapat për mbrojtjen e klientit.")
            ]
        elif pos == "PLAINTIFF":
            return [
                ("STRATEGJIA", "Identifiko 3 pikat kryesore ku mbështetet padia jonë dhe provat e përgjegjësisë së kundërshtarit."),
                ("BAZA_LIGJORE", "Analizo bazën ligjore të kërkesëpadisë dhe provat për shpërblimin e dëmit sipas LPK dhe kodeve përkatëse."),
                ("PYETESORI", "Gjenero pyetjet taktike për të kryqëzuar dhe demaskuar palën e paditur në seancë."),
                ("RAPORTI", "Përgatit një përmbledhje ekzekutive mbi shanset e fitimit të padisë, dëmet dhe hapat proceduralë për klientin.")
            ]
        else: # NEUTRAL
            return [
                ("STRATEGJIA", "Vlerëso në mënyrë objektive 3 provat kryesore dhe peshën e tyre ligjore në këtë dosje."),
                ("BAZA_LIGJORE", "Analizo barrën e provës (Onus Probandi) dhe përputhshmërinë ligjore për të dyja palët sipas LPK."),
                ("PYETESORI", "Gjenero pyetjet sqaruese të gjykatës për të vërtetuar faktet thelbësore kontestuese."),
                ("RAPORTI", "Përgatit sintezën e paanshme të dosjes dhe rekomandimet objektive ligjore.")
            ]

    def _determine_remaining_pills(self, query: str, position: str, history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Llogarit pyetjet e mbetura progresive (3 ➡️ 2 ➡️ 1) sipas rolit."""
        role_pillars = self._get_role_adapted_pillars(position)

        all_past_queries = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    all_past_queries.append(str(msg.get("content", "")).lower())
        all_past_queries.append(query.lower())
        combined_text = " ".join(all_past_queries)

        remaining = []
        
        # 1. Kontrollo Strategjinë
        if "strategjia" not in combined_text and "3 pikat" not in combined_text and "rrëzimin" not in combined_text:
            remaining.append(role_pillars[0][1])
            
        # 2. Kontrollo Bazën Ligjore
        if "lpk" not in combined_text and "baza ligjore" not in combined_text and "parashkrimin" not in combined_text and "barrën" not in combined_text:
            remaining.append(role_pillars[1][1])
            
        # 3. Kontrollo Pyetësorin e Seancës
        if "pyetësor" not in combined_text and "pyetjet" not in combined_text and "dëgjimin" not in combined_text and "kurth" not in combined_text:
            remaining.append(role_pillars[2][1])
            
        # 4. Kontrollo Raportin për Klientin
        if "raporti" not in combined_text and "përmbledhje ekzekutive" not in combined_text and "informimin" not in combined_text and "memorandum" not in combined_text:
            remaining.append(role_pillars[3][1])

        if remaining:
            return remaining[:3]
        
        if position.upper() == "DEFENDANT":
            return [
                "A ka ndonjë provë tjetër në fashikull që rrëzon pretendimet e paditësit?",
                "Si mund të kërkojmë kompensimin e shpenzimeve të procedurës për shkak të padisë së pabazuar?",
                "Cilat janë afatet ligjore prekluzive që paditësi i ka tejkaluar?"
            ]
        elif position.upper() == "PLAINTIFF":
            return [
                "Cilat janë provat shtesë që duhet të depozitojmë për të kërkuar masë të menjëhershme sigurie?",
                "Si llogaritet dëmi material dhe kamata ligjore prej 8% mbi vlerën e kërkuar?",
                "Cilat janë pyetjet shtesë për të provuar dashjen dhe përgjegjësinë e të paditurit?"
            ]
        else:
            return [
                "Cilat fakte kërkojnë marrjen e një ekspertize shtesë financiare apo mjekësore?",
                "Si ndahet barra e provës midis paditësit dhe të paditurit për pretendimet kryesore?",
                "Cilat janë alternativat për zgjidhjen e çështjes me ndërmjetësim?"
            ]

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            yield AI_DISCLAIMER
            return

        from app.services import vector_store_service, llm_service

        client_position = "DEFENDANT"
        client_name = "Pala Kliente"
        opposing_name = "Pala Kundërshtare"
        db_documents = []

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or case_doc.get("title") or client_name
                    opposing_name = case_doc.get("opposing_party") or case_doc.get("opponent") or opposing_name

                doc_cursor = self.db.documents.find({
                    "$or": [{"case_id": case_id}, {"case_id": c_oid}], 
                    "status": {"$ne": "DELETED"}
                })
                db_documents = list(doc_cursor)
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        identity_header = llm_service.build_dynamic_identity_header(
            client_name=client_name, 
            opposing_name=opposing_name, 
            position=client_position
        )

        optimized_query = self._optimize_query(query)
        sanitized_query = llm_service._sanitize_and_disambiguate_prompt(optimized_query, opposing_name=opposing_name)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=sanitized_query, case_context_id=case_id, n_results=12
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=sanitized_query, n_results=6
        )

        manifest_str, context_str = self._build_context(case_docs, global_docs, db_documents)

        # LLOGARITJA E PYETJEVE TË MBETURA TË PËRSHTATURA SIPAS ROLIT
        suggested_pills = self._determine_remaining_pills(query=query, position=client_position, history=history)
        pills_formatted_instruction = "\n".join([f"[PILL: {p}]" for p in suggested_pills])

        system_prompt = f"""
        {identity_header}

        Ti je "Sokrati - Krye-Strategu dhe Avokati Elitar i Drejtësisë në Kosovë".

        MANDATI DHE BESNIKËRIA JURIDIKE:
        - KLIENTI YNË: **{client_name}** (Pozicioni: **{client_position}**).
        - PALA KUNDËRSHTARE: **{opposing_name}**.

        REGJISTRI I SKEDARËVE REALË TË LËNDËS:
        {manifest_str}

        RREGULLAT E ANALIZËS SIPAS ROLIT PROCEDURAL:
        1. BAZOHU EKSKLUZIVISHT NË PROVAT E FASHIKULLIT DHE MBRO INTERESIN E {client_name}.
        2. ÇDO CITIM I PROVAVE DUHET TË JETË LINK I KLIKUESHËM: `[Emri_Skedarit.pdf](/documents/ID)`
        3. PËRSHTAT PËRGJIGJEN SIPAS POZICIONIT PROCEDURAL ({client_position}):
           - Nëse Paditës: thekso provat e dëmit, përgjegjësisë së {opposing_name} dhe masat e sigurisë.
           - Nëse I Paditur: thekso provat shfajësuese, kontradiktat e {opposing_name} dhe prapësimet ligjore.
           - Nëse Neutral: analizo paanshmërinë dhe peshën e provave.
        4. Cito nenet e sakta të ligjeve të Kosovës (LPK, KPRK, KPPRK, LFK, LMD).

        STRUKTURA E PËRGJIGJES:
        ### 1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
        ### 2. BAZA LIGJORE DHE ANALIZA PROCEDURALE
        ### 3. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM

        FORMATIMI I SUGJERIMEVE NË FUND:
        {pills_formatted_instruction}
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
                max_tokens=4096
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER