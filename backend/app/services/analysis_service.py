# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V25.0 (DYNAMIC DUAL-PARTY ROLE PROMPT ENGINE)

import asyncio
import structlog
import io
from typing import List, Dict, Any, Tuple, Optional
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone

import app.services.llm_service as llm_service
from . import vector_store_service, report_service, archive_service
from .report_service import _get_text 

logger = structlog.get_logger(__name__)

import logging
debug_logger = logging.getLogger("analysis_debug")
debug_logger.setLevel(logging.DEBUG)
if not debug_logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    debug_logger.addHandler(ch)

async def _fetch_rag_context_async(db: Database, case_id: str, user_id: str, include_laws: bool = True) -> str:
    """Parallelized and filtered RAG retrieval."""
    case = await asyncio.to_thread(db.cases.find_one, {"_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id})
    q = f"{case.get('case_name', '')} {case.get('description', '')}" if case else "Legal analysis"
    
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=q, case_context_id=case_id, n_results=15)
    ]
    if include_laws:
        law_query = f"{q} ligj neni dispozita"
        tasks.append(asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=law_query, n_results=15))
    
    results = await asyncio.gather(*tasks)
    case_facts = results[0]
    global_laws = results[1] if include_laws else []

    blocks = ["=== FAKTE NGA DOSJA ==="]
    for f in case_facts:
        blocks.append(f"DOKUMENTI: {f['source']} (Faqja {f['page']})\nTEKSTI: {f['text']}\n")
    
    if include_laws:
        if global_laws:
            blocks.append("=== BAZA LIGJORE STATUTORE ===")
            for l in global_laws:
                law_title = l.get('law_title', 'Ligji i panjohur')
                article_num = l.get('article_number', '')
                if article_num:
                    blocks.append(f"LIGJI: {law_title}, Neni {article_num}\nTEKSTI: {l['text']}\n")
                else:
                    blocks.append(f"LIGJI: {law_title}\nTEKSTI: {l['text']}\n")
        else:
            blocks.append("=== BAZA LIGJORE STATUTORE ===\nNuk u gjetën dispozita ligjore specifike.")
            
    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "owner_id": u_oid}) is not None
    except: return False

def build_and_populate_graph(db: Database, case_id: str, user_id: str) -> bool:
    """Synchronously extracts entities from all case documents and populates the Graph DB."""
    if not authorize_case_access(db, case_id, user_id):
        logger.warning("Unauthorized graph build attempt", case_id=case_id, user_id=user_id)
        return False
    try:
        from .document_service import get_document_content_by_key
        from .graph_service import graph_service
        doc_cursor = db.documents.find({"case_id": ObjectId(case_id)})
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
    """PHOENIX: High-IQ analysis mapping law to case relevance with explicit Party Role Mandate."""
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    user = await asyncio.to_thread(db.users.find_one, {"_id": u_oid}) or {}
    profile = await asyncio.to_thread(db.business_profiles.find_one, {"$or": [{"user_id": u_oid}, {"user_id": str(user_id)}]}) or {}
    
    # Resolve explicit client party stance (DEFENDANT vs PLAINTIFF)
    effective_position = (client_position or case.get("client_position") or "DEFENDANT").upper()
    active_user_identity = f"Emri: {user.get('username', '')}, Email: {user.get('email', '')}, Biznesi: {profile.get('firm_name', '')}"
    
    context = await _fetch_rag_context_async(db, case_id, user_id, include_laws=True)

    if effective_position == "PLAINTIFF":
        position_instruction = """
        MANDATI ZYRTAR I PALËS: SULM / PADITËS / I DËMTUAR
        - TI JE PËRFAQËSUESI LIGJOR I PADITËSIT / TË DËMTUARIT.
        - KUNDËRSHTARI TUAJ ËSHTË: I Padituri / I Akuzuari.
        - Të gjitha strategjitë, pikat e forta, pikat e dobëta të kundërshtarit dhe plani i veprimit DUHET TË JENË 100% OFENSIVE DHE SULMUESE PËR PADITËSIN.
        - Fokusohuni te: vërtetimi i përgjegjësisë së të paditurit, provimi i dëmit të shkaktuar, sigurimi i kërkesëpadisë, dhe rrëzimi i prapësimeve apo justifikimeve të të paditurit.
        """
    else:
        position_instruction = """
        MANDATI ZYRTAR I PALËS: MBROJTJE / I PADITUR / I AKUZUAR
        - TI JE MBROJTËSI LIGJOR I TË PADITURIT / TË AKUZUARIT.
        - KUNDËRSHTARI TUAJ ËSHTË: Paditësi / Prokuroria.
        - Të gjitha strategjitë, pikat e forta, pikat e dobëta të kundërshtarit dhe plani i veprimit DUHET TË JENË 100% MBROJTËSE DHE KUNDËRSHTUESE PËR TË PADITURIN.
        - Fokusohuni te: rrëzimi i padisë, shfrytëzimi i gabimeve procedurale të paditësit (si mungesa e prokurës origjinale, parashkrimi i kërkesës, apo mungesa e provave), dhe hartimi i Prapësimit apo Kundërpadisë.
        """

    system_prompt = """
    DETYRA: Analizë e thellë strategjike dhe ligjore e këtij rasti. Jep një vlerësim profesional për avokatin, dhe shpjegime praktike për qytetarin.
    
    PËRDORUESI AKTIV QË PO KËRKON ANALIZËN:
    __ACTIVE_USER_IDENTITY__
    
    __PARTY_POSITION_INSTRUCTION__
    
    UDHËZIME PËR THJESHTËSINË (CITIZEN-FRIENDLY MANDATE):
    1. Seksioni 'executive_summary' (Përmbledhja) DUHET të ndahet në dy pjesë të qarta duke përdorur saktësisht këto kryetituj:
       - '### 👨‍💼 UDHËZUESI PËR QYTETARIN (Gjuhë e Thjeshtë)'
         (Shpjegoni me fjalë të thjeshta të përditshme se çfarë po ndodh në këtë lëndë dhe çfarë do të thotë për anën tuaj.)
       - '### ⚖️ ANALIZA PROFESIONALE E AVOKATIT'
         (Përmbledhja teknike, strategjike dhe procedurale për avokatët.)
         
    2. Seksioni 'action_plan' (Plani i Veprimit) DUHET të ketë udhëzime konkrete për rolin tuaj.
    
    3. INJEKTIMI I PROMPT-IT TË HARTIMIT (DRAFTING PROMPT):
       Në pikën ku udhëzohet përgatitja e shkresës, shkruani një PROMPT konkret dhe të gatshëm që përdoruesi mund ta kopjojë dhe ta ngjisë direkt në faqen e 'Hartimit'.
       *Shembull*: "Hapi 2: Shkoni te faqja e 'Hartimit' dhe ngjisni këtë prompt: `Gjenero një Prapësim në lëndën...`"
    
    MANDATI SHTESË LIGJOR:
    - MOS përdor asnjë ligj që nuk shfaqet në kontekstin e dhënë në "BAZA LIGJORE STATUTORE".
    - Për çdo nen të cituar, shpjego 'RELEVANCËN' për këtë rast specifik.
    
    STRUKTURA E PËRGJIGJES (JSON):
    {
      "executive_summary": "### 👨‍💼 UDHËZUESI PËR QYTETARIN (Gjuhë e Thjeshtë)\\n[Shpjegimi i thjeshtë]\\n\\n### ⚖️ ANALIZA PROFESIONALE E AVOKATIT\\n[Analiza teknike]",
      "legal_audit": {
          "burden_of_proof": "Kush e mban barrën e provës dhe pse?",
          "legal_basis": [
            {
              "title": "[Emri i Ligjit, Neni XX](doc://ligji)",
              "article": "Teksti i nenit",
              "relevance": "Pse ky nen është vendimtar për këtë rast?"
            }
          ]
      },
      "strategic_recommendation": {
          "recommendation_text": "Analiza strategjike e përshtatur për anën tuaj",
          "strengths": ["Lista e pikave tona të forta"],
          "weaknesses": ["Pikat e dobëta të kundërshtarit dhe rreziqet tona"],
          "key_arguments": ["Argumentet kryesore specifike për parashtresën tonë"],
          "action_plan": [
             "HAPAT PËR JU (Si Qytetar): [Udhëzimi i thjeshtë praktik i veprimit]",
             "HAPAT PËR JU (Si Qytetar) - HARTIMI: Përdorni këtë prompt të gatshëm: `[Teksti i prompt-it]`",
             "HAPAT PËR AVOKATIN TUAJ: [Udhëzimi teknik ligjor]"
          ],
          "success_probability": "XX%",
          "risk_level": "LOW/MEDIUM/HIGH"
      },
      "missing_evidence": ["Çfarë provash ose dokumentesh duhen siguruar?"]
    }
    """
    
    system_prompt = system_prompt.replace("__ACTIVE_USER_IDENTITY__", active_user_identity)
    system_prompt = system_prompt.replace("__PARTY_POSITION_INSTRUCTION__", position_instruction)
    
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
    """PHOENIX: Parallel execution with role-adapted War Room simulation."""
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    case = await asyncio.to_thread(db.cases.find_one, {"_id": c_oid}) or {}
    effective_position = (client_position or case.get("client_position") or "DEFENDANT").upper()

    try:
        full_context_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=True)
        facts_only_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=False)
        
        full_context, facts_only = await asyncio.gather(full_context_task, facts_only_task)

        # Append explicit party mandate context to simulation prompt
        context_with_role = f"POZICIONI I KLIENTIT TONË: {effective_position}\n\n{full_context}"

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
    
    case = await asyncio.to_thread(db.cases.find_one, {"_id": ObjectId(case_id)})
    
    if not case:
        return {"error": "Rasti nuk u gjet."}
        
    case_name = case.get("case_name", "Pa Titull")
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