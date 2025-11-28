# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTERFACE (VISUALIZATION ENABLED)
# 1. SEARCH: Fuzzy matching for smart lookups.
# 2. VISUALIZATION: Added 'get_case_graph' for 2D React Force Graph.
# 3. SAFETY: Robust error handling and connection management.

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

    def ingest_entities_and_relations(self, case_id: str, document_id: str, entities: List[Dict], relations: List[Dict]):
        """Creates nodes and relationships from AI-extracted data."""
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, ents, rels):
            # 1. Document Node
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id
            """, doc_id=d_id, case_id=c_id)

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
                session.execute_write(_tx_ingest, case_id, document_id, entities, relations)
            logger.info(f"🕸️  Graph Ingestion Complete: {len(entities)} Nodes.")
        except Exception as e:
            logger.error(f"Graph Transaction Failed: {e}")

    def find_hidden_connections(self, query_term: str) -> List[str]:
        """
        Finds connections using FUZZY matching (Case Insensitive).
        """
        self._connect()
        if not self._driver: return []
        
        query = """
        MATCH (a)-[r]-(b)
        WHERE toLower(a.name) CONTAINS toLower($term)
        RETURN a.name as source, type(r) as relation, b.name as target, labels(b) as type
        LIMIT 15
        """
        try:
            with self._driver.session() as session:
                result = session.run(query, term=query_term)
                connections = []
                for record in result:
                    target_type = record['type'][0] if record['type'] else "Entity"
                    connections.append(f"{record['source']} --{record['relation']}--> {record['target']} ({target_type})")
                return connections
        except Exception as e:
            logger.warning(f"Graph Search Error: {e}")
            return []

    def get_case_graph(self, case_id: str) -> Dict[str, List]:
        """
        Retrieves the full knowledge graph for a specific case.
        Returns strict Node/Link structure for React 2D Graph.
        """
        self._connect()
        if not self._driver: return {"nodes": [], "links": []}

        # 1. Find Documents for Case
        # 2. Find Entities linked to those Documents
        # 3. Find relationships between those entities
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
                    # 1. Document Node (The Center)
                    doc_node = record['d']
                    if doc_node:
                        # Use element_id (Neo4j 5) or id (older)
                        doc_id = getattr(doc_node, "element_id", str(doc_node.id))
                        # Or rely on the property 'id' we set
                        doc_prop_id = doc_node.get("id", doc_id)
                        
                        if doc_prop_id not in nodes:
                            nodes[doc_prop_id] = {
                                "id": doc_prop_id,
                                "name": "DOKUMENTI",
                                "group": "DOCUMENT",
                                "val": 20 # Size
                            }
                    
                    # 2. Target Node (The Entity)
                    target = record['target']
                    rel = record['r']
                    
                    if target and rel:
                        target_id = getattr(target, "element_id", str(target.id))
                        # Prefer name as ID for visualization stability if unique, else use element_id
                        # Here using element_id for uniqueness
                        
                        target_labels = list(target.labels)
                        group_type = target_labels[0] if target_labels else "Entity"
                        target_name = target.get("name", "Unknown")
                        
                        # Use name as ID to merge same entities across docs? 
                        # Better to use a unique key. Let's use the DB ID.
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
                            "label": type(rel).__name__ # Relationship type
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