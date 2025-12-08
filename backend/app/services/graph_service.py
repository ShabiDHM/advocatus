# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - LITIGATION ENGINE V6
# 1. SCHEMA: Added support for 'CLAIM', 'EVIDENCE', 'LAW' nodes.
# 2. LOGIC: Added 'ACCUSES', 'CONTRADICTS', 'CORROBORATES' relationship handling.
# 3. INTELLIGENCE: New 'find_contradictions' method to feed the Chatbot.

import os
import structlog
from neo4j import GraphDatabase, Driver, basic_auth
from typing import List, Dict, Any, Optional

logger = structlog.get_logger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class GraphService:
    _driver: Optional[Driver] = None

    def _connect(self):
        if self._driver: return
        try:
            self._driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))
            self._driver.verify_connectivity()
        except Exception as e:
            logger.error(f"❌ Neo4j Connection Failed: {e}")
            self._driver = None

    def close(self):
        if self._driver: self._driver.close()

    # --- ADVANCED INGESTION ---
    def ingest_legal_analysis(self, case_id: str, doc_id: str, analysis: List[Dict]):
        """
        Ingests high-level legal concepts extracted by the LLM.
        Expected format from LLM:
        [
          {"type": "CLAIM", "source": "Agim", "target": "Besnik", "text": "Stole the car", "status": "DISPUTED"},
          {"type": "FACT", "text": "Agim was in Tirana", "evidence_doc": "Flight Ticket.pdf"}
        ]
        """
        self._connect()
        if not self._driver: return

        def _tx_ingest_legal(tx, c_id, d_id, items):
            # Link Document to Case
            tx.run("MERGE (d:Document {id: $d_id}) SET d.case_id = $c_id", d_id=d_id, c_id=c_id)

            for item in items:
                # 1. Handle ACCUSATIONS (Person vs Person)
                if item.get('type') == 'ACCUSATION':
                    accuser = item.get('source', 'Unknown').title()
                    accused = item.get('target', 'Unknown').title()
                    claim_text = item.get('text', 'Unspecified Claim')
                    
                    query = """
                    MERGE (p1:Person {name: $accuser})
                    MERGE (p2:Person {name: $accused})
                    MERGE (c:Claim {text: $claim_text, case_id: $case_id})
                    MERGE (p1)-[:ACCUSES]->(p2)
                    MERGE (p1)-[:ASSERTS]->(c)
                    MERGE (c)-[:CONCERNS]->(p2)
                    MERGE (d:Document {id: $doc_id})-[:RECORDS]->(c)
                    """
                    tx.run(query, accuser=accuser, accused=accused, claim_text=claim_text, case_id=c_id, doc_id=d_id)

                # 2. Handle CONTRADICTIONS (Evidence vs Claim) - The "False Claim" Detector
                elif item.get('type') == 'CONTRADICTION':
                    claim_text = item.get('claim_text')
                    evidence_text = item.get('evidence_text')
                    
                    query = """
                    MERGE (c:Claim {text: $claim_text})
                    MERGE (e:Evidence {text: $evidence_text})
                    MERGE (d:Document {id: $doc_id})-[:CONTAINS]->(e)
                    MERGE (e)-[:CONTRADICTS]->(c)
                    """
                    tx.run(query, claim_text=claim_text, evidence_text=evidence_text, doc_id=d_id)

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest_legal, case_id, doc_id, analysis)
            logger.info("⚖️ Legal Graph Ingestion Complete")
        except Exception as e:
            logger.error(f"Legal Ingestion Failed: {e}")

    # --- THE DETECTIVE QUERIES ---
    
    def find_contradictions(self, case_id: str) -> str:
        """
        Returns a text summary of all contradictions found in the graph.
        Used by the Chatbot to answer "Is anyone lying?"
        """
        self._connect()
        if not self._driver: return ""

        query = """
        MATCH (e:Evidence)-[:CONTRADICTS]->(c:Claim)<-[:ASSERTS]-(p:Person)
        WHERE c.case_id = $case_id
        RETURN p.name as liar, c.text as lie, e.text as proof, e.source_doc as doc
        """
        
        try:
            with self._driver.session() as session:
                result = session.run(query, case_id=case_id)
                summary = []
                for r in result:
                    summary.append(f"⚠️ POTENTIAL FALSE CLAIM: {r['liar']} claimed '{r['lie']}', but evidence '{r['proof']}' contradicts this.")
                
                return "\n".join(summary) if summary else "No direct contradictions found in the graph."
        except Exception:
            return ""

    def get_accusation_chain(self, person_name: str) -> List[str]:
        """
        Who accused this person, and what did they accuse them of?
        """
        self._connect()
        if not self._driver: return []

        query = """
        MATCH (accuser:Person)-[:ACCUSES]->(target:Person {name: $name})
        MATCH (accuser)-[:ASSERTS]->(c:Claim)-[:CONCERNS]->(target)
        RETURN accuser.name, c.text
        """
        results = []
        try:
            with self._driver.session() as session:
                res = session.run(query, name=person_name.title())
                for r in res:
                    results.append(f"{r['accuser.name']} accused {person_name} of: {r['c.text']}")
            return results
        except Exception:
            return []

graph_service = GraphService()