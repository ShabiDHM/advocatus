# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH MASTER V5 (NETWORK INTELLIGENCE)
# 1. UPGRADE: 'get_case_graph' now fetches INTER-ENTITY connections (The "Web"), not just Document links.
# 2. VISUAL: Calculates 'val' (Node Size) dynamically based on importance (Degree Centrality).
# 3. SCHEMA: strict upper-case Grouping for easy Frontend Color mapping.

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
        """
        Removes a document and cleans up orphaned entities to keep graph clean.
        """
        self._connect()
        if not self._driver: return

        query = """
        MATCH (d:Document {id: $doc_id})
        DETACH DELETE d
        """
        # Cleanup orphans (Nodes with no relationships left)
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
        Ingests extracted data. 
        Crucial: Creates the 'MENTIONS' link from Doc to Entity, AND the 'ACTION' link between Entities.
        """
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            # 1. Document Node (The Anchor)
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id, d.name = $doc_name, d.group = 'DOCUMENT'
            """, doc_id=d_id, case_id=c_id, doc_name=d_name)

            # 2. Entities (Nodes)
            for ent in ents:
                # Normalize Label & Name
                raw_label = ent.get("type", "Entity").strip().capitalize()
                # Strict Schema for Colors
                if raw_label in ["Person", "People"]: label = "PERSON"
                elif raw_label in ["Organization", "Company", "Org"]: label = "ORGANIZATION"
                elif raw_label in ["Money", "Amount", "Currency"]: label = "MONEY"
                elif raw_label in ["Date", "Time"]: label = "DATE"
                elif raw_label in ["Location", "Place"]: label = "LOCATION"
                else: label = "ENTITY"
                
                name = ent.get("name", "").strip()
                # Capitalize generic names, keep Acronyms if detected? Simple title case is safest.
                name = name.title() 
                if not name or len(name) < 2: continue

                # Create Entity and Link to Doc
                # Note: We use the 'name' as the unique constraints usually.
                query = f"""
                MERGE (e:{label} {{name: $name}})
                ON CREATE SET e.group = '{label}'
                MERGE (d:Document {{id: $doc_id}})
                MERGE (d)-[:MENTIONS]->(e)
                """
                tx.run(query, name=name, doc_id=d_id)

            # 3. Relationships (Edges)
            for rel in rels:
                subj = rel.get("subject", "").strip().title()
                obj = rel.get("object", "").strip().title()
                
                # Predicate Normalization (e.g., "paid to" -> "PAID_TO")
                predicate = rel.get("relation", "RELATED_TO").upper().strip().replace(" ", "_")
                if len(predicate) > 20: predicate = "RELATED_TO" # Safety cap
                
                if not subj or not obj: continue

                # Search for ANY existing node with these names to link them
                query = f"""
                MATCH (a {{name: $subj}})
                MATCH (b {{name: $obj}})
                MERGE (a)-[r:{predicate}]->(b)
                """
                try:
                    tx.run(query, subj=subj, obj=obj)
                except Exception:
                    pass

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, doc_name, entities, relations)
            logger.info(f"🕸️ Graph Ingestion Complete: {len(entities)} Entities for {doc_name}")
        except Exception as e:
            logger.error(f"Graph Transaction Failed: {e}")

    def get_case_graph(self, case_id: str) -> Dict[str, List]:
        """
        The "Professional V5" Query.
        Fetches the entire connected subgraph for a case, allowing us to see 
        connections between people that don't involve the document directly.
        """
        self._connect()
        if not self._driver: return {"nodes": [], "links": []}

        # QUERY LOGIC:
        # 1. Find all Documents in this Case.
        # 2. Collect all Entities mentioned by these Documents.
        # 3. UNWIND this list to get a set of "Relevant Nodes".
        # 4. Find ALL relationships (r) where BOTH start and end nodes are in this Relevant set.
        # 5. Return everything.
        
        query = """
        MATCH (d:Document {case_id: $case_id})
        OPTIONAL MATCH (d)-[:MENTIONS]->(e)
        
        WITH collect(DISTINCT d) + collect(DISTINCT e) as nodes
        UNWIND nodes as n
        
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m IN nodes
        
        RETURN DISTINCT n, r, m
        """
        
        nodes_dict = {}
        links_list = []
        
        try:
            with self._driver.session() as session:
                result = session.run(query, case_id=case_id)
                
                for record in result:
                    n = record['n']
                    r = record['r']
                    m = record['m']
                    
                    # Process Node N
                    if n:
                        # Use Neo4j element_id or fallback 'id' property or name
                        # For Documents, we have 'id'. For Entities, 'name' is the unique key.
                        nid = n.get("id", n.get("name")) 
                        if not nid: continue
                        
                        if nid not in nodes_dict:
                            # Calculate Importance (Simple Degree Centrality Simulation)
                            # We default to 1, and increment on links later, or rely on Frontend physics
                            grp = n.get("group", "ENTITY")
                            base_size = 20 if grp == 'DOCUMENT' else 8
                            
                            nodes_dict[nid] = {
                                "id": nid,
                                "name": n.get("name", "Unknown"),
                                "group": grp,
                                "val": base_size, # Base size
                                "neighbor_count": 0
                            }
                    
                    # Process Node M (Target)
                    if m:
                        mid = m.get("id", m.get("name"))
                        if mid and mid not in nodes_dict:
                            grp = m.get("group", "ENTITY")
                            base_size = 20 if grp == 'DOCUMENT' else 8
                            nodes_dict[mid] = {
                                "id": mid,
                                "name": m.get("name", "Unknown"),
                                "group": grp,
                                "val": base_size,
                                "neighbor_count": 0
                            }

                    # Process Relationship
                    if r and n and m:
                        src = n.get("id", n.get("name"))
                        tgt = m.get("id", m.get("name"))
                        rel_type = r.type
                        
                        # Filter out basic "MENTIONS" to reduce noise? 
                        # No, user wants to see connections.
                        
                        links_list.append({
                            "source": src,
                            "target": tgt,
                            "label": rel_type.replace("_", " ") # Clean formatting "PAID_TO" -> "PAID TO"
                        })
                        
                        # Increment Centrality for Visualization Sizing
                        if src in nodes_dict: nodes_dict[src]['neighbor_count'] += 1
                        if tgt in nodes_dict: nodes_dict[tgt]['neighbor_count'] += 1

            # Post-Process: Adjust Size based on Centrality
            final_nodes = []
            for node in nodes_dict.values():
                # Documents stay large (20). Entities grow from 8 up to 30 based on connections.
                if node['group'] != 'DOCUMENT':
                    # Cap size at 30 to prevent massive bubbles
                    node['val'] = min(30, 8 + (node['neighbor_count'] * 1.5))
                
                final_nodes.append(node)

            return {
                "nodes": final_nodes,
                "links": links_list
            }

        except Exception as e:
            logger.error(f"Graph Retrieval Failed: {e}")
            return {"nodes": [], "links": []}

    def find_hidden_connections(self, query_term: str) -> List[str]:
        """
        Deep Search for Search Bar.
        """
        self._connect()
        if not self._driver: return []
        
        # Simple 1-Hop Search
        query = """
        MATCH (a)-[r]-(b)
        WHERE toLower(a.name) CONTAINS toLower($term)
        RETURN a.name, type(r), b.name
        LIMIT 15
        """
        results = []
        try:
            with self._driver.session() as session:
                res = session.run(query, term=query_term)
                for rec in res:
                    results.append(f"{rec['a.name']} --[{rec['type(r)']}]--> {rec['b.name']}")
            return list(set(results))
        except Exception:
            return []

graph_service = GraphService()