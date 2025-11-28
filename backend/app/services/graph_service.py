# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH LOGIC FIX
# 1. LABEL FIX: Uses actual Document Name instead of static "DOKUMENTI".
# 2. CLEANUP: Added 'delete_document_nodes' to remove deleted files from graph.
# 3. ROBUSTNESS: Better handling of missing properties.

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
            logger.info("✅ Connected to Neo4j Graph Database.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()

    def delete_document_nodes(self, document_id: str):
        """
        Removes a document and its exclusive entities from the graph.
        """
        self._connect()
        if not self._driver: return

        # Cypher: Detach delete the document node
        # Also delete orphan entities that are no longer connected to anything
        query = """
        MATCH (d:Document {id: $doc_id})
        DETACH DELETE d
        """
        # Cleanup orphans (optional but recommended)
        cleanup_query = """
        MATCH (n)
        WHERE NOT (n)--()
        DELETE n
        """
        try:
            with self._driver.session() as session:
                session.run(query, doc_id=document_id)
                session.run(cleanup_query)
            logger.info(f"🗑️ Deleted Graph Nodes for Document {document_id}")
        except Exception as e:
            logger.error(f"Graph Deletion Failed: {e}")

    def ingest_entities_and_relations(self, case_id: str, document_id: str, doc_name: str, entities: List[Dict], relations: List[Dict]):
        """Creates nodes and relationships from AI-extracted data."""
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            # 1. Document Node (Now includes NAME)
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id, d.name = $doc_name
            """, doc_id=d_id, case_id=c_id, doc_name=d_name)

            # 2. Entities
            for ent in ents:
                label = ent.get("type", "Entity").capitalize()
                name = ent.get("name", "").strip()
                if not name: continue
                
                allowed_labels = ["Person", "Organization", "Location", "Date", "Money", "Law", "Entity"]
                if label not in allowed_labels: label = "Entity"

                query = f"""
                MERGE (e:{label} {{name: $name}})
                MERGE (d:Document {{id: $doc_id}})
                MERGE (d)-[:MENTIONS]->(e)
                """
                tx.run(query, name=name, doc_id=d_id)

            # 3. Relationships
            for rel in rels:
                subj = rel.get("subject", "").strip()
                obj = rel.get("object", "").strip()
                predicate = rel.get("relation", "RELATED_TO").upper().replace(" ", "_")
                
                if not subj or not obj: continue

                query = f"""
                MATCH (a {{name: $subj}})
                MATCH (b {{name: $obj}})
                MERGE (a)-[:{predicate}]->(b)
                """
                try:
                    tx.run(query, subj=subj, obj=obj)
                except Exception:
                    pass

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, doc_name, entities, relations)
            logger.info(f"🕸️ Graph Ingestion Complete: {len(entities)} Nodes.")
        except Exception as e:
            logger.error(f"Graph Transaction Failed: {e}")

    def get_case_graph(self, case_id: str) -> Dict[str, List]:
        """
        Retrieves the full knowledge graph for a specific case.
        """
        self._connect()
        if not self._driver: return {"nodes": [], "links": []}

        query = """
        MATCH (d:Document {case_id: $case_id})
        OPTIONAL MATCH (d)-[r]-(target)
        RETURN d, r, target
        """
        
        nodes = {}
        links = []
        
        try:
            with self._driver.session() as session:
                result = session.run(query, case_id=case_id)
                
                for record in result:
                    # 1. Document Node
                    doc_node = record['d']
                    if doc_node:
                        doc_id = getattr(doc_node, "element_id", str(doc_node.id))
                        doc_prop_id = doc_node.get("id", doc_id)
                        
                        # PHOENIX FIX: Use actual document name
                        doc_name = doc_node.get("name", "Document") 
                        
                        if doc_prop_id not in nodes:
                            nodes[doc_prop_id] = {
                                "id": doc_prop_id,
                                "name": doc_name, # Shows "Contract.pdf" instead of "DOKUMENTI"
                                "group": "DOCUMENT",
                                "val": 20
                            }
                    
                    # 2. Target Node
                    target = record['target']
                    rel = record['r']
                    
                    if target and rel:
                        target_id = getattr(target, "element_id", str(target.id))
                        target_labels = list(target.labels)
                        group_type = target_labels[0] if target_labels else "Entity"
                        target_name = target.get("name", "Unknown")
                        
                        # Use Name + Group as unique key to prevent merging unrelated entities?
                        # For now, element_id is safest.
                        node_key = target_id 
                        
                        if node_key not in nodes:
                            nodes[node_key] = {
                                "id": node_key,
                                "name": target_name,
                                "group": group_type,
                                "val": 10
                            }
                        
                        # 3. Link
                        links.append({
                            "source": doc_prop_id,
                            "target": node_key,
                            "label": type(rel).__name__
                        })
                        
            return {
                "nodes": list(nodes.values()),
                "links": links
            }
        except Exception as e:
            logger.error(f"Graph Retrieval Failed: {e}")
            return {"nodes": [], "links": []}

# Global Instance
graph_service = GraphService()