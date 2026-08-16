# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTELLIGENCE (NEO4J PRODUCTION READY & SAFE CYPHER)

import os
import time
import re
import structlog
from neo4j import GraphDatabase, Driver, basic_auth
from typing import List, Dict, Any, Optional

logger = structlog.get_logger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def normalize_text_to_albanian(text: str) -> str:
    return text.strip() if text else ""

class GraphService:
    _driver: Optional[Driver] = None
    _connection_failed_until: float = 0.0

    def _connect(self):
        if time.time() < self._connection_failed_until:
            return

        if self._driver:
            return

        if not NEO4J_URI or NEO4J_URI in ["bolt://neo4j:7687", "REPLACE_WITH_AURA_URI"]:
            self._connection_failed_until = time.time() + 300
            return

        try:
            self._driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=30 * 60
            )
            self._driver.verify_connectivity()
            logger.info("✅ Neo4j Aura Cloud Connected Successfully")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j Connection Disabled (cooling down for 60s): {e}")
            self._driver = None
            self._connection_failed_until = time.time() + 60

    def create_evidence_edge(self, case_id: str, source_id: str, target_id: str, relation: str, properties: Dict[str, Any]):
        """Krijon lidhjen në Neo4j duke ruajtur të gjitha atributet dhe duke mbrojtur shkronjat shqipe."""
        self._connect()
        if not self._driver:
            return

        clean_rel = re.sub(r'[^A-Z0-9_]', '_', relation.upper().replace(" ", "_"))
        if not clean_rel:
            clean_rel = "LIDHJE_LIGJORE"

        evidence_text = properties.get("evidence_text", "")
        amount_eur = properties.get("amount_eur")
        date_iso = properties.get("date_iso", "")

        query = f"""
        MERGE (a:Entity {{id: $source_id, case_id: $case_id}})
        MERGE (b:Entity {{id: $target_id, case_id: $case_id}})
        MERGE (a)-[r:`{clean_rel}` {{case_id: $case_id}}]->(b)
        SET r.evidence_text = $evidence_text,
            r.amount_eur = $amount_eur,
            r.date_iso = $date_iso,
            r.updated_at = datetime()
        """
        try:
            with self._driver.session() as session:
                session.run(
                    query,
                    case_id=case_id,
                    source_id=source_id,
                    target_id=target_id,
                    evidence_text=evidence_text,
                    amount_eur=amount_eur,
                    date_iso=date_iso
                )
        except Exception as e:
            logger.error(f"Neo4j create_evidence_edge error: {e}")

    def get_case_graph(self, case_id: str) -> Dict[str, List[Dict[str, Any]]]:
        self._connect()
        if not self._driver:
            return {"nodes": [], "links": []}
        
        nodes_dict = {}
        links_list = []
        
        query = """
        MATCH (n) WHERE n.case_id = $case_id
        OPTIONAL MATCH (n)-[r]->(m) WHERE m.case_id = $case_id
        RETURN n, r, m
        """
        
        try:
            with self._driver.session() as session:
                res = session.run(query, case_id=case_id)
                for record in res:
                    n, r, m = record['n'], record['r'], record['m']
                    
                    for node in [n, m]:
                        if node:
                            n_id = str(node.get("id") or node.element_id)
                            if n_id not in nodes_dict:
                                raw_label = list(node.labels)[0] if node.labels else "PERSONA"
                                nodes_dict[n_id] = {
                                    "id": n_id,
                                    "name": node.get('name') or node.get('label') or n_id,
                                    "group": raw_label.upper(),
                                    "description": node.get('description', ''),
                                    "val": 20
                                }
                    
                    if r and n and m:
                        n_source = str(n.get("id") or n.element_id)
                        m_target = str(m.get("id") or m.element_id)
                        links_list.append({
                            "source": n_source,
                            "target": m_target,
                            "label": type(r).__name__.replace("_", " "),
                            "evidence_text": r.get("evidence_text", ""),
                            "date_iso": r.get("date_iso", "")
                        })
        except Exception as e:
            logger.error(f"Graph Fetch Error: {e}")
            
        return {"nodes": list(nodes_dict.values()), "links": links_list}

    def delete_case_nodes(self, case_id: str):
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (n {case_id: $id}) DETACH DELETE n", id=case_id)
        except Exception as e:
            logger.warning(f"Delete Case Nodes Error: {e}")

graph_service = GraphService()