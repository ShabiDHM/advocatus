# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - UNIVERSAL AUTONOMOUS LEGAL ENGINE V79.0 (KOSOVO CITATION FORMATTING & MULTIMEDIA SYNC)

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
        
        if API_KEY:
            self.client = AsyncOpenAI(
                api_key=API_KEY,
                base_url=OPENROUTER_BASE_URL,
                timeout=LLM_TIMEOUT
            )
            logger.info("✅ [RAG] Universal Autonomous AI Engine initialized.")
        else:
            self.client = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

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
        manifest_lines = ["\n<<< REGJISTRI ZYRTAR I SKEDARËVE TË FASHIKULLIT (PËR CITIM ME LINKE) >>>\n"]
        context = "\n<<< PËRMBAJTJA E PLOTË E PROVEVE DHE DOKUMENTEVE TË LËNDËS >>>\n"
        
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
                    text_content = f"PËRMBLEDHJE: {summ}\nPËRMBAJTJA E TEKSTIT:\n{raw_t[:14000]}"
                elif raw_t:
                    text_content = f"PËRMBAJTJA E TEKSTIT:\n{raw_t[:16000]}"
                elif summ:
                    text_content = f"PËRMBLEDHJE: {summ}"
                else:
                    text_content = "Dokument i administruar në fashikull."

                context += f"\n==================== DOKUMENTI #{idx} ====================\n"
                context += f"CITIMI I SAKTË: {doc_clickable_link}\n"
                context += f"{text_content}\n"
                context += f"===========================================================\n"
        else:
            context += "Nuk ka dokumente të bashkangjitura në fashikull.\n\n"

        context += "\n<<< PARAGRAFET SELEKTIVE NGA KËRKIMI SEMANTIK I LËNDËS >>>\n"
        for idx, d in enumerate(case_docs):
            text_content = self._get_expanded_text(d)
            context += f"[{d.get('source') or 'Dokument'}, FAQJA: {d.get('page') or 'N/A'}]: {text_content}\n"

        context += "\n<<< BAZA LIGJORE STATUTORE E REPUBLIKËS SË KOSOVËS >>>\n"
        for d in global_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number', 'N/A')
            text_content = self._get_expanded_text(d)
            context += f"LIGJI: {law_title}, Neni {article_num}\nPËRMBAJTJA: {text_content}\n"

        return "\n".join(manifest_lines), context

    def _get_role_adapted_pillars(self, position: str) -> List[Tuple[str, str]]:
        pos = position.upper()
        if pos == "PLAINTIFF":
            p1 = "Identifiko 3 shtyllat kryesore të kërkesëpadisë, përgjegjësinë e kundërshtarit dhe provat vendimtare në fashikull."
            p2 = "Analizo bazën ligjore procedurale dhe materiale, afatet dhe zbatueshmërinë e neneve të ligjeve përkatëse të Kosovës."
            p3 = "Gjenero pyetjet taktike të ballafaqimit për dëgjimin e palëve dhe dëshmitarëve në seancë."
            p4 = "Përgatit një përmbledhje ekzekutive mbi rreziqet ligjore, shanset e suksesit dhe hapat e mëtejshëm proceduralë."
        elif pos == "NEUTRAL":
            p1 = "Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara."
            p2 = "Vlerëso ligjshmërinë e pretendimeve të palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit në fuqi."
            p3 = "Identifiko mospërputhjet thelbësore procedurale dhe mjetet juridike të zbatueshme në këtë fazë të lëndës."
            p4 = "Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme."
        else: # DEFENDANT
            p1 = "Analizo 3 prapësimet kryesore të mbrojtjes, kontradiktat e palës kundërshtare dhe provat shfajësuese në fashikull."
            p2 = "Analizo bazën ligjore procedurale dhe materiale, afatet dhe zbatueshmërinë e neneve të ligjeve përkatëse të Kosovës."
            p3 = "Gjenero pyetjet taktike dhe kundër-pyetjet për ballafaqimin e dëshmitarëve dhe ekspertëve në seancë."
            p4 = "Përgatit një përmbledhje ekzekutive mbi rreziqet ligjore, shanset e suksesit dhe hapat e mëtejshëm proceduralë."

        return [
            ("PILLAR_1", p1),
            ("PILLAR_2", p2),
            ("PILLAR_3", p3),
            ("PILLAR_4", p4)
        ]

    def _determine_remaining_pills(self, query: str, position: str, history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        pillars = self._get_role_adapted_pillars(position)

        all_past_queries = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    all_past_queries.append(str(msg.get("content", "")).lower())
        all_past_queries.append(query.lower())
        combined_text = " ".join(all_past_queries)

        remaining = []

        if not any(k in combined_text for k in ["3 pikat kryesore", "3 shtyllat kryesore", "3 prapësimet kryesore", "mbështetet padia", "gjendjen e lëndës"]):
            remaining.append(pillars[0][1])

        if not any(k in combined_text for k in ["bazën ligjore", "përputhshmërinë procedurale", "ligjshmërinë e pretendimeve"]):
            remaining.append(pillars[1][1])

        if not any(k in combined_text for k in ["pyetjet taktike", "kundër-pyetjet", "mospërputhjet thelbësore", "dëgjimin e palëve"]):
            remaining.append(pillars[2][1])

        if not any(k in combined_text for k in ["përmbledhje ekzekutive", "memorandumin objektiv", "rreziqet ligjore"]):
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
            user_id=user_id, query_text=sanitized_query, case_context_id=case_id, n_results=16
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=sanitized_query, n_results=8
        )

        manifest_str, context_str = self._build_context(case_docs, global_docs, db_documents)

        remaining_pills = self._determine_remaining_pills(query=query, position=client_position, history=history)
        
        if remaining_pills and len(remaining_pills) > 0:
            formatted_suggestions = (
                "NË FUND TË PËRGJIGJES TËNDE, SHTO SAKTËSISHT KËTË BLOK SUGJERIMESH:\n"
                "Sugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
            )
        else:
            formatted_suggestions = "MOS shto asnjë seksion Sugjerime në fund të përgjigjes."

        # RREGULLAT E ARSYETIMIT SIPAS POZICIONIT PROCEDURAL
        if client_position == "NEUTRAL":
            role_instructions = """
            TI JE NË ROLIN: **NEUTRAL / AUDITOR GJYQËSOR I PAANSHËM**.
            1. PËRCAKTIMI I FAZËS PROCEDURALE:
               - Skoni shkresat për të verifikuar nëse lënda ka Aktgjykim të shkallës së parë apo Vendim të Apelit në fashikull.
               - Nëse lënda është vendosur nga gjykatat, analizo arsyetimin ligjor dhe mjetet e jashtëzakonshme pa marrë anësi.
            2. OBJEKTIVITETI: Mos përdor 'padia jonë' apo 'mbrojtja jonë'. Analizo ligjshmërinë e shkresave me paanshmëri magjistrati.
            """
        elif client_position == "PLAINTIFF":
            role_instructions = f"""
            TI JE NË ROLIN: **PADITËS / SULM PROCEDURAL** (Mbro interesin e {client_name}).
            - Thekso provat që mbështesin kërkesën, përgjegjësinë e palës kundërshtare ({opposing_name}) dhe kërkesat ligjore.
            """
        else:
            role_instructions = f"""
            TI JE NË ROLIN: **I PADITUR / MBROJTJE GJYQËSORE** (Mbro interesin e {client_name}).
            - Thekso prapësimet procedurale, provat shfajësuese dhe kontradiktat e palës kundërshtare ({opposing_name}).
            """

        system_prompt = f"""
        {identity_header}

        Ti je "Sokrati - Krye-Strategu dhe Avokati Elitar i Drejtësisë në Kosovë".

        METADATAT E LËNDËS:
        - TITULLI: **{case_title}**
        - PALËT: **{client_name}** vs. **{opposing_name}**
        - ROLI I ZGJEDHUR I PËRDORUESIT: **{client_position}**
        {f'- PËRSHKRIMI: {case_desc}' if case_desc else ''}

        {role_instructions}

        REGJISTRI I SKEDARËVE TË FASHIKULLIT:
        {manifest_str}

        DOKUMENTET DHE SHKRESAT E LEXUARA NGA FASHIKULLI:
        {context_str}

        RREGULLAT E SAKTËSISË PROCEDURALE DHE CITIMIT TË KOSOVËS:
        1. STANDARDI I CITIMIT TË NENEVE TË KOSOVËS:
           - Nenet shkruhen me formatin zyrtar: `Neni [Numri]` ose `Neni [Numri], paragrafi [X]`. MOS përdor pika dhjetore si '386.2' apo '428.1'.
           - NËSE nuk e ke numrin ekzakt të nenit në bazën statutore, cito me emër INSTITUTIN PROCEDURAL (p.sh. 'dispozitat e LPK-së për dorëzimin e ftesave dhe njoftimin e rregullt', 'dispozitat e LPK-së për shkeljet thelbësore procedurale', 'Ligji për Mbrojtjen nga Dhuna në Familje'). MOS shpik numra të pasaktë nenesh!
        2. CITIMI I PROVEVE TË FASHIKULLIT:
           - Çdo provë e fashikullit DUHET të citohet si link i klikueshëm: `[Emri_Skedarit.pdf](/documents/ID)`.
           - Nenet e ligjit shkruhen natyrshëm (p.sh. `Neni 12 i LPK`). MOS përdor kllapa [ ] për nenet e ligjit.
        3. BALLAFAQIMI DHE PROVAT MULTIMEDIALE:
           - Nëse fashikulli përmban inqizime audio apo video, integroji ato në analizë duke evidentuar vlerën e tyre provuese.

        STRUKTURA E DETYRUESHME E PËRGJIGJES:
        ### 1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
        ### 2. BAZA LIGJORE DHE ANALIZA PROCEDURALE
        ### 3. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM

        {formatted_suggestions}
        """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": sanitized_query}
                ],
                temperature=0.05,
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