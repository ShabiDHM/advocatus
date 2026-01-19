# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTELLIGENCE V2.3 (VISUALIZATION ENABLED)
# 1. FIX: Added missing 'get_case_graph' method to support frontend visualization.
# 2. FEATURE: Queries Neo4j for Document->Entity mentions and Case-specific relationships.
# 3. STATUS: Fully compatible with 'graph.py' router.

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
            self._driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))
            self._driver.verify_connectivity()
        except Exception as e:
            logger.error(f"❌ Neo4j Connection Failed: {e}")
            self._driver = None

    def close(self):
        if self._driver: self._driver.close()

    # ==============================================================================
    # VISUALIZATION (Frontend Data)
    # ==============================================================================

    def get_case_graph(self, case_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves the 2D Node/Link structure for the specific case.
        Used by the 'Detective Board' visualization.
        """
        self._connect()
        if not self._driver: 
            return {"nodes": [], "links": []}
        
        nodes_dict = {}
        links_list = []
        
        # 1. Fetch Documents and their Entity Mentions
        query_docs = """
        MATCH (d:Document {case_id: $case_id})
        OPTIONAL MATCH (d)-[:MENTIONS]->(e)
        RETURN d, e
        """
        
        # 2. Fetch Semantic Relationships explicitly tagged with this case
        query_rels = """
        MATCH (a)-[r]->(b)
        WHERE r.case_id = $case_id
        RETURN a, type(r) as label, b
        """
        
        try:
            with self._driver.session() as session:
                # Execution 1: Documents & Mentions
                res1 = session.run(query_docs, case_id=case_id)
                for record in res1:
                    d = record['d']
                    e = record['e']
                    
                    # Add Document Node
                    # Use 'id' prop if available, else Neo4j internal element_id
                    d_id = d.get('id') or str(d.element_id)
                    if d_id not in nodes_dict:
                        nodes_dict[d_id] = {
                            "id": d_id, 
                            "name": d.get('name', 'Doc'), 
                            "group": "DOCUMENT", 
                            "val": 20
                        }
                    
                    # Add Entity Node & Link
                    if e:
                        e_id = str(e.element_id)
                        if e_id not in nodes_dict:
                            # Use the first label as the group (e.g., Person, Organization)
                            grp = list(e.labels)[0] if e.labels else "ENTITY"
                            nodes_dict[e_id] = {
                                "id": e_id, 
                                "name": e.get('name', 'Unknown'), 
                                "group": grp, 
                                "val": 10
                            }
                        
                        links_list.append({"source": d_id, "target": e_id, "label": "MENTIONS"})

                # Execution 2: Relationships (Person -> Person, etc.)
                res2 = session.run(query_rels, case_id=case_id)
                for record in res2:
                    a = record['a']
                    b = record['b']
                    lbl = record['label']
                    
                    a_id = str(a.element_id)
                    b_id = str(b.element_id)
                    
                    # Ensure nodes exist (safety check)
                    for node, nid in [(a, a_id), (b, b_id)]:
                        if nid not in nodes_dict:
                            grp = list(node.labels)[0] if node.labels else "ENTITY"
                            nodes_dict[nid] = {
                                "id": nid, 
                                "name": node.get('name', 'Unknown'), 
                                "group": grp, 
                                "val": 10
                            }
                            
                    links_list.append({"source": a_id, "target": b_id, "label": lbl})
                    
        except Exception as e:
            logger.error(f"Graph Fetch Error: {e}")
            return {"nodes": [], "links": []}
            
        return {"nodes": list(nodes_dict.values()), "links": links_list}

    # ==============================================================================
    # INTELLIGENCE QUERIES (The "Invisible" Brain)
    # ==============================================================================

    def get_strategic_context(self, case_id: str) -> str:
        """
        Aggregates all graph insights into a text summary for the LLM.
        """
        self._connect()
        if not self._driver: return ""
        
        insights = []
        
        # 1. Conflict of Interest Scan
        conflicts = self._find_hidden_conflicts(case_id)
        if conflicts:
            insights.append(f"⚠️ GRAPH WARNING (CONFLICTS): {'; '.join(conflicts)}")
            
        # 2. Financial Web Scan
        money_flows = self._trace_money_flows(case_id)
        if money_flows:
            insights.append(f"💰 MONEY TRAIL: {'; '.join(money_flows)}")
            
        # 3. Central Actors
        key_players = self._identify_central_actors(case_id)
        if key_players:
            insights.append(f"👥 KEY ACTORS (Graph Centrality): {', '.join(key_players)}")

        return "\n".join(insights)

    def _find_hidden_conflicts(self, case_id: str) -> List[str]:
        if not self._driver: return []
        query = """
        MATCH (p1:Person)-[:ACCUSES|:KUNDËRSHTON]->(p2:Person)
        MATCH (p1)-[:RELATION*1..2]-(common)-[:RELATION*1..2]-(p2)
        WHERE common.group <> 'CASE_NUMBER' AND common.group <> 'COURT'
        RETURN p1.name, p2.name, common.name
        """
        results = []
        try:
            with self._driver.session() as session:
                res = session.run(query)
                for r in res:
                    results.append(f"{r['p1.name']} and {r['p2.name']} share a hidden link via '{r['common.name']}'")
        except Exception: return []
        return results

    def _trace_money_flows(self, case_id: str) -> List[str]:
        if not self._driver: return []
        query = """
        MATCH (a)-[r:ALIMENTACION|BORXH|PAGUAN|FINANCE]->(b)
        WHERE a.case_id = $case_id OR r.case_id = $case_id
        RETURN a.name, type(r), b.name
        """
        results = []
        try:
            with self._driver.session() as session:
                res = session.run(query, case_id=case_id)
                for r in res:
                    results.append(f"{r['a.name']} -> {r['type(r)']} -> {r['b.name']}")
        except Exception: return []
        return results

    def _identify_central_actors(self, case_id: str) -> List[str]:
        if not self._driver: return []
        query = """
        MATCH (n:Person)-[:MENTIONS]-(d:Document {case_id: $case_id})
        RETURN n.name, count(d) as docs
        ORDER BY docs DESC
        LIMIT 3
        """
        results = []
        try:
            with self._driver.session() as session:
                res = session.run(query, case_id=case_id)
                for r in res:
                    results.append(f"{r['n.name']} ({r['docs']} docs)")
        except Exception: return []
        return results

    # ==============================================================================
    # CRUD & SYNC OPERATIONS
    # ==============================================================================

    def ingest_entities_and_relations(self, case_id: str, document_id: str, doc_name: str, entities: List[Dict], relations: List[Dict]):
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            tx.run("MERGE (d:Document {id: $d_id}) SET d.case_id = $c_id, d.name = $d_name", d_id=d_id, c_id=c_id, d_name=d_name)
            
            for ent in ents:
                name = ent.get("name", "").strip().title()
                if len(name) < 2 or name.lower() in ['unknown', 'n/a']: continue
                label = "Person" if ent.get("type") in ["Person", "People"] else "Entity"
                tx.run(f"MERGE (e:{label} {{name: $name}}) MERGE (d:Document {{id: $d_id}})-[:MENTIONS]->(e)", name=name, d_id=d_id)

            for rel in rels:
                subj, obj = rel.get("subject"), rel.get("object")
                if subj and obj:
                    pred = rel.get("relation", "RELATED").upper().replace(" ", "_")
                    tx.run(f"""
                        MATCH (a {{name: $subj}}), (b {{name: $obj}})
                        MERGE (a)-[:{pred} {{case_id: $c_id}}]->(b)
                    """, subj=subj, obj=obj, c_id=c_id)

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, doc_name, entities, relations)
        except Exception as e:
            logger.error(f"Graph Ingestion Error: {e}")

    def delete_node(self, node_id: str):
        """
        Deletes a specific node (Document or Case) by its ID and detaches relationships.
        """
        self._connect()
        if not self._driver: return
        query = "MATCH (n {id: $id}) DETACH DELETE n"
        try:
            with self._driver.session() as session:
                session.run(query, id=node_id)
        except Exception as e:
            logger.error(f"Graph Delete Error (Node {node_id}): {e}")

    def delete_document_nodes(self, doc_id: str):
        self.delete_node(doc_id)

graph_service = GraphService()