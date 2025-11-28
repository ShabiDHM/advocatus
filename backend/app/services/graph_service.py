# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH SERVICE v2.0 (PROFESSIONAL GRADE)
# 1. INGESTION: Uses MERGE for relations to ensure no data is lost.
# 2. RETRIEVAL: Fetches deep relationships (Entity<->Entity) for a richer graph.
# 3. ROBUSTNESS: Handles connection errors gracefully.

import os
import structlog
from neo4j import GraphDatabase, Driver, basic_auth
from typing import List, Dict, Any, Optional

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class GraphService:
    _driver: Optional[Driver] = None

    def __init__(self):
        pass

    def _connect(self):
        if self._driver: return
        try:
            self._driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
            )
            self._driver.verify_connectivity()
            # logger.info("✅ Connected to Neo4j Graph Database.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()

    def delete_document_nodes(self, document_id: str):
        """Removes a document and cleans up orphan nodes."""
        self._connect()
        if not self._driver: return

        query = "MATCH (d:Document {id: $doc_id}) DETACH DELETE d"
        cleanup_query = "MATCH (n) WHERE NOT (n)--() DELETE n"
        
        try:
            with self._driver.session() as session:
                session.run(query, doc_id=document_id)
                session.run(cleanup_query)
            logger.info(f"🗑️ Deleted Graph Nodes for Document {document_id}")
        except Exception as e:
            logger.error(f"Graph Deletion Failed: {e}")

    def ingest_entities_and_relations(self, case_id: str, document_id: str, doc_name: str, entities: List[Dict], relations: List[Dict]):
        """Creates nodes and relationships. Uses MERGE aggressively to prevent data loss."""
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            # 1. Ensure Document Node Exists
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id, d.name = $doc_name, d.type = 'Document'
            """, doc_id=d_id, case_id=c_id, doc_name=d_name)

            # 2. Ingest Entities (Nodes)
            for ent in ents:
                label = ent.get("type", "Entity").capitalize()
                name = ent.get("name", "").strip()
                if not name: continue
                
                # Sanitize Label (Neo4j labels cannot be dynamic parameters easily in pure python without risk, strictly allowlist or default)
                allowed_labels = ["Person", "Organization", "Location", "Date", "Money", "Law", "Entity"]
                if label not in allowed_labels: label = "Entity"

                # Link Document -> Mentions -> Entity
                query = f"""
                MERGE (e:{label} {{name: $name}})
                SET e.type = $label
                WITH e
                MATCH (d:Document {{id: $doc_id}})
                MERGE (d)-[:MENTIONS]->(e)
                """
                tx.run(query, name=name, doc_id=d_id, label=label)

            # 3. Ingest Relationships (Edges)
            for rel in rels:
                subj = rel.get("subject", "").strip()
                obj = rel.get("object", "").strip()
                predicate = rel.get("relation", "RELATED_TO").upper().replace(" ", "_")
                
                if not subj or not obj: continue

                # PHOENIX FIX: Use MERGE for nodes too. 
                # If the AI found a relationship but missed the entity extraction, we create the node anyway.
                query = f"""
                MERGE (a {{name: $subj}})
                MERGE (b {{name: $obj}})
                MERGE (a)-[:{predicate}]->(b)
                """
                try:
                    tx.run(query, subj=subj, obj=obj)
                except Exception as e:
                    logger.warning(f"Failed to create relation {subj}->{obj}: {e}")

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, doc_name, entities, relations)
            logger.info(f"🕸️ Graph Ingestion Complete: {len(entities)} Entities, {len(relations)} Relations.")
        except Exception as e:
            logger.error(f"Graph Transaction Failed: {e}")

    def get_case_graph(self, case_id: str) -> Dict[str, List]:
        """
        Retrieves the 'Professional' subgraph for a case.
        Includes Documents, Entities, and ALL relationships between them.
        """
        self._connect()
        if not self._driver: return {"nodes": [], "links": []}

        # PHOENIX FIX: Expanded Query
        # 1. Find all documents for the case.
        # 2. Find all entities mentioned by those documents.
        # 3. Find relationships between those entities (The "Intelligence" layer).
        query = """
        MATCH (d:Document {case_id: $case_id})
        OPTIONAL MATCH (d)-[:MENTIONS]->(e)
        WITH collect(d) + collect(e) as case_nodes
        UNWIND case_nodes as n
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m IN case_nodes
        RETURN n, r, m
        LIMIT 300
        """
        
        nodes_dict = {}
        links_list = []
        
        try:
            with self._driver.session() as session:
                result = session.run(query, case_id=case_id)
                
                for record in result:
                    n = record['n']
                    m = record['m']
                    r = record['r']
                    
                    if n:
                        n_id = n.get("id", n.element_id) # Use prop ID if set (docs), else internal ID
                        if n_id not in nodes_dict:
                            # Determine Group/Color
                            labels = list(n.labels)
                            group = "Entity"
                            if "Document" in labels: group = "Document"
                            elif "Person" in labels: group = "Person"
                            elif "Organization" in labels: group = "Organization"
                            elif "Law" in labels: group = "Law"
                            
                            nodes_dict[n_id] = {
                                "id": n_id,
                                "name": n.get("name", "Unknown"),
                                "group": group,
                                "val": 20 if group == "Document" else 10
                            }

                    if m:
                        m_id = m.get("id", m.element_id)
                        if m_id not in nodes_dict:
                            labels = list(m.labels)
                            group = "Entity"
                            if "Document" in labels: group = "Document"
                            elif "Person" in labels: group = "Person"
                            elif "Organization" in labels: group = "Organization"
                            elif "Law" in labels: group = "Law"

                            nodes_dict[m_id] = {
                                "id": m_id,
                                "name": m.get("name", "Unknown"),
                                "group": group,
                                "val": 10
                            }

                    if r and n and m:
                        links_list.append({
                            "source": n.get("id", n.element_id),
                            "target": m.get("id", m.element_id),
                            "label": type(r).__name__
                        })
                        
            return {
                "nodes": list(nodes_dict.values()),
                "links": links_list
            }
        except Exception as e:
            logger.error(f"Graph Retrieval Failed: {e}")
            return {"nodes": [], "links": []}

graph_service = GraphService()