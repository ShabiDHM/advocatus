# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V33.1 (SOLVED MONGO TRUTHY EXCEPTION)

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
1. Çdo citim ligjor DUHET të përmbajë **EMRIN E PLOTË ZYRTAR TË LIGJIT** dhe **NUMRIN ZYRTAR** (p.sh., "Nr. 04/L-077").  
   **Shembull i saktë:** `Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve, Neni 5`  
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

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict]) -> str:
        context = "\n<<< MATERIALET E DOSJES >>>\n"
        for idx, d in enumerate(case_docs):
            text_content = self._get_expanded_text(d)
            context += f"[{d.get('source') or 'Dokument'}, FAQJA: {d.get('page') or 'N/A'}]: {text_content}\n\n"

        context += "\n<<< BAZA LIGJORE STATUTORE >>>\n"
        for d in global_docs:
            law_title = d.get('law_title') or d.get('source') or "Ligji përkatës"
            article_num = d.get('article_number', 'N/A')
            text_content = self._get_expanded_text(d)
            context += f"LIGJI: {law_title}, Neni {article_num}\nPËRMBAJTJA: {text_content}\n\n"
        return context

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            yield AI_DISCLAIMER
            return

        from app.services import vector_store_service

        logger.info(f"🔍 RAG Chat request: query='{query[:100]}...'")

        client_position = "DEFENDANT"
        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc and case_doc.get("client_position"):
                    client_position = str(case_doc["client_position"]).upper()
            except Exception as ex:
                logger.warning(f"Could not read case position: {ex}")

        # Dynamic Tri-Party Role Instructions
        if client_position == "PLAINTIFF":
            role_instruction = """
            **MANDATI LIGJOR: SULM / PADITËS**
            - Ti je Avokati i Paditësit / të Dëmtuarit.
            - Analiza jote DUHET të përqendrohet 100% në vërtetimin e përgjegjësisë së palës tjetër, sigurimin e provave për dëmin e shkaktuar, dhe forcat e kërkesëpadisë.
            - Rrëzo çdo prapësim apo pretendim mbrojtës të të paditurit.
            """
        elif client_position == "NEUTRAL":
            role_instruction = """
            **MANDATI LIGJOR: NEUTRAL / OBJEKTIV**
            - Ti je një Analist dhe Auditor Ligjor plotësisht Objektiv dhe Neutral.
            - Analizo rastin me paanshmëri zyrtare: pesho argumentet e të dyja palëve, vlerëso barrën e provës (barra e provës), dhe trego me objektivitet se cila palë ka bazën më të fortë ligjore sipas kornizës statutore të Kosovës.
            """
        else:
            role_instruction = """
            **MANDATI LIGJOR: MBROJTJE / I PADITUR**
            - Ti je Mbrojtësi Ligjor i të Paditurit / të Akuzuarit.
            - Analiza jote DUHET të përqendrohet 100% në rrëzimin e padisë, shfrytëzimin e gabimeve procedurale të paditësit (si parashkrimi i afateve, mungesa e prokurës, apo mungesa e provave), dhe mbrojtjen strategjike.
            - Rrëzo pretendimet e paditësit med prapësime ose kundërpadi.
            """

        optimized_query = self._optimize_query(query)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=optimized_query, n_results=4
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=optimized_query, n_results=3
        )

        context_str = self._build_context(case_docs, global_docs)

        prompt = f"""
        Ti je "Juristi AI - Asistenti i Avokatit dhe Auditorit Ligjor". 

        {role_instruction}

        **RREGULLI I REFUZIMIT (I DETYRUESHËM):**
        Nëse përgjigjja nuk mund të nxirret nga [KONTEKSTI], je i ndaluar rreptësisht të përgjigjesh.
        Përgjigju VETËM me: "Më vjen keq, pot ky informacion nuk gjendet në dokumentet e ngarkuara."

        **PRIORITETI I BURIMEVE:**
        Në rast konflikti midis <<< MATERIALET E DOSJES >>> dhe <<< BAZA LIGJORE STATUTORE >>>, **materialet e dosjes kanë përparësi absolute**.

        {PROTOKOLLI_MANDATOR}

        **KONTEKSTI:**
        {context_str}

        **PYETJA AKTUALE:** "{query}"

        **STRUKTURA (OBLIGATIVE):**
        ### 1. ANALIZA E FAKTEVE

        ### 2. BAZA LIGJORE DHE RELEVANCA

        ### 3. KONKLUZIONI STRATEGJIK

        Fillo hartimin tani:
        """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.2,
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