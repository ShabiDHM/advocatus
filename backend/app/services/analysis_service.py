# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V27.0 (DYNAMIC DYNAMIC IDENTITY HEADER INVOCATION FIX)

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
    CONSOLIDATED FASHIKULL INGESTION (SQ + EN + DE)
    Combines top semantic vector search with complete document summaries of ALL uploaded exhibits.
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

    # 2. Fetch ALL Uploaded Case Documents directly (Consolidated Fashikull)
    doc_filter = {"$or": [{"case_id": case_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}}
    documents = await asyncio.to_thread(lambda: list(db.documents.find(doc_filter)))

    blocks = ["=== FASHIKULLI I PLOTË I DOKUMENTEVE TË LËNDËS (PROVAT MATERIALE) ==="]
    
    if documents:
        for idx, doc in enumerate(documents, 1):
            file_name = doc.get("file_name") or doc.get("title") or "Dokument"
            text_content = (doc.get("summary") or doc.get("extracted_text") or "")[:2000]
            blocks.append(f"EKSPONATI {idx}: {file_name}\nPËRMBAJTJA / PROVA: {text_content}\n")
    else:
        blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.")

    blocks.append("\n=== VEKTORËT E KËRKIMIT SEMANTIK ===")
    for f in case_facts:
        blocks.append(f"DOKUMENTI: {f['source']} (Faqja {f['page']})\nTEKSTI: {f['text']}\n")
    
    if include_laws:
        blocks.append("\n=== BAZA LIGJORE STATUTORE (LPK, LMD, LSHT) ===")
        if global_laws:
            for l in global_laws:
                law_title = l.get('law_title', 'Ligji përkatës')
                article_num = l.get('article_number', '')
                if article_num:
                    blocks.append(f"LIGJI: {law_title}, Neni {article_num}\nTEKSTI: {l['text']}\n")
                else:
                    blocks.append(f"LIGJI: {law_title}\nTEKSTI: {l['text']}\n")
        else:
            blocks.append("Nuk u gjetën dispozita statutore dytësore.")
            
    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "$or": [{"owner_id": u_oid}, {"user_id": u_oid}]}) is not None
    except Exception: 
        return False

def build_and_populate_graph(db: Database, case_id: str, user_id: str) -> bool:
    """Synchronously extracts entities from all case documents and populates the Graph DB."""
    if not authorize_case_access(db, case_id, user_id):
        logger.warning("Unauthorized graph build attempt", case_id=case_id, user_id=user_id)
        return False
    try:
        from .document_service import get_document_content_by_key
        from .graph_service import graph_service
        
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        doc_cursor = db.documents.find({"$or": [{"case_id": case_id}, {"case_id": c_oid}]})
        docs = list(doc_cursor)
        if not docs: return False

        for doc in docs:
            text_key = doc.get("processed_text_storage_key")
            if not text_key: continue
            content = get_document_content_by_key(text_key)
            if not content: continue
            graph_data = llm_service.extract_graph_data(content)
            entities = graph_data.get("nodes", [])
            relations = graph_data.get("edges", [])
            if not entities: continue
            graph_service.ingest_entities_and_relations(
                case_id=str(case_id),
                document_id=str(doc["_id"]),
                doc_name=doc.get("file_name", "Unknown"),
                entities=entities,
                relations=relations
            )
        return True
    except Exception as e:
        logger.error(f"Failed to build graph: {e}")
        return False

async def cross_examine_case(db: Database, case_id: str, user_id: str, client_position: Optional[str] = None) -> Dict[str, Any]:
    """
    PHOENIX: High-IQ Stage-Reasoning Analysis Engine.
    Executes deep cross-examination with locked client role and full fashikull ingestion.
    """
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    user = await asyncio.to_thread(db.users.find_one, {"_id": u_oid}) or {}
    profile = await asyncio.to_thread(db.business_profiles.find_one, {"$or": [{"user_id": u_oid}, {"user_id": str(user_id)}]}) or {}
    
    effective_position = (client_position or case.get("client_position") or "DEFENDANT").upper()
    client_name = case.get("client_name") or case.get("client", {}).get("name") or "Shaban Bala"
    opposing_name = case.get("opposing_party") or "Getting Competent ShPK / Raimier Gerger"

    context = await _fetch_rag_context_async(db, case_id, user_id, include_laws=True)
    identity_header = llm_service.build_dynamic_identity_header(client_name=client_name, opposing_name=opposing_name, position=effective_position)

    system_prompt = f"""
    {identity_header}
    
    DETYRA: Analizë e thellë strategjike dhe gjyqësore e lëndës.
    
    MANDATI KRITIK I PALËS:
    - KLIENTI YNË: {client_name} ({'I PADITUR / KUNDËRPADITËS' if effective_position == 'DEFENDANT' else 'PADITËS'})
    - PALA KUNDËRSHTARE: {opposing_name}
    
    STRUKTURA E MANDATUAR E PËRMBLEDHJES (EXECUTIVE SUMMARY):
    Seksioni 'executive_summary' DUHET të ndahet në dy pjesë të qarta:
    1. '### 👨‍💼 UDHËZUESI PËR QYTETARIN (Gjuhë e Thjeshtë)'
       - Shpjegoni me fjalë të thjeshta dhe të qarta se çfarë po ndodh me këtë rast.
       - Identifikoni veprimet e paautorizuara të palës kundërshtare dhe hapat e mbrojtjes/sulmit.
    2. '### ⚖️ ANALIZA PROFESIONALE E AVOKATIT'
       - Goditja Procedurale: Kontrollo për LPK Nenet 98/99 (Mungesa e prokurës, afatet prekluzive 7-ditore).
       - Baza Materiale: LSHT Neni 258/259 (Detyrimi i Besnikërisë & Ndalimi i Konkurrencës), LMD Neni 180.
       - Provat Zyrtare: Cito raportet e ATK-së, pasqyrat e bankës TEB/NLB, dhe certifikatat e ARBK-së.

    Përgjigju VETËM në formatin e strukturuar JSON ashtu siç kërkohet.
    """
    
    try:
        raw_res = await asyncio.to_thread(llm_service.analyze_case_integrity, context, custom_prompt=system_prompt)
        
        audit = raw_res.get("legal_audit", {})
        rec = raw_res.get("strategic_recommendation", {})
        return {
            "summary": raw_res.get("executive_summary"),
            "client_position": effective_position,
            "burden_of_proof": audit.get("burden_of_proof"),
            "legal_basis": audit.get("legal_basis", []), 
            "strategic_analysis": rec.get("strategic_recommendation", {}).get("recommendation_text") if isinstance(rec, dict) else "",
            "strengths": rec.get("strengths", []) if isinstance(rec, dict) else [],
            "weaknesses": rec.get("weaknesses", []) if isinstance(rec, dict) else [],
            "key_arguments": rec.get("key_arguments", []) if isinstance(rec, dict) else [],
            "action_plan": rec.get("action_plan", []) if isinstance(rec, dict) else [],
            "missing_evidence": raw_res.get("missing_evidence", []),
            "success_probability": rec.get("success_probability") if isinstance(rec, dict) else None,
            "risk_level": rec.get("risk_level", "MEDIUM") if isinstance(rec, dict) else "MEDIUM"
        }
    except Exception as e:
        logger.error(f"Analysis Processing Failed: {e}")
        return {"summary": "Dështoi gjenerimi i analizës strategjike."}

async def run_deep_strategy(db: Database, case_id: str, user_id: str, client_position: Optional[str] = None) -> Dict[str, Any]:
    """PHOENIX: Parallel execution with role-adapted War Room simulation and full fashikull ingestion."""
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    effective_position = (client_position or case.get("client_position") or "DEFENDANT").upper()
    client_name = case.get("client_name") or case.get("client", {}).get("name") or "Shaban Bala"
    opposing_name = case.get("opposing_party") or "Getting Competent ShPK / Raimier Gerger"

    try:
        full_context_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=True)
        facts_only_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=False)
        
        full_context, facts_only = await asyncio.gather(full_context_task, facts_only_task)
        identity_header = llm_service.build_dynamic_identity_header(client_name=client_name, opposing_name=opposing_name, position=effective_position)

        context_with_role = f"{identity_header}\n\nPOZICIONI I KLIENTIT TONË: {effective_position}\n\n{full_context}"

        tasks = [
            llm_service.generate_adversarial_simulation(context_with_role),
            llm_service.build_case_chronology(facts_only), 
            llm_service.detect_contradictions(full_context)
        ]
        
        adv, chr_res, cnt = await asyncio.gather(*tasks)
        
        return {
            "client_position": effective_position,
            "adversarial_simulation": adv if isinstance(adv, dict) else {},
            "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
            "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
        }
    except Exception as e:
        logger.error(f"Deep Strategy Failed: {e}")
        return {"error": "Dështoi analiza e thellë."}

async def archive_full_strategy_report(db: Database, case_id: str, user_id: str, legal_data: Dict[str, Any], deep_data: Dict[str, Any], lang: str = "sq") -> Dict[str, Any]:
    """Synthesizes all analysis data and persists it as a PDF in the Archive."""
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid})
    
    if not case:
        return {"error": "Rasti nuk u gjet."}
        
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
            title = lb.get('title', 'Ligj/Nen')
            md += f"### {title}\n"
            md += f"**Baza:** {lb.get('article', '')}\n\n"
            md += f"**Arsyetimi Strategjik:** {lb.get('relevance', '')}\n\n"
        
    md += "## 3. ANALIZA STRATEGJIKE\n"
    md += f"{legal_data.get('strategic_analysis', '')}\n\n"
    
    if legal_data.get('strengths'):
        md += "### Pikat e forta\n"
        for s in legal_data.get('strengths', []):
            md += f"* {s}\n"
        md += "\n"
    
    if legal_data.get('weaknesses'):
        md += "### Pikat e dobëta\n"
        for w in legal_data.get('weaknesses', []):
            md += f"* {w}\n"
        md += "\n"
    
    if legal_data.get('action_plan'):
        md += "### Hapat e rekomanduar\n"
        for step in legal_data.get('action_plan', []):
            md += f"* {step}\n"
    
    sim = deep_data.get('adversarial_simulation', {})
    md += "\n---\n## 4. SIMULIMI I KUNDËRSHTARIT (WAR ROOM)\n"
    md += f"### STRATEGJIA E PALËS TJETËR\n{sim.get('opponent_strategy', 'Nuk u gjenerua.')}\n\n"

    if deep_data.get('chronology'):
        md += "\n## 5. KRONOLOGJIA E FAKTEVE\n"
        for event in deep_data.get('chronology', []):
            md += f"* **{event.get('date', '')}**: {event.get('event', '')}\n"

    if deep_data.get('contradictions'):
        md += "\n## 6. ANALIZA E KONTRADIKTAVE\n"
        for c in deep_data.get('contradictions', []):
            severity = c.get('severity', 'LOW')
            md += f"### Konflikt: {severity}\n"
            md += f"**Deklarata:** {c.get('claim', '')}\n"
            md += f"**Prova:** {c.get('evidence', '')}\n"
            md += f"**Impakti:** {c.get('impact', '')}\n\n"

    try:
        main_report_title = _get_text('analysis_title', lang)
        
        pdf_buffer = report_service.create_pdf_from_text(
            text=md,
            document_title=main_report_title,
            header_meta_content_html=None 
        )
        pdf_bytes = pdf_buffer.getvalue()
    except Exception as e:
        logger.error(f"Strategy PDF generation failed: {e}")
        return {"error": "Dështoi krijimi i dokumentit PDF."}

    archiver = archive_service.ArchiveService(db)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    archive_item_title = f"{_get_text('analysis_title', lang)} ({role_label}): {case_name}"
    filename = f"{_get_text('analysis_title', lang).replace(' ', '_')}_{case_name.replace(' ', '_')}_{timestamp}.pdf"
    
    try:
        archive_item = await archiver.save_generated_file(
            user_id=user_id,
            filename=filename,
            content=pdf_bytes,
            category="CASE_FILE",
            title=archive_item_title,
            case_id=case_id
        )
        return {"status": "success", "item_id": str(archive_item.id)}
    except Exception as e:
        logger.error(f"Strategy archiving failed: {e}")
        return {"error": "Dështoi ruajtja në arkiv."}