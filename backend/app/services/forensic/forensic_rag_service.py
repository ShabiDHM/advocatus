# FILE: backend/app/services/forensic/forensic_rag_service.py
# PHOENIX PROTOCOL - FORENSIC GRAPHRAG & WAR ROOM SYNTHESIZER V1.0

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from .forensic_llm_service import call_forensic_llm, stream_forensic_llm_async

logger = logging.getLogger(__name__)

# Neo4j Driver Singleton
_neo4j_driver = None

def get_neo4j_driver():
    global _neo4j_driver
    uri = getattr(settings, "NEO4J_URI", "")
    user = getattr(settings, "NEO4J_USER", "neo4j")
    pwd = getattr(settings, "NEO4J_PASSWORD", "")

    if not uri or not pwd:
        return None

    if _neo4j_driver is None:
        try:
            from neo4j import GraphDatabase
            _neo4j_driver = GraphDatabase.driver(uri, auth=(user, pwd))
            logger.info("✅ Lidhja me Neo4j Aura GraphRAG u vendos me sukses.")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j nuk mund të inicializohet: {e}")
            _neo4j_driver = None

    return _neo4j_driver

def query_legal_knowledge_graph(query_term: str) -> List[Dict[str, Any]]:
    """Pyet rrjetin grafik për nene, precedentë dhe lidhje ligjore."""
    driver = get_neo4j_driver()
    if not driver:
        return []

    cypher = """
    MATCH (n)
    WHERE n.name CONTAINS $term OR n.title CONTAINS $term OR n.case_number CONTAINS $term
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n.name AS entity, labels(n)[0] AS type, type(r) AS relation, m.name AS connected_to
    LIMIT 10
    """
    results = []
    try:
        with driver.session() as session:
            records = session.run(cypher, term=query_term)
            for r in records:
                results.append({
                    "entity": r["entity"],
                    "type": r["type"],
                    "relation": r["relation"],
                    "connected_to": r["connected_to"]
                })
    except Exception as e:
        logger.warning(f"⚠️ Neo4j Query Error: {e}")

    return results

def synthesize_war_room_intelligence(
    case_title: str,
    audio_findings: Optional[Dict[str, Any]] = None,
    visual_findings: Optional[Dict[str, Any]] = None,
    financial_findings: Optional[Dict[str, Any]] = None,
    document_excerpts: Optional[List[str]] = None,
    graph_context: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Sinteza Madhore e War Room me Claude Sonnet 4.6:
    Bashkon të 5 laboratorët për të gjeneruar strategjinë vrastare mbrojtëse/akuzuese.
    """
    system_prompt = """KOMANDA E WAR ROOM FORENZIK (CLAUDE SONNET 4.6):
Ju jeni Shefi i Shtabit të Mbrojtjes Ligjore dhe Eksperti Kryesor Forenzik.
MANDATI JUAJ NË WAR ROOM:
1. Bashkoni provat e audios (stres/kërcënime), provat vizuale (GPS/EXIF/manipulim), shifrat financiare dhe shkresat e lëndës.
2. Zbuloni KONTRADIKTAT NDËRPROVUESE (p.sh. diferenca orare mes bisedës audio dhe vendndodhjes GPS, fryrje shifrash financiare).
3. Hartoni 5 PYETJE TËRTHORE VRATARE (Cross-Examination) për të diskredituar palën kundërshtare ose dëshmitarët e tyre.
4. Identifikoni rrethanat lehtësuese ose pikëpyetjet e mëdha të dyshimit të arsyeshëm ('In Dubio Pro Reo').

Kthe përgjigjen në format JSON:
{
  "war_room_executive_summary": "Përmbledhja strategjike e lëndës",
  "critical_cross_contradictions": ["Kontradikta 1", "Kontradikta 2"],
  "cross_examination_traps": [
    {
      "witness_or_target": "Kush pyetet",
      "question": "Pyetja e saktë vrastare",
      "trap_explanation": "Pse kjo pyetje e zë në kurth dhe cilën provë e ekspozon"
    }
  ],
  "in_dubio_pro_reo_vectors": ["Vektori i dyshimit 1", "Vektori i dyshimit 2"],
  "winning_theory_of_the_case": "Teoria fituese e lëndës për fjalën përfundimtare"
}"""

    bundle = {
        "case_title": case_title,
        "audio_forensics": audio_findings or {},
        "visual_forensics": visual_findings or {},
        "financial_forensics": financial_findings or {},
        "document_excerpts": document_excerpts or [],
        "graph_precedents": graph_context or []
    }

    import json
    user_content = f"TË GJITHA PROVAT E DOSJES FORENZIKE:\n{json.dumps(bundle, ensure_ascii=False, indent=2)}"

    raw_response = call_forensic_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        json_mode=True,
        temperature=0.0
    )

    try:
        from app.services.llm.llm_client import clean_and_parse_json
        parsed = clean_and_parse_json(raw_response)
        if parsed:
            return parsed
    except Exception:
        pass

    return {
        "war_room_executive_summary": "Sinteza u përpilua.",
        "critical_cross_contradictions": [],
        "cross_examination_traps": [],
        "in_dubio_pro_reo_vectors": [],
        "winning_theory_of_the_case": raw_response
    }

async def stream_interactive_war_room_chat(
    case_context: str,
    chat_history: List[Dict[str, str]],
    user_question: str
):
    """Bisedë interaktive në kohë reale me Claude Sonnet 4.6 për strategjinë e lëndës."""
    system_prompt = f"""TERMINALI STRATEGJIK I WAR ROOM FORENZIK (CLAUDE SONNET 4.6):
Ju po këshilloni avokatin udhëheqës në kohë reale brenda sallës operative.
Përgjigjuni me taktika konkrete procedurale, analiza provash dhe nene të sakta të Kosovës.

KONTEKSTI I LËNDËS:
{case_context}"""

    # Formatoni historikun
    conversation_str = ""
    for msg in chat_history[-6:]:
        conversation_str += f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}\n"

    full_user_input = f"{conversation_str}USER: {user_question}\nASSISTANT (WAR ROOM):"

    async for chunk in stream_forensic_llm_async(
        system_prompt=system_prompt,
        user_content=full_user_input,
        temperature=0.05
    ):
        yield chunk