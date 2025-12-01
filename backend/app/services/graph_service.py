# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH MASTER V4.1
# 1. NORMALIZATION: Auto-capitalizes names to prevent duplicates (e.g., "agim" -> "Agim").
# 2. DEPTH: 'find_hidden_connections' now searches 2 degrees of separation.
# 3. SCHEMA: Enforces strict labels (Person, Org, etc.) for better visualization colors.

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
        Removes a document and cleans up orphaned entities.
        """
        self._connect()
        if not self._driver: return

        query = """
        MATCH (d:Document {id: $doc_id})
        DETACH DELETE d
        """
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
        """
        Creates nodes/relationships. Uses MERGE to prevent duplicates.
        """
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            # 1. Document Node (The Anchor)
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id, d.name = $doc_name
            """, doc_id=d_id, case_id=c_id, doc_name=d_name)

            # 2. Entities (With Normalization)
            for ent in ents:
                # Normalize Label
                raw_label = ent.get("type", "Entity").capitalize()
                allowed_labels = ["Person", "Organization", "Location", "Date", "Money", "Law", "Entity"]
                label = raw_label if raw_label in allowed_labels else "Entity"
                
                # Normalize Name (Title Case to merge "agim" and "Agim")
                name = ent.get("name", "").strip().title()
                if not name or len(name) < 2: continue

                # Create Entity and Link to Doc
                query = f"""
                MERGE (e:{label} {{name: $name}})
                MERGE (d:Document {{id: $doc_id}})
                MERGE (d)-[:MENTIONS]->(e)
                """
                tx.run(query, name=name, doc_id=d_id)

            # 3. Relationships (Subject -> Object)
            for rel in rels:
                subj = rel.get("subject", "").strip().title()
                obj = rel.get("object", "").strip().title()
                # Normalize Predicate (e.g., "signed contract" -> "SIGNED_CONTRACT")
                predicate = rel.get("relation", "RELATED_TO").upper().replace(" ", "_")
                
                if not subj or not obj: continue

                # We search for ANY node with this name, regardless of label
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
            logger.info(f"🕸️ Graph Ingestion Complete: {len(entities)} Entities.")
        except Exception as e:
            logger.error(f"Graph Transaction Failed: {e}")

    def find_hidden_connections(self, query_term: str) -> List[str]:
        """
        Finds direct and 2-hop connections. 
        Example: "Agim" -> Signed -> "Contract" -> Mentioned -> "Company X"
        """
        self._connect()
        if not self._driver: return []
        
        # PHOENIX UPGRADE: 2-Hop Search
        query = """
        MATCH (start)-[r1]-(mid)-[r2]-(end)
        WHERE toLower(start.name) CONTAINS toLower($term)
        RETURN start.name, type(r1), mid.name, type(r2), end.name
        LIMIT 10
        """
        
        # Fallback for direct connections if 2-hop is empty or too slow
        direct_query = """
        MATCH (a)-[r]-(b)
        WHERE toLower(a.name) CONTAINS toLower($term)
        RETURN a.name, type(r), b.name, labels(b) as type
        LIMIT 10
        """
        
        connections = []
        try:
            with self._driver.session() as session:
                # 1. Try Deep Search first
                result = session.run(query, term=query_term)
                for record in result:
                    # Format: "Agim --SIGNED--> Contract --OWNED_BY--> Company"
                    connections.append(
                        f"{record['start.name']} --{record['type(r1)']}--> {record['mid.name']} --{record['type(r2)']}--> {record['end.name']}"
                    )
                
                # 2. Get Direct connections to fill gaps
                res_direct = session.run(direct_query, term=query_term)
                for rec in res_direct:
                    target_type = rec['type'][0] if rec['type'] else "Entity"
                    connections.append(f"{rec['a.name']} --{rec['type(r)']}--> {rec['b.name']} ({target_type})")
                    
                return list(set(connections)) # Deduplicate
        except Exception as e:
            logger.warning(f"Graph Search Error: {e}")
            return []

    def get_case_graph(self, case_id: str) -> Dict[str, List]:
        """
        Visualization Query. Returns Document nodes and their 1-hop neighbors.
        """
        self._connect()
        if not self._driver: return {"nodes": [], "links": []}

        # Optimized Query: Find Documents in Case, then find everything connected to them.
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
                    if not doc_node: continue
                    
                    # Neo4j 5.x uses element_id
                    d_id = getattr(doc_node, "element_id", str(doc_node.id))
                    # We stored the real UUID in property 'id'
                    doc_uuid = doc_node.get("id", d_id)
                    
                    if doc_uuid not in nodes:
                        nodes[doc_uuid] = {
                            "id": doc_uuid,
                            "name": doc_node.get("name", "Document"),
                            "group": "DOCUMENT",
                            "val": 25 # Size
                        }
                    
                    # 2. Target Entity
                    target = record['target']
                    rel = record['r']
                    
                    if target and rel:
                        # Target UUID strategy: Use name as ID for entities to merge them visually
                        # Or use element_id if we want strict graph separation. 
                        # Using 'name' merges "Agim" from Doc A and "Agim" from Doc B -> ONE NODE (Better)
                        target_name = target.get("name", "Unknown")
                        t_id = target_name # Visual Merge
                        
                        target_labels = list(target.labels)
                        # Filter out internal labels if any
                        lbl = target_labels[0] if target_labels else "Entity"
                        
                        if t_id not in nodes:
                            nodes[t_id] = {
                                "id": t_id,
                                "name": target_name,
                                "group": lbl.upper(), # 'PERSON', 'ORG'
                                "val": 10
                            }
                        
                        links.append({
                            "source": doc_uuid,
                            "target": t_id,
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