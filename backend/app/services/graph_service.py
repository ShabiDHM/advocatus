# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH SERVICE V9.0 (UNIVERSAL DELETION & ORPHAN SWEEP)
# 1. UPGRADE: Added delete_node() with Universal ID Matching (Case, Document).
# 2. HYGIENE: Implemented specific orphan cleanup for Judges, Courts, and Persons.
# 3. SYNC: Ensures Neo4j stays perfectly aligned with MongoDB deletions.

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
        except Exception as e:
            logger.error(f"❌ Neo4j Connection Failed: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()

    # ==============================================================================
    # SECTION 1: MAINTENANCE & DELETION (V9 UPGRADE)
    # ==============================================================================

    def delete_node(self, node_id: str):
        """
        Universally removes a node (Case or Document) and cleans up resulting orphans.
        Called by API endpoints when deleting items from MongoDB.
        """
        self._connect()
        if not self._driver: return

        try:
            with self._driver.session() as session:
                # 1. Delete the target node (Document or Case context)
                session.run("""
                    MATCH (n) 
                    WHERE n.id = $id 
                       OR n.case_id = $id 
                       OR n.documentId = $id
                    DETACH DELETE n
                """, id=node_id)
                
                # 2. Targeted Orphan Sweep (Don't leave stray Judges/People)
                self._cleanup_orphans(session)
                
            logger.info(f"🗑️ Deleted Graph Node {node_id} and cleaned orphans")
        except Exception as e:
            logger.error(f"Graph Deletion Failed: {e}")

    def delete_document_nodes(self, document_id: str):
        """Legacy wrapper for backward compatibility"""
        self.delete_node(document_id)

    def _cleanup_orphans(self, session):
        """
        Removes secondary nodes that have lost all connections.
        Targeting: Person, Judge, Court, Claim, Evidence, Entity.
        """
        query = """
        MATCH (n)
        WHERE (n:Person OR n:Judge OR n:Court OR n:Claim OR n:Evidence OR n:Entity)
          AND NOT (n)--()
        DELETE n
        """
        session.run(query)

    # ==============================================================================
    # SECTION 2: VISUALIZATION
    # ==============================================================================

    def get_case_graph(self, case_id: str) -> Dict[str, List]:
        self._connect()
        if not self._driver: return {"nodes": [], "links": []}
        
        query = """
        MATCH (d:Document {case_id: $case_id})
        OPTIONAL MATCH (d)-[:MENTIONS|ISSUED_BY]->(e)
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
                    n, m, r = record['n'], record['m'], record['r']
                    
                    for node_obj in [n, m]:
                        if node_obj:
                            nid = node_obj.get("id", node_obj.get("name"))
                            if nid and nid not in nodes_dict:
                                grp = node_obj.get("group", "ENTITY")
                                nodes_dict[nid] = {
                                    "id": nid,
                                    "name": node_obj.get("name", "Unknown"),
                                    "group": grp,
                                    "val": 20 if grp == 'DOCUMENT' else 8
                                }

                    if r and n and m:
                        links_list.append({
                            "source": n.get("id", n.get("name")),
                            "target": m.get("id", m.get("name")),
                            "label": r.type.replace("_", " ")
                        })

            return {"nodes": list(nodes_dict.values()), "links": links_list}
        except Exception as e:
            logger.error(f"Graph Retrieval Failed: {e}")
            return {"nodes": [], "links": []}

    # ==============================================================================
    # SECTION 3: DATA INGESTION
    # ==============================================================================

    def ingest_entities_and_relations(self, case_id: str, document_id: str, doc_name: str, entities: List[Dict], relations: List[Dict], doc_metadata: Optional[Dict] = None):
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels, meta):
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id, d.name = $doc_name, d.group = 'DOCUMENT'
            """, doc_id=d_id, case_id=c_id, doc_name=d_name)

            if meta:
                if meta.get("court"):
                    tx.run("""
                        MERGE (c:Court {name: $court_name, group: 'COURT'})
                        MERGE (d:Document {id: $doc_id})
                        MERGE (d)-[:ISSUED_BY]->(c)
                    """, court_name=meta["court"], doc_id=d_id)
                if meta.get("judge"):
                    tx.run("""
                        MERGE (j:Judge {name: $judge_name, group: 'JUDGE'})
                        MERGE (d:Document {id: $doc_id})
                        MERGE (d)-[:MENTIONS]->(j)
                    """, judge_name=meta["judge"], doc_id=d_id)
                if meta.get("case_number"):
                    tx.run("""
                        MERGE (cn:CaseNumber {name: $case_num, group: 'CASE_NUMBER'})
                        MERGE (d:Document {id: $doc_id})
                        MERGE (d)-[:MENTIONS]->(cn)
                    """, case_num=meta["case_number"], doc_id=d_id)

            for ent in ents:
                raw_label = ent.get("type", "Entity").strip().capitalize()
                label = "ENTITY"
                if raw_label in ["Person", "People"]: label = "PERSON"
                elif raw_label in ["Organization", "Company"]: label = "ORGANIZATION"
                elif raw_label in ["Money", "Amount"]: label = "MONEY"
                elif raw_label in ["Date", "Time"]: label = "DATE"
                
                name = ent.get("name", "").strip().title()
                if not name or len(name) < 2: continue

                tx.run(f"""
                MERGE (e:{label} {{name: $name}})
                ON CREATE SET e.group = '{label}'
                MERGE (d:Document {{id: $doc_id}})
                MERGE (d)-[:MENTIONS]->(e)
                """, name=name, doc_id=d_id)

            for rel in rels:
                subj = rel.get("subject", "").strip().title()
                obj = rel.get("object", "").strip().title()
                predicate = rel.get("relation", "RELATED_TO").upper().replace(" ", "_")
                if subj and obj:
                    tx.run(f"""
                    MATCH (a {{name: $subj}})
                    MATCH (b {{name: $obj}})
                    MERGE (a)-[:{predicate}]->(b)
                    """, subj=subj, obj=obj)

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, doc_name, entities, relations, doc_metadata)
        except Exception as e:
            logger.error(f"Graph Ingestion Error: {e}")

    def ingest_legal_analysis(self, case_id: str, doc_id: str, analysis: List[Dict]):
        self._connect()
        if not self._driver: return
        def _tx_ingest_legal(tx, c_id, d_id, items):
            tx.run("MERGE (d:Document {id: $d_id}) SET d.case_id = $c_id", d_id=d_id, c_id=c_id)
            for item in items:
                if item.get('type') == 'ACCUSATION':
                    accuser = item.get('source', 'Unknown').title()
                    accused = item.get('target', 'Unknown').title()
                    claim_text = item.get('text', 'Unspecified Claim')
                    tx.run("""
                    MERGE (p1:Person {name: $accuser})
                    MERGE (p2:Person {name: $accused})
                    MERGE (c:Claim {text: $claim_text, case_id: $case_id})
                    MERGE (p1)-[:ACCUSES]->(p2)
                    MERGE (p1)-[:ASSERTS]->(c)
                    MERGE (c)-[:CONCERNS]->(p2)
                    MERGE (d:Document {id: $doc_id})-[:RECORDS]->(c)
                    """, accuser=accuser, accused=accused, claim_text=claim_text, case_id=c_id, doc_id=d_id)
                elif item.get('type') == 'CONTRADICTION':
                    tx.run("""
                    MERGE (c:Claim {text: $claim_text})
                    MERGE (e:Evidence {text: $evidence_text})
                    MERGE (d:Document {id: $doc_id})-[:CONTAINS]->(e)
                    MERGE (e)-[:CONTRADICTS]->(c)
                    """, claim_text=item.get('claim_text'), evidence_text=item.get('evidence_text'), doc_id=d_id)
        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest_legal, case_id, doc_id, analysis)
            logger.info("⚖️ Legal Graph Ingestion Complete")
        except Exception as e:
            logger.error(f"Legal Ingestion Failed: {e}")

    # ==============================================================================
    # SECTION 4: INTELLIGENCE QUERIES
    # ==============================================================================

    def find_hidden_connections(self, query_term: str) -> List[str]:
        self._connect()
        if not self._driver: return []
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

    def find_contradictions(self, case_id: str) -> str:
        self._connect()
        if not self._driver: return ""
        query = """
        MATCH (e:Evidence)-[:CONTRADICTS]->(c:Claim)<-[:ASSERTS]-(p:Person)
        WHERE c.case_id = $case_id
        RETURN p.name as liar, c.text as lie, e.text as proof
        """
        try:
            with self._driver.session() as session:
                result = session.run(query, case_id=case_id)
                summary = []
                for r in result:
                    summary.append(f"⚠️ FALSE CLAIM: {r['liar']} claimed '{r['lie']}', but evidence '{r['proof']}' contradicts this.")
                return "\n".join(summary) if summary else "No direct contradictions found in the graph."
        except Exception:
            return ""

    def get_accusation_chain(self, person_name: str) -> List[str]:
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

# Global Instance
graph_service = GraphService()