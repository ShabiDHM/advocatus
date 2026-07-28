# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V32.0 (ISOLATED DOKUMENT BOUNDARIES & HIGH-PRECISION OCR INGESTION)

import os
import re
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, List, AsyncGenerator
from bson import ObjectId
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

LEGAL_DOMAINS = {
    "FAMILY": {
        "keywords": ["shkurorëzim", "divorc", "alimentacion", "kujdestari", "fëmijë", "bashkëshort", "martesë"],
        "law": "Ligji Nr. 2004/32 për Familjen e Kosovës",
        "context_note": "Fokus: Interesi më i mirë i fëmijës, barazia bashkëshortore."
    },
    "CORPORATE": {
        "keywords": ["shpk", "aksion", "biznes", "bord", "divident", "falimentim", "statut", "marrëveshje themelimi", "ortak", "partneritet"],
        "law": "Ligji Nr. 06/L-016 për Shoqëritë Tregtare",
        "context_note": "Fokus: Përgjegjësia e kufizuar, qeverisja korporative."
    },
    "OBLIGATIONS": {
        "keywords": ["kontratë", "borxh", "dëm", "kredi", "faturë", "qira", "shitblerje", "marrëveshje", "përmbushje"],
        "law": "Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve (LMD)",
        "context_note": "Fokus: Pacta sunt servanda, kompensimi i dëmit."
    },
    "PROPERTY": {
        "keywords": ["pronë", "tokë", "banesë", "kadastër", "posedim", "hipotekë", "servitut", "shpronësim"],
        "law": "Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat Tjera Sendore",
        "context_note": "Fokus: Titulli juridik, mbrojtja e posedimit."
    },
    "LABOR": {
        "keywords": ["punë", "rrogë", "pagë", "pushim", "kontratë pune", "largim nga puna", "diskriminim", "orar"],
        "law": "Ligji Nr. 03/L-212 i Punës",
        "context_note": "Fokus: Të drejtat e punëtorit, procedurat disiplinore."
    },
    "CRIMINAL": {
        "keywords": ["vepër penale", "aktakuzë", "burgim", "gjobë", "kallëzim penal", "vjedhje", "mashtrim", "lëndim", "vrasje"],
        "law": "Kodi Penal i Republikës së Kosovës (KPRK) & Kodi i Procedurës Penale (KPPK)",
        "context_note": "Fokus: Prezumimi i pafajësisë, elementet e veprës penale."
    },
    "ADMINISTRATIVE": {
        "keywords": ["vendim administrativ", "komuna", "ministria", "leje", "licencë", "inspektorat", "konflikt administrativ"],
        "law": "Ligji për Procedurën e Përgjithshme Administrative",
        "context_note": "Fokus: Ligjshmëria, proporcionaliteti."
    }
}

def detect_legal_domain(text: str) -> Dict[str, str]:
    text_lower = text.lower()
    scores = {key: 0 for key in LEGAL_DOMAINS}
    for domain, data in LEGAL_DOMAINS.items():
        for keyword in data["keywords"]:
            if keyword in text_lower:
                scores[domain] += 1
    best_match = max(scores, key=lambda k: scores[k])
    if scores[best_match] > 0:
        return LEGAL_DOMAINS[best_match]
    return {
        "law": "Legjislacioni i Aplikueshëm në Kosovë",
        "context_note": "Fokus: Zbatimi i përgjithshëm i ligjit dhe procedurës."
    }

def sanitize_unresolved_placeholders(bracket_text: str) -> str:
    pattern = r"\[([^\]]{1,100})\]"
    def replacement(match):
        placeholder_content = match.group(1).strip()
        return f"________________________ ({placeholder_content})"
    return re.sub(pattern, replacement, bracket_text)

async def stream_with_placeholder_cleaning(
    raw_generator: AsyncGenerator[str, None]
) -> AsyncGenerator[str, None]:
    buffer = ""
    in_bracket = False
    
    async for token in raw_generator:
        for char in token:
            if char == "[":
                in_bracket = True
                buffer += char
            elif char == "]":
                buffer += char
                in_bracket = False
                cleaned = sanitize_unresolved_placeholders(buffer)
                yield cleaned
                buffer = ""
            elif in_bracket:
                buffer += char
                if len(buffer) > 120:
                    yield buffer
                    buffer = ""
                    in_bracket = False
            else:
                yield char
                
    if buffer:
        yield buffer

async def stream_draft_generator(
    db: Database, 
    user_id: str, 
    case_id: Optional[str], 
    draft_type: str, 
    user_prompt: str
) -> AsyncGenerator[str, None]:
    
    logger.info("Drafting initiated", user=user_id, type=draft_type)
    
    client_position = "DEFENDANT"
    db_documents = []
    
    if case_id and db is not None:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case_doc = db.cases.find_one({"_id": c_oid})
            if case_doc and case_doc.get("client_position"):
                client_position = str(case_doc["client_position"]).upper()

            # Direct Mongo Documents Fetch
            doc_cursor = db.documents.find({"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}})
            db_documents = list(doc_cursor)
        except Exception as ex:
            logger.warning(f"Could not read case or documents for drafting: {ex}")

    if client_position == "PLAINTIFF":
        role_mandate = """
        MANDATI ZYRTAR I HARTIMIT: SULM / PADITËS
        - Harto këtë shkresë me ton rigorozisht sulmues dhe profesional për Paditësin.
        - Vërteto bazën e kërkesëpadisë, detyrimin e palës tjetër, dëmin e shkaktuar dhe forcat e kërkesës sonë.
        """
    elif client_position == "NEUTRAL":
        role_mandate = """
        MANDATI ZYRTAR I HARTIMIT: OBJEKTIV / NEUTRAL
        - Harto këtë shkresë me ton të paanshëm, objektiv dhe neutral.
        """
    else:
        role_mandate = """
        MANDATI ZYRTAR I HARTIMIT: MBROJTJE / I PADITUR
        - Harto këtë shkresë me ton rigorozisht mbrojtës dhe prapësues për të Paditurin.
        - Shfrytëzo gabimet procedurale, parashkrimin e afateve, mungesën e provave dhe kërko rrëzimin ose hedhjen poshtë të padisë.
        """

    domain_context = detect_legal_domain(user_prompt)
    detected_law = domain_context["law"]
    context_note = domain_context["context_note"]

    search_query = f"{user_prompt} {detected_law} neni dispozita"

    try:
        tasks = [
            asyncio.to_thread(
                vector_store_service.query_case_knowledge_base, 
                user_id=user_id, 
                query_text=user_prompt, 
                n_results=8, 
                case_context_id=case_id
            ),
            asyncio.to_thread(
                vector_store_service.query_global_knowledge_base, 
                query_text=search_query, 
                n_results=10
            )
        ]
        results = await asyncio.gather(*tasks)
        case_facts_list = results[0] or []
        legal_articles_list = results[1] or []
    except Exception as e:
        logger.error(f"Vector Store Retrieval Failed: {e}")
        case_facts_list = []
        legal_articles_list = []

    # Build Strict Document Boundary Block for Case Exhibits
    exhibits_block = ""
    if db_documents:
        for idx, doc in enumerate(db_documents, 1):
            file_name = doc.get("file_name") or doc.get("title") or "Dokument"
            raw_t = doc.get("extracted_text") or ""
            summ = doc.get("summary") or ""
            if summ == "Sinteza...": summ = ""

            text_content = f"PËRMBLEDHJE: {summ}\nTEKSTI EKSKLUSIV:\n{raw_t[:3500]}" if raw_t else summ
            exhibits_block += f"\n==================== DOKUMENTI INDIVIDUAL #{idx} ====================\n"
            exhibits_block += f"EMRI I SKEDARIT: {file_name}\n"
            exhibits_block += f"PËRMBAJTJA TEKSTUALE:\n{text_content}\n"
            exhibits_block += f"=======================================================================\n"

    vector_facts_block = "\n".join([f"- {f.get('text', '')}" for f in case_facts_list]) if case_facts_list else ""
    full_facts_context = f"{exhibits_block}\n\n[PARAGRAFET TË TJERA NGA KËRKIMI SEMANTIK]\n{vector_facts_block}"

    if legal_articles_list:
        laws_lines = []
        for l in legal_articles_list:
            law_title = l.get('law_title', 'Ligji i panjohur')
            article_num = l.get('article_number')
            text = l.get('text', '')
            laws_lines.append(f"- {law_title}, Neni {article_num}:\n  {text}" if article_num else f"- {law_title}:\n  {text}")
        laws_block = "\n".join(laws_lines)
    else:
        laws_block = "Nuk u gjetën nene specifike në bazën ligjore."

    system_prompt = f"""
ROLI: Avokat i Licencuar në Republikën e Kosovës.

{role_mandate}

UDHËZIME TË RREPTA JURIDIKE DHE AKURATESE TË PALËVE:
1. Përdor dhe plotëso saktësisht strukturën e shabllonit të zgjedhur.
2. RREGULLI KRITIK I KONTRATAVE: Cito me saktësi absolute palët nënshkruese të dhëna në [FAKTET DHE DOKUMENTET E RASTIT] (p.sh. INTEGRATION GmbH, Dr. Rainer Gerke, GIZ Kosovo, €51,500 EUR, TEB Bank).
3. Mos përziej procesverbalet e seancave gjyqësore me preambulën e kontratave origjinale!
4. CITO VETËM LIGJET E LISTUARA NË [MATERIALI LIGJOR NDIHMËS]. Përdor titujt e plotë zyrtarë me numra ligjesh (p.sh. Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve).

Ofroni draftin direkt në format markdown të strukturuar sipas shabllonit, pa asnjë hyrje ose koment shtesë.

[KONTEKSTI LIGJOR I DETEKTUAR]
Ligji primar i identifikuar: {detected_law}
Udhëzim: {context_note}

[MATERIALI LIGJOR NDIHMËS]
{laws_block}

[FAKTET DHE DOKUMENTET E RASTIT (ME BOUNDARIES TË TË IZOLUARA)]
{full_facts_context}
"""

    raw_stream = llm_service.stream_text_async(system_prompt, user_prompt, temp=llm_service.TEMP_DRAFTING)
    
    full_content = ""
    try:
        async for clean_char in stream_with_placeholder_cleaning(raw_stream):
            full_content += clean_char
            yield clean_char

        if full_content.strip() and case_id:
            asyncio.create_task(save_draft_result(db, user_id, case_id, draft_type, full_content))

    except Exception as e:
        logger.error(f"Streaming draft generation failed: {e}")
        yield f"\n\n[GABIM SISTEMI]: {str(e)}"

async def save_draft_result(db: Database, user_id: str, case_id: str, draft_type: str, content: str):
    try:
        await asyncio.to_thread(
            db.drafting_results.insert_one, 
            {
                "case_id": case_id, 
                "user_id": user_id, 
                "draft_type": draft_type, 
                "result_text": content, 
                "status": "COMPLETED", 
                "created_at": datetime.now(timezone.utc)
            }
        )
    except Exception as e:
        logger.error(f"Failed to save draft result: {e}")