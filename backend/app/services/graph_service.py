# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTELLIGENCE V4.0 (NEO4J AURA CLOUD & SILENT COOLDOWN FIX)

import os
import time
import structlog
from neo4j import GraphDatabase, Driver, basic_auth
from typing import List, Dict, Any, Optional

logger = structlog.get_logger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

class GraphService:
    _driver: Optional[Driver] = None
    _connection_failed_until: float = 0.0

    def _connect(self):
        # Prevent continuous reconnection spam if connection previously failed (60s cooldown)
        if time.time() < self._connection_failed_until:
            return

        if self._driver:
            return

        # Skip connection attempts if URI is empty or unconfigured default
        if not NEO4J_URI or NEO4J_URI in ["bolt://neo4j:7687", "REPLACE_WITH_AURA_URI"]:
            self._connection_failed_until = time.time() + 300  # Pause for 5 minutes
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
                            n_id = str(node.element_id)
                            if n_id not in nodes_dict:
                                label = list(node.labels)[0] if node.labels else "Entity"
                                nodes_dict[n_id] = {
                                    "id": n_id,
                                    "name": node.get('name', 'N/A'),
                                    "group": label.upper(),
                                    "description": node.get('description', ''),
                                    "val": 25 if label == "Claim" else 15
                                }
                    
                    if r and n and m:
                        links_list.append({
                            "source": str(n.element_id),
                            "target": str(m.element_id),
                            "label": type(r).__name__
                        })
        except Exception as e:
            logger.error(f"Graph Fetch Error: {e}")
            
        return {"nodes": list(nodes_dict.values()), "links": links_list}

    def ingest_entities_and_relations(
        self, 
        case_id: str, 
        document_id: str, 
        doc_name: str, 
        entities: List[Dict], 
        relations: List[Dict], 
        doc_metadata: Optional[Dict] = None
    ):
        """Robust ingestion for professional argument maps."""
        self._connect()
        if not self._driver:
            return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            tx.run(
                "MERGE (d:Document {id: $d_id}) SET d.case_id = $c_id, d.name = $d_name, d.processed_at = datetime()", 
                d_id=d_id, c_id=c_id, d_name=d_name
            )
            
            for ent in ents:
                name = (ent.get("name") or ent.get("label") or "").strip()
                if not name:
                    continue
                
                raw_type = str(ent.get("type", "Entity")).lower()
                if "claim" in raw_type or "pretendim" in raw_type:
                    label = "Claim"
                elif "fact" in raw_type or "fakt" in raw_type:
                    label = "Fact"
                elif "law" in raw_type or "ligj" in raw_type:
                    label = "Law"
                elif "evidence" in raw_type or "prove" in raw_type:
                    label = "Evidence"
                else:
                    label = "Party"

                tx.run(f"""
                    MERGE (e:{label} {{name: $name, case_id: $c_id}})
                    SET e.description = $desc
                    WITH e
                    MATCH (d:Document {{id: $d_id}})
                    MERGE (d)-[:MENTIONS]->(e)
                """, name=name, c_id=c_id, d_id=d_id, desc=ent.get("description", ""))

            for rel in rels:
                subj = rel.get("source") or rel.get("subject")
                obj = rel.get("target") or rel.get("object")
                if subj and obj:
                    pred = str(rel.get("relation", "RELATED")).upper().replace(" ", "_")
                    tx.run(f"""
                        MATCH (a {{name: $subj, case_id: $c_id}}), (b {{name: $obj, case_id: $c_id}})
                        MERGE (a)-[:{pred} {{case_id: $c_id}}]->(b)
                    """, subj=subj, obj=obj, c_id=c_id)

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, doc_name, entities, relations)
        except Exception as e:
            logger.error(f"Ingestion Error: {e}")

    def delete_node(self, node_id: str):
        """Deletes a specific node by its ID attribute or element_id."""
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (n) WHERE n.id = $id OR elementId(n) = $id DETACH DELETE n", id=node_id)
        except Exception as e:
            logger.warning(f"Delete Node Error: {e}")

    def delete_document_nodes(self, document_id: str):
        """Deletes a document node and orphaned relationships."""
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (d:Document {id: $id}) DETACH DELETE d", id=document_id)
        except Exception as e:
            logger.warning(f"Delete Document Nodes Error: {e}")

    def delete_case_nodes(self, case_id: str):
        """Deletes all graph nodes associated with a case."""
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (n) WHERE n.case_id = $id DETACH DELETE n", id=case_id)
        except Exception as e:
            logger.warning(f"Delete Case Nodes Error: {e}")

graph_service = GraphService()