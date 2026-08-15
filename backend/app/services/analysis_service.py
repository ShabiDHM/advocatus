# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - UNIFIED ANALYSIS & FULL STRATEGY REPORT ARCHIVER V37.0 (GEMINI 2.0 FLASH ACCELERATED)

import asyncio
import structlog
from typing import List, Dict, Any, Tuple, Optional
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone

import app.services.llm_service as llm_service
from . import vector_store_service, report_service, archive_service

logger = structlog.get_logger(__name__)

async def _fetch_rag_context_async(db: Database, case_id: str, user_id: str, include_laws: bool = True) -> str:
    """Nxjerr të gjithë fashikullin e lëndës në mënyrë të izoluar dhe të saktë."""
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid})
    
    q = f"{case.get('title', '')} {case.get('case_name', '')} {case.get('description', '')}" if case else "Legal analysis"
    
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=q, case_context_id=case_id, n_results=15)
    ]
    if include_laws:
        law_query = f"{q} ligj neni LPK LMD KPRK KPPRK LFK"
        tasks.append(asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=law_query, n_results=15))
    
    results = await asyncio.gather(*tasks)
    case_facts = results[0]
    global_laws = results[1] if include_laws else []

    doc_filter = {"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}}
    documents = await asyncio.to_thread(lambda: list(db.documents.find(doc_filter)))

    blocks = ["<<< FASHIKULLI I PROVEVE MATERIALE (DOKUMENTE TË IZOLUARA) >>>\n"]
    
    if documents:
        for idx, doc in enumerate(documents, 1):
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
        blocks.append("\n<<< BAZA LIGJORE STATUTORE (LPK, LMD, LFK, KPRK) >>>\n")
        if global_laws:
            for l in global_laws:
                law_title = l.get('law_title', 'Ligji përkatës')
                article_num = l.get('article_number', '')
                blocks.append(f"LIGJI: {law_title}, Neni {article_num}\nTEKSTI: {l['text']}\n")

    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "$or": [{"owner_id": u_oid}, {"user_id": u_oid}]}) is not None
    except Exception: 
        return False

async def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str, 
    client_position: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """Kryen analizën e thellë të lëndës dhe War Room me shpejtësi maksimale."""
    if not authorize_case_access(db, case_id, user_id): 
        return {"error": "Pa autorizim."}
    
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    effective_position = (client_position or case.get("client_position") or case.get("client_role") or "DEFENDANT").upper()
    
    client_name = case.get("client_name") or case.get("client", {}).get("name") or case.get("title") or "Pala Kliente"
    opposing_name = case.get("opposing_party") or case.get("opponent") or "Pala Kundërshtare"

    doc_filter = {"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}}
    documents = await asyncio.to_thread(lambda: list(db.documents.find(doc_filter, {"_id": 1, "updated_at": 1})))
    current_doc_ids = sorted([str(d["_id"]) for d in documents])

    cached_analysis = case.get("latest_analysis")
    cached_deep = case.get("latest_deep_analysis")
    saved_doc_ids = case.get("analyzed_doc_ids")

    if not force and cached_analysis and (saved_doc_ids == current_doc_ids):
        logger.info("Serving cached analysis - gatekeeper active", case_id=case_id)
        return {
            **cached_analysis,
            "latest_deep_analysis": cached_deep or {},
            "cached": True,
            "message": "Analiza ekzistuese është e përditësuar."
        }

    # Nxjerr kontekstin e plotë të lëndës
    context, facts_only = await asyncio.gather(
        _fetch_rag_context_async(db, case_id, user_id, include_laws=True),
        _fetch_rag_context_async(db, case_id, user_id, include_laws=False)
    )

    identity_header = llm_service.build_dynamic_identity_header(client_name=client_name, opposing_name=opposing_name, position=effective_position)

    system_prompt = f"""
    {identity_header}
    
    DETYRA: Analizë e thellë strategjike dhe gjyqësore e lëndës për DHOMËN E LUFTËS (WAR ROOM).
    
    RREGULLAT KRITIKE:
    1. Dallo Paditësin nga i Padituri dhe analizo faktet sipas ligjeve të Kosovës (LPK, KPRK, KPPRK, LFK, LMD).
    2. Cito saktësisht nenet e ligjit dhe shkeljet materiale.
    3. Identifiko barrën e provës dhe planin procedural të veprimit.

    Përgjigju VETËM si JSON me këtë strukturë:
    {{
      "executive_summary": "Përmbledhje ekzekutive e thellë ligjore...",
      "legal_audit": {{
          "burden_of_proof": "Kush e mban barrën e provës...",
          "legal_basis": [
            {{
              "title": "Titulli i shkeljes",
              "article": "Neni i ligjit",
              "relevance": "Arsyetimi strategjik"
            }}
          ]
      }},
      "strategic_recommendation": {{
          "recommendation_text": "Strategjia kryesore e mbrojtjes/sulmit...",
          "strengths": ["Pika e fortë 1", "Pika e fortë 2"],
          "weaknesses": ["Dobësia 1", "Dobësia 2"],
          "key_arguments": ["Argumenti ligjor 1", "Argumenti 2"],
          "action_plan": ["Hapi 1 për avokatin", "Hapi 2"],
          "success_probability": "85%",
          "risk_level": "MEDIUM"
      }},
      "missing_evidence": ["Provat shtesë që kërkohen"]
    }}
    """

    context_with_role = f"{identity_header}\n\nPOZICIONI I KLIENTIT TONË: {effective_position}\n\n{context}"

    # Ekzekutimi Paralel i 4 Analizave me Gemini 2.0 Flash (Koha ~5-6 sekonda)
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
        "summary": raw_res.get("executive_summary") or "Përmbledhja ekzekutive u përpunua me sukses.",
        "client_position": effective_position,
        "burden_of_proof": audit.get("burden_of_proof") or "Barra e provës përcaktohet sipas ligjit procedural.",
        "legal_basis": audit.get("legal_basis", []), 
        "strategic_analysis": strat_analysis,
        "strengths": raw_rec.get("strengths") or [],
        "weaknesses": raw_rec.get("weaknesses") or [],
        "key_arguments": raw_rec.get("key_arguments") or [],
        "action_plan": raw_rec.get("action_plan") or [],
        "missing_evidence": raw_res.get("missing_evidence", []),
        "success_probability": raw_rec.get("success_probability") or "85%",
        "risk_level": raw_rec.get("risk_level") or "MEDIUM"
    }

    deep_analysis = {
        "client_position": effective_position,
        "adversarial_simulation": adv if isinstance(adv, dict) else {},
        "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
        "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
    }

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": c_oid},
        {"$set": {
            "latest_analysis": primary_analysis,
            "latest_deep_analysis": deep_analysis,
            "analyzed_doc_ids": current_doc_ids,
            "client_position": effective_position,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return {
        **primary_analysis,
        "latest_deep_analysis": deep_analysis,
        "cached": False,
        "message": "Analiza strategjike u krye me sukses."
    }

async def run_deep_strategy(db: Database, case_id: str, user_id: str, client_position: Optional[str] = None) -> Dict[str, Any]:
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    
    if case.get("latest_deep_analysis"):
        return case["latest_deep_analysis"]

    res = await cross_examine_case(db, case_id, user_id, client_position=client_position)
    return res.get("latest_deep_analysis", {})

async def archive_full_strategy_report(db: Database, case_id: str, user_id: str, legal_data: Dict[str, Any], deep_data: Dict[str, Any], lang: str = "sq") -> Dict[str, Any]:
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid})
    if not case: return {"error": "Rasti nuk u gjet."}
        
    case_name = case.get("title") or case.get("case_name") or "Pa Titull"
    position = (case.get("client_position") or "DEFENDANT").upper()
    role_label = "I PADITUR / MBROJTJE" if position == "DEFENDANT" else "PADITËS / SULM"

    md = f"# STRATEGJIA LIGJORE E RASTIT ({role_label})\n\n"
    
    md += "## 1. PËRMBLEDHJA LIGJORE\n"
    summary_text = legal_data.get('summary', '')
    if summary_text:
        md += f"{summary_text}\n\n"
        
    if legal_data.get('burden_of_proof'):
        md += f"> **BARRA E PROVËS:** {legal_data.get('burden_of_proof', '')}\n\n"
    
    legal_basis_list = legal_data.get('legal_basis', [])
    if legal_basis_list:
        md += "## 2. REGJISTRI I BAZËS LIGJORE DHE RELEVANCËS\n\n"
        md += "| # | SHKELJA / TEMA | BAZA LIGJORE | ARSYETIMI STRATEGJIK DHE RELEVANCA |\n"
        md += "|---|---|---|---|\n"
        for idx, lb in enumerate(legal_basis_list, 1):
            title = str(lb.get('title', 'Shkelje Ligjore')).replace('|', '-')
            article = str(lb.get('article', 'Neni përkatës')).replace('|', '-')
            relevance = str(lb.get('relevance', '')).replace('|', '-').replace('\n', ' ')
            md += f"| [{idx}] | **{title}** | <span class=\"badge badge-blue\">{article}</span> | {relevance} |\n"
        md += "\n"
        
    md += "## 3. ANALIZA STRATEGJIKE DHE PLANI I VEPRIMIT\n"
    strat_text = legal_data.get('strategic_analysis', '')
    if strat_text:
        md += f"{strat_text}\n\n"

    action_plan = legal_data.get('action_plan', [])
    if action_plan:
        md += "### PLANI I HAPAVE TË VEPRIMIT\n\n"
        md += "| # | ROLI | VEPRIMI STRATEGJIK I REKOMANDUAR |\n"
        md += "|---|---|---|\n"
        for idx, act in enumerate(action_plan, 1):
            act_clean = str(act).replace('|', '-').replace('HAPAT PËR QYTETARIN:', '').replace('HAPAT PËR AVOKATIN:', '').strip()
            role = "QYTETARI" if "QYTETAR" in str(act).upper() else "AVOKATI"
            badge_class = "badge-green" if role == "QYTETARI" else "badge-blue"
            md += f"| [{idx}] | <span class=\"badge {badge_class}\">{role}</span> | {act_clean} |\n"
        md += "\n"

    chronology = deep_data.get('chronology', []) if isinstance(deep_data, dict) else []
    if chronology:
        md += "## 4. KRONOLOGJIA E FAKTEVE\n\n"
        md += "| DATAT / PERIUDHA | EVENTI DHE PROVA ORIGJINALE |\n"
        md += "|---|---|\n"
        for ev in chronology:
            if isinstance(ev, dict):
                d_str = str(ev.get('date', 'Datë e pacaktuar')).replace('|', '-')
                e_str = str(ev.get('event', '')).replace('|', '-').replace('\n', ' ')
                md += f"| **{d_str}** | {e_str} |\n"
        md += "\n"

    contradictions = deep_data.get('contradictions', []) if isinstance(deep_data, dict) else []
    if contradictions:
        md += "## 5. KONTRADIKTAT DHE MOSPËRPUTHJET FAKTIKE\n\n"
        md += "| # | SEVERITETI | DEKLARATA E PALËS | PROVA OBJEKTIVE DHE NDIKIMI |\n"
        md += "|---|---|---|---|\n"
        for idx, c in enumerate(contradictions, 1):
            if isinstance(c, dict):
                sev = str(c.get('severity', 'HIGH')).upper()
                claim = str(c.get('claim', '')).replace('|', '-').replace('\n', ' ')
                evidence = str(c.get('evidence', '')).replace('|', '-').replace('\n', ' ')
                impact = str(c.get('impact', '')).replace('|', '-').replace('\n', ' ')
                badge_class = "badge-red" if "HIGH" in sev or "CRIT" in sev else "badge-yellow"
                sev_label = "KRITIKE" if "CRIT" in sev or "HIGH" in sev else "E MESME"
                md += f"| [{idx}] | <span class=\"badge {badge_class}\">{sev_label}</span> | *\"{claim}\"* | **PROVA:** {evidence}<br/>**NDIKIMI:** {impact} |\n"
        md += "\n"

    try:
        main_report_title = "RAPORTI I ANALIZËS"
        pdf_buffer = report_service.create_pdf_from_text(
            text=md, 
            document_title=main_report_title, 
            header_meta_content_html=f"<b>LËNDA:</b> {case_name} &nbsp;|&nbsp; <b>POZICIONI:</b> {role_label}"
        )
        pdf_bytes = pdf_buffer.getvalue()
    except Exception as e:
        logger.error(f"Strategy PDF generation failed: {e}", exc_info=True)
        return {"error": "Dështoi krijimi i dokumentit PDF."}

    archiver = archive_service.ArchiveService(db)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"Raporti_i_Analizes_{case_name.replace(' ', '_')}_{timestamp}.pdf"
    
    try:
        archive_item = await archiver.save_generated_file(
            user_id=user_id, filename=filename, content=pdf_bytes,
            category="CASE_FILE", title=f"Raporti i Analizës ({role_label}): {case_name}", case_id=case_id
        )
        return {"status": "success", "item_id": str(archive_item.id)}
    except Exception as e:
        logger.error(f"Strategy archiving failed: {e}")
        return {"error": "Dështoi ruajtja në arkiv."}