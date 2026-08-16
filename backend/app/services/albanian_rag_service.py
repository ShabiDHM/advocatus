# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - RAG SERVICE V40.0 (STRICT FACTUAL GROUNDING • ZERO HARDCODED DOMAIN BIAS)

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

AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga Juristi AI, ekskluzivisht për përdorim dhe referencë ligjore.*"

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

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict], db_documents: List[Dict]) -> str:
        context = "\n<<< FASHIKULLI I PROVEVE MATERIALE TË DOSJES >>>\n"
        
        if db_documents:
            for idx, doc in enumerate(db_documents, 1):
                file_name = doc.get("file_name") or doc.get("title") or "Dokument"
                raw_t = doc.get("extracted_text") or doc.get("text_content") or ""
                summ = doc.get("summary") or ""
                
                if summ == "Sinteza...":
                    summ = ""

                if raw_t and summ:
                    text_content = f"PËRMBLEDHJE: {summ}\nTEKSTI:\n{raw_t[:10000]}"
                elif raw_t:
                    text_content = f"TEKSTI:\n{raw_t[:12000]}"
                elif summ:
                    text_content = f"PËRMBLEDHJE: {summ}"
                else:
                    text_content = "Dokument i verifikuar në fashikull."

                context += f"\n==================== DOKUMENTI #{idx} ====================\n"
                context += f"TITULLI I SKEDARIT: {file_name}\n"
                context += f"PËRMBAJTJA:\n{text_content}\n"
                context += f"===========================================================\n"
        else:
            context += "Nuk ka dokumente të bashkangjitura në fashikull.\n\n"

        context += "\n<<< PARAGRAFET SELEKTIVE NGA KËRKIMI SEMANTIK >>>\n"
        for idx, d in enumerate(case_docs):
            text_content = self._get_expanded_text(d)
            context += f"[{d.get('source') or 'Dokument'}, FAQJA: {d.get('page') or 'N/A'}]: {text_content}\n"

        context += "\n<<< BAZA LIGJORE STATUTORE E KOSOVËS >>>\n"
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

                doc_cursor = self.db.documents.find({"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}})
                db_documents = list(doc_cursor)
            except Exception as ex:
                logger.warning(f"Could not read case details: {ex}")

        identity_header = llm_service.build_dynamic_identity_header(
            client_name=client_name, 
            opposing_name=opposing_name, 
            position=client_position
        )

        optimized_query = self._optimize_query(query)
        sanitized_query = llm_service._sanitize_and_disambiguate_prompt(optimized_query, opposing_name=opposing_name)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=sanitized_query, case_context_id=case_id, n_results=8
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=sanitized_query, n_results=6
        )

        context_str = self._build_context(case_docs, global_docs, db_documents)

        # PROMPTI 100% DINAMIK PA ASNJË TEMATIKË TË HARDKODUAR
        system_prompt = f"""
        {identity_header}

        Ti je "Juristi AI - Asistenti dhe Avokati Strateg i Drejtësisë në Kosovë".

        RREGULLAT E HEKURTA TË FAKTEVE (ZERO HALUCINIME):
        1. BAZOHU EKSKLUZIVISHT NË TEKSTIN DHE DOKUMENTET E KËSAJ DOSJE SPECIFIKE!
        2. MOS SHPIK LIGJE APO TEMA TË PAQENA (nëse dosja bën fjalë për kujdestari fëmije, urdhërmbrojtje apo procedurë penale, MOS përmend prona intelektuale apo kompani!).
        3. KLIENTI YNË ËSHTË: **{client_name}** (Në rolin: **{client_position}**). PALA KUNDËRSHTARE: **{opposing_name}**.
        4. Kur pyetesh për "padinë tonë", "kërkesat tona" apo "provat tona", analizo kërkesat e {client_name} dhe përdor provat shkencore e materiale të fashikullit për të rrëzuar pretendimet e {opposing_name}.
        5. Cito nenet reale të ligjeve përkatëse të Kosovës (LPK, KPRK, KPPRK, LFK, LMD).

        STRUKTURA E PËRGJIGJES:
        ### 1. ANALIZA E FAKTEVE DHE PROVAT E FASHIKULLIT
        ### 2. BAZA LIGJORE DHE KORNIZA STATUTORE
        ### 3. STRATEGJIA DHE HAPAT PROCEDURALË

        Në fund shto 3 pyetje interaktive:
        [PILL: Pyetja e parë strategjike...]
        [PILL: Pyetja e dytë procedurale...]
        [PILL: Pyetja e tretë për prova...]
        """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": sanitized_query}
                ],
                temperature=0.0,
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