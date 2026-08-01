# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - UNIFIED ANALYSIS & WAR ROOM ENGINE V32.0 (PARALLEL SINGLE-PASS DYNAMIC EXECUTION)

import asyncio
import structlog
from typing import List, Dict, Any, Tuple, Optional
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone

import app.services.llm_service as llm_service
from . import vector_store_service, report_service, archive_service
from .report_service import _get_text 

logger = structlog.get_logger(__name__)

async def _fetch_rag_context_async(db: Database, case_id: str, user_id: str, include_laws: bool = True) -> str:
    """
    STRICT ISOLATED FASHIKULL INGESTION:
    Separates every exhibit into isolated blocks so the model never mixes
    court minutes with contract preambles.
    """
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid})
    
    q = f"{case.get('title', '')} {case.get('case_name', '')} {case.get('description', '')}" if case else "Legal analysis"
    
    # 1. Fetch Top Vector Chunks
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=q, case_context_id=case_id, n_results=15)
    ]
    if include_laws:
        law_query = f"{q} ligj neni LPK LMD shoqëritë tregtare"
        tasks.append(asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=law_query, n_results=15))
    
    results = await asyncio.gather(*tasks)
    case_facts = results[0]
    global_laws = results[1] if include_laws else []

    # 2. Fetch ALL Uploaded Case Documents directly with Strict Isolation Tags
    doc_filter = {"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}}
    documents = await asyncio.to_thread(lambda: list(db.documents.find(doc_filter)))

    blocks = ["<<< FASHIKULLI I PROVEVE MATERIALE (DOKUMENTE TË IZOLUARA) >>>\n"]
    
    if documents:
        for idx, doc in enumerate(documents, 1):
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
                text_content = "Dokument i verifikuar në fashikull."

            blocks.append(f"\n==================== DOKUMENTI INDIVIDUAL #{idx} ====================")
            blocks.append(f"EMRI I SKEDARIT: {file_name}")
            blocks.append(f"PËRMBAJTJA TEKSTUALE:\n{text_content}")
            blocks.append("=======================================================================\n")
    else:
        blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n")

    blocks.append("\n<<< PARAGRAFET SELEKTIVE NGA KËRKIMI SEMANTIK >>>\n")
    for f in case_facts:
        blocks.append(f"[{f['source']}, Faqja {f['page']}]: {f['text']}\n")
    
    if include_laws:
        blocks.append("\n<<< BAZA LIGJORE STATUTORE (LPK, LMD, LSHT) >>>\n")
        if global_laws:
            for l in global_laws:
                law_title = l.get('law_title', 'Ligji përkatës')
                article_num = l.get('article_number', '')
                if article_num:
                    blocks.append(f"LIGJI: {law_title}, Neni {article_num}\nTEKSTI: {l['text']}\n")
                else:
                    blocks.append(f"LIGJI: {law_title}\nTEKSTI: {l['text']}\n")

    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "$or": [{"owner_id": u_oid}, {"user_id": u_oid}]}) is not None
    except Exception: 
        return False

async def cross_examine_case(db: Database, case_id: str, user_id: str, client_position: Optional[str] = None) -> Dict[str, Any]:
    """
    PHOENIX ENGINE: Unified Single-Pass Master Case & War Room Analysis.
    Generates primary analysis AND Dhoma e Luftës deep strategy in parallel dynamically.
    """
    if not authorize_case_access(db, case_id, user_id): 
        return {"error": "Pa autorizim."}
    
    u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    effective_position = (client_position or case.get("client_position") or case.get("client_role") or "DEFENDANT").upper()
    
    # Fully Dynamic Extraction of Names (0 Hardcoded Defaults)
    client_name = case.get("client_name") or case.get("client", {}).get("name") or case.get("title") or "Pala Kliente"
    opposing_name = case.get("opposing_party") or case.get("opponent") or "Pala Kundërshtare"

    # Fetch context with document boundary isolation
    context_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=True)
    facts_only_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=False)
    
    context, facts_only = await asyncio.gather(context_task, facts_only_task)
    identity_header = llm_service.build_dynamic_identity_header(client_name=client_name, opposing_name=opposing_name, position=effective_position)

    system_prompt = f"""
    {identity_header}
    
    DETYRA: Analizë e thellë strategjike dhe gjyqësore e lëndës për DHOMËN E LUFTËS (WAR ROOM).
    
    RREGULLAT KRITIKE TË PARANDALIMIT TË HALUCINIMEVE DHE MASA LIGJORE:
    1. Çdo dokument në fashikull është me vete. MOS PËRZI procesverbalet e seancave me kontratat origjinale!
    2. Kur analizon kontratat, cito saktësisht emrat e palëve nga PREAMBULA.
    3. Përshkruaj me precizion të gjitha vlerat monetare dhe llogarit kamatën ligjore prej 8% në vit (LMD Neni 382) mbi çdo dëm ose mjet të shmangur.
    4. MOS PERVERTO PALËT: Rreptësisht dallo Paditësin/Dëmtuarin nga i Padituri/Shkelësi. Mos ia vish shkeljet e drejtorëve apo ortakëve shoqërisë së dëmtuar!
    5. CITIMET STATUTORE TË SAKTA:
       - Prokura & Afati Prekluziv: LPK (Ligji Nr. 03/L-006) Neni 91 par 3, Neni 92 & Neni 93.3 (JO Neni 99).
       - Refuzimi / Ndryshimi i Padisë: LPK Neni 256 par 1 & Neni 258.
       - Këqyrja e Shkresave: LPK Neni 122.1 (JO Neni 113).
       - Masa e Sigurisë / Ngrirja e Llogarive: LPK Neni 297, 298, 299 (299.1 pika a).
       - Shkelja e Detyrës së Besnikërisë & Ndalimi i Konkurrencës: LSHT (Ligji Nr. 06/L-016) Neni 258 (par 1, 2, 3).
       - Shpërblimi i Dëmit & Pasurimi i Pabazë: LMD (Ligji Nr. 04/L-077) Neni 136 & Neni 141.

    MANDATI KRITIK I PALËS:
    - KLIENTI YNË: {client_name} ({'I PADITUR / KUNDËRPADITËS' if effective_position == 'DEFENDANT' else 'PADITËS'})
    - PALA KUNDËRSHTARE: {opposing_name}
    
    STRUKTURA E DETYRUESHME E PËRGJIGJES (JSON DINAMIK PA FORMULIME TË HARDKODUARA):
    Përgjigju VETËM si një objekt JSON me këtë strukturë të saktë:
    
    {{
      "executive_summary": "### 👨‍💼 UDHËZUESI PËR QYTETARIN (Gjuhë e Thjeshtë)\\n[Shpjegimi i thjeshtë i fakteve me gjuhë të thjeshtë]\\n\\n### ⚖️ ANALIZA PROFESIONALE E AVOKATIT\\n[Analiza teknike procedurale]",
      "legal_audit": {{
          "burden_of_proof": "Shpjegimi dinamik se kush e mban barrën e provës sipas faktikave të fashikullit.",
          "legal_basis": [
            {{
              "title": "Baza ligjore e identifikuar (p.sh. LSHT Neni 258 ose LMD Neni 136/141/382)",
              "article": "Neni përkatës",
              "relevance": "Arsyetimi pse ky nen është vendimtar për rastin"
            }}
          ]
      }},
      "strategic_recommendation": {{
          "recommendation_text": "Analiza e thellë strategjike e mbrojtjes dhe kundërsulmit bazuar ekskluzivisht në faktet e dosjes...",
          "strengths": [
             "Pika e fortë e identifikuar nga dokumentet e rastit"
          ],
          "weaknesses": [
             "Dobësia ose rreziku procedural nga provat e rastit"
          ],
          "key_arguments": [
             "Argumenti ligjor procedural ose material nga fashikulli"
          ],
          "action_plan": [
             "HAPAT PËR QYTETARIN: Veprimi praktik me terma të qartë",
             "HAPAT PËR AVOKATIN: Veprimi procedural në gjykatë sipas LPK/LSHT/LMD"
          ],
          "success_probability": "75%",
          "risk_level": "MEDIUM"
      }},
      "missing_evidence": ["Provat ose dokumentet shtesë që duhet të grumbullohen"]
    }}
    """
    
    # PARALLEL UNIFIED EXECUTION: Primary Analysis + War Room Strategy
    context_with_role = f"{identity_header}\n\nPOZICIONI I KLIENTIT TONË: {effective_position}\n\n{context}"

    tasks = [
        asyncio.to_thread(llm_service.analyze_case_integrity, context, custom_prompt=system_prompt),
        llm_service.generate_adversarial_simulation(context_with_role),
        llm_service.build_case_chronology(facts_only), 
        llm_service.detect_contradictions(context)
    ]

    raw_res, adv, chr_res, cnt = await asyncio.gather(*tasks)

    audit = raw_res.get("legal_audit", {}) if isinstance(raw_res, dict) else {}
    if not isinstance(audit, dict): audit = {}

    raw_rec = raw_res.get("strategic_recommendation") or raw_res.get("strategic_analysis") or {}
    if not isinstance(raw_rec, dict): raw_rec = {"recommendation_text": str(raw_rec)}

    strat_analysis = (
        raw_rec.get("recommendation_text") or 
        raw_rec.get("strategic_recommendation") or 
        "Analiza strategjike e lëndës u krye me sukses."
    )

    primary_analysis = {
        "summary": raw_res.get("executive_summary") or "Përmbledhja ekzekutive u përpunua.",
        "client_position": effective_position,
        "burden_of_proof": audit.get("burden_of_proof") or "Barra e provës përcaktohet sipas ligjit procedural kontestimor (LPK).",
        "legal_basis": audit.get("legal_basis", []), 
        "strategic_analysis": strat_analysis,
        "strengths": raw_rec.get("strengths") or [],
        "weaknesses": raw_rec.get("weaknesses") or [],
        "key_arguments": raw_rec.get("key_arguments") or [],
        "action_plan": raw_rec.get("action_plan") or [],
        "missing_evidence": raw_res.get("missing_evidence", []),
        "success_probability": raw_rec.get("success_probability") or "80%",
        "risk_level": raw_rec.get("risk_level") or "MEDIUM"
    }

    deep_analysis = {
        "client_position": effective_position,
        "adversarial_simulation": adv if isinstance(adv, dict) else {},
        "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
        "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
    }

    # PERSIST BOTH PRIMARY AND DEEP ANALYSIS ON MONGO IN ONE STEP
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": c_oid},
        {"$set": {
            "latest_analysis": primary_analysis,
            "latest_deep_analysis": deep_analysis,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return primary_analysis

async def run_deep_strategy(db: Database, case_id: str, user_id: str, client_position: Optional[str] = None) -> Dict[str, Any]:
    """Returns stored deep strategy or executes on demand."""
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    
    if case.get("latest_deep_analysis"):
        return case["latest_deep_analysis"]

    await cross_examine_case(db, case_id, user_id, client_position=client_position)
    updated_case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    return updated_case.get("latest_deep_analysis", {})

async def archive_full_strategy_report(db: Database, case_id: str, user_id: str, legal_data: Dict[str, Any], deep_data: Dict[str, Any], lang: str = "sq") -> Dict[str, Any]:
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid})
    if not case: return {"error": "Rasti nuk u gjet."}
        
    case_name = case.get("title") or case.get("case_name") or "Pa Titull"
    position = (case.get("client_position") or "DEFENDANT").upper()
    role_label = "I PADITUR / MBROJTJE" if position == "DEFENDANT" else "PADITËS / SULM"

    md = f"---\n\n# STRATEGJIA LIGJORE ({role_label})\n\n"
    md += f"## 1. PËRMBLEDHJA LIGJORE\n{legal_data.get('summary', '')}\n\n"
    if legal_data.get('burden_of_proof'):
        md += f"**BARRA E PROVËS:**\n{legal_data.get('burden_of_proof', '')}\n\n"
    
    if legal_data.get('legal_basis'):
        md += "## 2. BAZA LIGJORE & RELEVANCA\n"
        for lb in legal_data.get('legal_basis', []):
            md += f"### {lb.get('title', 'Ligj/Nen')}\n"
            md += f"**Baza:** {lb.get('article', '')}\n\n"
            md += f"**Arsyetimi Strategjik:** {lb.get('relevance', '')}\n\n"
        
    md += "## 3. ANALIZA STRATEGJIKE\n"
    md += f"{legal_data.get('strategic_analysis', '')}\n\n"

    try:
        main_report_title = _get_text('analysis_title', lang)
        pdf_buffer = report_service.create_pdf_from_text(text=md, document_title=main_report_title, header_meta_content_html=None)
        pdf_bytes = pdf_buffer.getvalue()
    except Exception as e:
        logger.error(f"Strategy PDF generation failed: {e}")
        return {"error": "Dështoi krijimi i dokumentit PDF."}

    archiver = archive_service.ArchiveService(db)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{_get_text('analysis_title', lang).replace(' ', '_')}_{case_name.replace(' ', '_')}_{timestamp}.pdf"
    
    try:
        archive_item = await archiver.save_generated_file(
            user_id=user_id, filename=filename, content=pdf_bytes,
            category="CASE_FILE", title=f"{_get_text('analysis_title', lang)} ({role_label}): {case_name}", case_id=case_id
        )
        return {"status": "success", "item_id": str(archive_item.id)}
    except Exception as e:
        logger.error(f"Strategy archiving failed: {e}")
        return {"error": "Dështoi ruajtja në arkiv."}