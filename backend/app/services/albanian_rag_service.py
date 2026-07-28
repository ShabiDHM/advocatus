# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V36.0 (STRICT DOCUMENT BOUNDARY ISOLATION & ANTI-CONFUSION LOCK)

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
LLM_TIMEOUT = 120

AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

PROTOKOLLI_MANDATOR = """
**URDHËRA TË RREPTË FORMATIMI (NDIQINI ME PRECIZION):**
1. Çdo citim ligjor DUHET të përmbajë **EMRIN E PLOTË ZYRTAR TË LIGJIT** dhe **NUMRIN ZYRTAR** (p.sh., "Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve, Neni 180").
2. Për çdo ligj të cituar, DUHET të shtoni rreshtin: **RELEVANCA:** [Pse ky nen është thelbësor për këtë rast].
3. Përdor TITUJT MARKDOWN (###) për të ndarë seksionet.
"""

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

    def _extract_law_number(self, text: str) -> Optional[str]:
        match = re.search(r'Nr\.?\s*([\d/L\-]+)', text, re.IGNORECASE)
        return match.group(1) if match else None

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
            r"\bKPK\b": "Kodi Penal i Republikës së Kosovës",
            r"\bKPPK\b": "Kodi i Procedurës Penale",
            r"\bLPP\b": "Ligji për Procedurën Kontestimore",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLPA\b": "Ligji për Procedurën Administrative",
            r"\bKPC\b": "Kodi i Procedurës Civile",
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

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict], db_documents: List[Dict]) -> str:
        context = "\n<<< FASHIKULLI I PROVEVE MATERIALE (DOKUMENTE TË IZOLUARA) >>>\n"
        
        # 1. Direct Extracted Document Text with Strict Boundary Tagging
        if db_documents:
            for idx, doc in enumerate(db_documents, 1):
                file_name = doc.get("file_name") or doc.get("title") or "Dokument"
                raw_t = doc.get("extracted_text") or ""
                summ = doc.get("summary") or ""
                
                if summ == "Sinteza...":
                    summ = ""

                if raw_t and summ:
                    text_content = f"PËRMBLEDHJE: {summ}\nTEKSTI EKSKLUSIV I KËTIJ SKEDARI:\n{raw_t[:3500]}"
                elif raw_t:
                    text_content = f"TEKSTI EKSKLUSIV I KËTIJ SKEDARI:\n{raw_t[:4000]}"
                elif summ:
                    text_content = f"PËRMBLEDHJE: {summ}"
                else:
                    text_content = "Dokument i verifikuar në fashikull (Teksti në procesim)."

                context += f"\n==================== DOKUMENTI INDIVIDUAL #{idx} ====================\n"
                context += f"EMRI I SKEDARIT: {file_name}\n"
                context += f"PËRMBAJTJA TIEKSTUALE TË KËTIJ SKEDARI:\n{text_content}\n"
                context += f"=======================================================================\n"
        else:
            context += "Nuk ka dokumente të bashkangjitura në fashikull.\n\n"

        # 2. Vector Semantic Chunks
        context += "\n<<< PARAGRAFET SELEKTIVE NGA KËRKIMI SEMANTIK >>>\n"
        for idx, d in enumerate(case_docs):
            text_content = self._get_expanded_text(d)
            context += f"[{d.get('source') or 'Dokument'}, FAQJA: {d.get('page') or 'N/A'}]: {text_content}\n"

        # 3. Global Statutory Law Base
        context += "\n<<< BAZA LIGJORE STATUTORE (LPK, LMD, LSHT) >>>\n"
        for d in global_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number', 'N/A')
            text_content = self._get_expanded_text(d)
            context += f"LIGJI: {law_title}, Neni {article_num}\nPËRMBAJTJA: {text_content}\n"
        return context

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            yield AI_DISCLAIMER
            return

        from app.services import vector_store_service, llm_service

        logger.info(f"🔍 RAG Chat request: query='{query[:100]}...'")

        client_position = "DEFENDANT"
        client_name = "Shaban Bala"
        opposing_name = "Getting Competent ShPK / Raimier Gerger"
        db_documents = []

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc:
                    if case_doc.get("client_position"):
                        client_position = str(case_doc["client_position"]).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    opposing_name = case_doc.get("opposing_party") or opposing_name

                # FETCH ALL UPLOADED CASE DOCUMENTS DIRECTLY FROM MONGO
                doc_cursor = self.db.documents.find({"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}})
                db_documents = list(doc_cursor)
            except Exception as ex:
                logger.warning(f"Could not read case details or documents from Mongo: {ex}")

        # Dynamic Identity Header with Strict Contract Signatory Rules
        identity_header = llm_service.build_dynamic_identity_header(
            client_name=client_name, 
            opposing_name=opposing_name, 
            position=client_position
        )

        optimized_query = self._optimize_query(query)
        sanitized_query = llm_service._sanitize_and_disambiguate_prompt(optimized_query, opposing_name=opposing_name)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=sanitized_query, case_context_id=case_id, n_results=6
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=sanitized_query, n_results=4
        )

        context_str = self._build_context(case_docs, global_docs, db_documents)

        prompt = f"""
        {identity_header}

        Ti je "Juristi AI - Asistenti i Avokatit dhe Auditorit Ligjor".

        **RREGULLAT KRITIKE TË MOS-PËRZIJES SË DOKUMENTEVE (STRICT ISOLATION MANDATE):**
        1. Çdo dokument në fashikull është me vete. MOS PËRZI faktet, sekretarët, avokatët apo procesverbalet e seancave (p.sh. "Seanca e par Get_com.pdf") me përmbajtjen e një kontrate origjinale (p.sh. "Contract - Rainer Gerke.pdf")!
        2. Kur pyetesh për KONTRATËN ("Contract - Rainer Gerke.pdf"), lexo VETËM tekstin brenda bllokut që përket me atë skedar.
        3. Identifiko me saktësi absolute palët nënshkruese që citohen EKSPLIÇITISHT në vetë atë kontratë (Party A vs Party B). Mos përmend përfaqësueset ligjore ose procesverbalet e gjykatës sikur janë nënshkrues të kontratës!
        
        {PROTOKOLLI_MANDATOR}

        **KONTEKSTI I LËNDËS ME SKEDARË TË IZOLUAR:**
        {context_str}

        **PYETJA E DREJTPËRDREJTË E PËRDORUESIT:** "{sanitized_query}"

        **STRUKTURA E OBLIGUESHME E PËRGJIGJES:**
        ### 1. ANALIZA E FAKTEVE (Nga skedari përkatës)

        ### 2. BAZA LIGJORE DHE RELEVANCA

        ### 3. KONKLUZIONI STRATEGJIK

        Fillo përgjigjen tani:
        """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": sanitized_query}
                ],
                temperature=0.1,  # Lower temperature for maximum literal accuracy
                stream=True
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER