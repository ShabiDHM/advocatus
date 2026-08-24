# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - UNIVERSAL AUTONOMOUS LEGAL ENGINE V89.0 (AUTO-LINKING INJECTOR & DETERMINISTIC 4-3-2-1-0 PILLARS)

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
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE ME LINKE TË KLIKUESHME >>>\n"]
        context = "\n<<< PËRMBAJTJA E PROVEVE TË FASHIKULLIT >>>\n"
        
        if db_documents:
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

                if raw_t and summ:
                    text_content = f"PËRMBLEDHJE: {summ}\nPËRMBAJTJA:\n{raw_t[:14000]}"
                elif raw_t:
                    text_content = f"PËRMBAJTJA:\n{raw_t[:16000]}"
                elif summ:
                    text_content = f"PËRMBLEDHJE: {summ}"
                else:
                    text_content = "Dokument i administruar në fashikull."

                context += f"\n--- SHKRESA: {doc_clickable_link} ---\n"
                context += f"{text_content}\n"
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
            p1 = "Identifiko 3 shtyllat kryesore ku mbështetet kërkesëpadia jonë dhe provat vendimtare që ngarkojnë të paditurin."
            p2 = "Analizo bazën ligjore të kërkesëpadisë, afatet procedurale dhe nenet përkatëse të ligjeve të Kosovës."
            p3 = "Gjenero pyetjet taktike për të ballafaquar të paditurin dhe dëshmitarët e tij në seancë."
            p4 = "Llogarit dëmet e kërkuara sipas ligjit dhe përgatit përmbledhjen ekzekutive mbi ecurinë e padisë."
        elif pos == "NEUTRAL":
            p1 = "Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara."
            p2 = "Vlerëso ligjshmërinë e pretendimeve të të dyja palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit."
            p3 = "Identifiko mospërputhjet thelbësore dhe gjenero pyetje neutrale sqaruese për vërtetimin e fakteve."
            p4 = "Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme."
        else: # DEFENDANT
            p1 = "Analizo 3 prapësimet kryesore të mbrojtjes, mungesën e provave të paditësit dhe faktet shfajësuese në fashikull."
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
                    all_past_user_messages.append(str(msg.get("content", "")).lower().strip())
        all_past_user_messages.append(query.lower().strip())
        combined_text = " ".join(all_past_user_messages)

        remaining = []

        # Shtylla 1
        if not any(k in combined_text for k in ["3 shtyllat kryesore", "3 prapësimet kryesore", "gjendjen e lëndës", "mbështetet kërkesëpadia", "faktet shfajësuese"]):
            remaining.append(pillars[0][1])

        # Shtylla 2
        if not any(k in combined_text for k in ["bazën ligjore të kërkesëpadisë", "bazën ligjore të prapësimeve", "ligjshmërinë e pretendimeve"]):
            remaining.append(pillars[1][1])

        # Shtylla 3
        if not any(k in combined_text for k in ["pyetjet taktike për të ballafaquar", "kundër-pyetjet taktike", "pyetjet për zbardhjen"]):
            remaining.append(pillars[2][1])

        # Shtylla 4
        if not any(k in combined_text for k in ["llogarit dëmet", "rreziqet dhe raporti", "memorandumin objektiv"]):
            remaining.append(pillars[3][1])

        return remaining

    def _inject_document_links(self, text: str, db_documents: List[Dict[str, Any]]) -> str:
        """
        INJEKTUESI AUTOMATIK I LINKEVE (DETERMINISTIK):
        Sa herë që në tekst shfaqet emri i një skedari, kthehet automatikisht në link Markdown [file.pdf](/documents/id).
        """
        if not text or not db_documents:
            return text

        result = text
        for doc in db_documents:
            doc_id = str(doc.get("_id", ""))
            fname = str(doc.get("file_name") or doc.get("title") or "").strip()
            if not fname or len(fname) < 4:
                continue

            clean_base_name = re.sub(r'\.pdf$', '', fname, flags=re.IGNORECASE).strip()
            target_link = f"[{fname}](/documents/{doc_id})"

            # Zëvendëso emrin e plotë nëse nuk është tashmë link
            full_pattern = re.compile(rf'(?<!\[){re.escape(fname)}(?!\]\(/documents/)', re.IGNORECASE)
            result = full_pattern.sub(target_link, result)

            # Zëvendëso emrin pa .pdf nëse shfaqet i izoluar
            if len(clean_base_name) > 6:
                base_pattern = re.compile(rf'(?<!\[){re.escape(clean_base_name)}(?:\.pdf)?(?!\]\(/documents/)', re.IGNORECASE)
                result = base_pattern.sub(target_link, result)

        return result

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

        # Llogaritja e sigurt e kartave të mbetura (3 -> 2 -> 1 -> 0)
        remaining_pills = self._determine_remaining_pills(query=query, position=client_position, history=history)

        # RREGULLAT E ARSYETIMIT JURIDIK
        if client_position == "PLAINTIFF":
            role_instructions = f"""
            PERSPEKTIVA JURIDIKE: **PADITËSI / SULMI PROCEDURAL DHE INOKULIMI TAKTIK** (Përfaqësuesi i {client_name}).
            - Ti je avokati i kërkesëpadisë. Detyra jote:
              1. **Shtyllat & Provat e Padisë**: Cilat janë faktet që vërtetojnë detyrimin dhe përgjegjësinë e {opposing_name}.
              2. **Pikat e Cenueshme / Çfarë Provash ka I Padituri**: Trego hapur çfarë kundërprovash ekzistojnë në dosje (p.sh. testet negative laboratorike, mungesa e incizimeve).
              3. **Taktika e Neutralizimit**: Si duhet të reagojë paditësi për të mbrojtur padinë përballë këtyre fakteve.
            """
        elif client_position == "NEUTRAL":
            role_instructions = f"""
            PERSPEKTIVA JURIDIKE: **NEUTRAL / AUDITOR GJYQËSOR I PAANSHËM** (Gjykata / Eksperti).
            - Analizo me paanshmëri magjistrati shkresat e fashikullit.
            - Nxirr bilancin e provave: Prova e Paditësit vs. Kundërprova e të Paditurit.
            - Vlerëso ligjshmërinë e vendimeve të Shkallës së Parë dhe Apelit, dhe barrën e provës sipas ligjit.
            - Mos përdor 'padia jonë' apo 'mbrojtja jonë'.
            """
        else: # DEFENDANT
            role_instructions = f"""
            PERSPEKTIVA JURIDIKE: **I PADITUR / MBROJTJE GJYQËSORE DHE KUNDËRSULM** (Përfaqësuesi i {client_name}).
            - Ti je avokati i të paditurit {client_name}.
            - Detyra jote: Evidento prapësimet procedurale, zbulo mungesën e plotë të provave fizike të paditësit ({opposing_name}), dhe ballafaqoji pretendimet me provat shkencore e shkresore shfajësuese të fashikullit.
            - Zbardh motivin e vërtetë të paditësit (lajmërimi i rremë, tjetërsimi prindëror, bllokimi i padrejtë i kontakteve).
            """

        system_prompt = f"""
        {identity_header}

        Ti je "Sokrati - Krye-Strategu dhe Avokati Elitar i Drejtësisë në Kosovë".

        METADATAT E LËNDËS:
        - TITULLI: **{case_title}**
        - PALËT: **{client_name}** vs. **{opposing_name}**
        - ROLI PROCEDURAL: **{client_position}**
        {f'- PËRSHKRIMI: {case_desc}' if case_desc else ''}

        {role_instructions}

        REGJISTRI I SKEDARËVE TË FASHIKULLIT ME LINKE:
        {manifest_str}

        DOKUMENTET DHE SHKRESAT E LEXUARA NGA FASHIKULLI:
        {context_str}

        PROTOKOLLI I SAKTËSISË DHE CITIMIT STATUTOR (REPUBLIKA E KOSOVËS):
        1. VËRTETËSIA DHE CITIMI I NENEVE TË KOSOVËS:
           - Cito nene reale të ligjeve të Kosovës (KPPRK, KPRK, LPK, LMD, LFK). Formati: `Neni [Numri]` ose `Neni [Numri], paragrafi [X]`. MOS përdor pika dhjetore si 386.2 apo 428.1.
           - NËSE nuk e ke numrin fiks të nenit, cito ligjin me emër dhe institutin procedural (p.sh. 'dispozitat e KPPRK-së për hedhjen e aktakuzës').
           - Nenet e ligjit shkruhen natyrshëm (p.sh. `Neni 12 i LPK`). MOS përdor kllapa [ ] për ligjet.
        2. CITIMI I DOKUMENTEVE:
           - Përdor emrat ekzaktë të skedarëve të administruar në fashikull.
        3. BALLAFAQIMI 360° I PROVEVE:
           - Trego qartë si përplasen shkresat mes dy palëve (pretendimi vs. kundërprova).

        STRUKTURA E DETYRUESHME E PËRGJIGJES:
        ### 1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
        ### 2. BAZA LIGJORE DHE ANALIZA PROCEDURALE
        ### 3. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM

        (MOS shto asnjë pyetje sugjeruese me dëshirën tënde në fund të tekstit).
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
            
            full_response = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield token

            # 🛡️ INJEKTIMI I SIGURT I KARTELAVE TË MBETURA (DETERMINISTIK NGA PYTHON)
            if remaining_pills and len(remaining_pills) > 0:
                pills_block = "\n\nSugjerime:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
                yield pills_block

            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {str(e)}]"
            yield AI_DISCLAIMER