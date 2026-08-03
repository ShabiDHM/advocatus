# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTELLIGENCE V5.0 (NEO4J AURA CLOUD & 100% ALBANIAN INGESTION ENGINE)

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

# TRILINGUAL TO ALBANIAN DICTIONARY FOR DATABASE INGESTION
GERMAN_ENGLISH_TO_ALBANIAN_MAP = {
  "IMPLEMENTED_BY": "ZBATUAR_NGA",
  "IMPLEMENTED": "ZBATUAR_NGA",
  "CONTRACTED_BY": "KONTRAKTUAR_NGA",
  "CONTRACTED": "KONTRAKTUAR_ME",
  "CONTRACTED_WITH": "KONTRAKTUAR_ME",
  "REPRESENTED_BY": "PËRFAQËSOHET_NGA",
  "REPRESENTS": "PËRFAQËSON",
  "ASSOCIATED_WITH": "LIDHUR_ME",
  "ASSOCIATED": "LIDHUR_ME",
  "TRANSFERRED_FUNDS": "TRANSAKSION_FINANCIAR",
  "TRANSFER_FUNDS": "TRANSAKSION_FINANCIAR",
  "PAID_TO": "PAGESË_NDAJ",
  "PAYMENT": "PAGESË_FINANCIARE",
  "EMPLOYED_BY": "I_PUNËSUAR_NË",
  "WORKED_AT": "I_PUNËSUAR_NË",
  "EMPLOYEE": "I_PUNËSUAR_NË",
  "OWNED_BY": "PRONËSI_E",
  "OWNS": "PRONËSI_E",
  "OWNER": "PRONAR_NË",
  "PRESENT_AT": "PRANISHËM_NË",
  "LOCATED_AT": "VENDNDODHJA",
  "LOCATED_IN": "VENDNDODHJA",
  "CONTRADICTS": "KUNDËRTHËNIE_ME_PROVËN",
  "OWES_MONEY": "DETYRIM_FINANCIAR",
  "SIGNED": "NËNSHKRUAR_NGA",
  "SIGNED_BY": "NËNSHKRUAR_NGA",
  "MENTIONED_IN": "PËRMENDUR_NË_SHKRESË",
  "HAS_ACCOUNT": "LLOGARI_BANKARE",
  "PARTY_TO": "PALË_NË_KONTRAKT",
  "ISSUED_BY": "LËSHUAR_NGA",
  "FINANCED_BY": "FINANCUAR_NGA",
  "SUBMITTED_TO": "DORËZUAR_NË"
}

def normalize_text_to_albanian(text: str) -> str:
    """Translates and cleans English/German legal phrases into standard Albanian prior to DB storage."""
    if not text:
        return ""
    
    t = text
    t = re.sub(r'\bis mentioned as Consultant in the\b', 'përmendet si Konsulent në', t, flags=re.IGNORECASE)
    t = re.sub(r'\bis mentioned as Consultant in\b', 'përmendet si Konsulent në', t, flags=re.IGNORECASE)
    t = re.sub(r'\bis mentioned as\b', 'përmendet si', t, flags=re.IGNORECASE)
    t = re.sub(r'\bis mentioned in the\b', 'përmendet në', t, flags=re.IGNORECASE)
    t = re.sub(r'\bis mentioned in\b', 'përmendet në', t, flags=re.IGNORECASE)
    t = re.sub(r'\bFreelance Contract\b', 'Kontratë Shërbimi (Freelance)', t, flags=re.IGNORECASE)
    t = re.sub(r'\bService Contract\b', 'Kontratë Shërbimi', t, flags=re.IGNORECASE)
    t = re.sub(r'\bEmployment Contract\b', 'Kontratë Pune', t, flags=re.IGNORECASE)
    t = re.sub(r'\bDienstleistungsvertrag\b', 'Kontratë Shërbimi', t, flags=re.IGNORECASE)
    t = re.sub(r'\bAuftragnehmer\b', 'Kontraktuesi', t, flags=re.IGNORECASE)
    t = re.sub(r'\bAuftraggeber\b', 'Porositësi / Punëdhënësi', t, flags=re.IGNORECASE)
    t = re.sub(r'\bDurchführungspartner\b', 'Partner i Zbatimit', t, flags=re.IGNORECASE)
    t = re.sub(r'\bBerater\b', 'Konsulent', t, flags=re.IGNORECASE)
    t = re.sub(r'\bImplemented by\b', 'Zbatuar nga', t, flags=re.IGNORECASE)
    t = re.sub(r'\bContracted by\b', 'Kontraktuar nga', t, flags=re.IGNORECASE)
    t = re.sub(r'\bSigned by\b', 'Nënshkruar nga', t, flags=re.IGNORECASE)
    t = re.sub(r'\bSubmitted to\b', 'Dorëzuar në', t, flags=re.IGNORECASE)
    
    return t.strip()

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
                                raw_label = list(node.labels)[0] if node.labels else "PERSONA"
                                
                                # Map category labels to Kosovo Shqip standards
                                group_map = {
                                    "PERSON": "PERSONA",
                                    "PARTY": "PERSONA",
                                    "ORGANIZATION": "INSTITUCIONE",
                                    "COMPANY": "INSTITUCIONE",
                                    "ACCOUNT": "LLOGARI BANKARE",
                                    "DOCUMENT": "DOKUMENTE & PROVAT",
                                    "EVIDENCE": "DOKUMENTE & PROVAT",
                                    "LOCATION": "LOKACIONE",
                                    "EVENT": "NGJARJE / SEANCA",
                                    "CLAIM": "NGJARJE / SEANCA"
                                }
                                group_clean = group_map.get(raw_label.upper(), "INSTITUCIONE")

                                name_clean = normalize_text_to_albanian(node.get('name', 'N/A'))
                                desc_clean = normalize_text_to_albanian(node.get('description', ''))

                                nodes_dict[n_id] = {
                                    "id": n_id,
                                    "name": name_clean,
                                    "group": group_clean,
                                    "description": desc_clean,
                                    "val": 25 if group_clean == "DOKUMENTE & PROVAT" else 15
                                }
                    
                    if r and n and m:
                        raw_rel = type(r).__name__.upper().replace(" ", "_")
                        clean_rel = GERMAN_ENGLISH_TO_ALBANIAN_MAP.get(raw_rel, raw_rel)
                        links_list.append({
                            "source": str(n.element_id),
                            "target": str(m.element_id),
                            "label": clean_rel.replace("_", " ")
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
        """Robust ingestion with 100% Albanian text normalization."""
        self._connect()
        if not self._driver:
            return

        def _tx_ingest(tx, c_id, d_id, d_name, ents, rels):
            tx.run(
                "MERGE (d:Document {id: $d_id}) SET d.case_id = $c_id, d.name = $d_name, d.processed_at = datetime()", 
                d_id=d_id, c_id=c_id, d_name=normalize_text_to_albanian(d_name)
            )
            
            for ent in ents:
                raw_name = (ent.get("name") or ent.get("label") or "").strip()
                if not raw_name:
                    continue
                
                name = normalize_text_to_albanian(raw_name)
                desc = normalize_text_to_albanian(ent.get("description", ""))
                
                raw_type = str(ent.get("type", "Entity")).lower()
                if "person" in raw_type or "persona" in raw_type or "individ" in raw_type:
                    label = "Person"
                elif "org" in raw_type or "company" in raw_type or "institucion" in raw_type:
                    label = "Organization"
                elif "account" in raw_type or "bank" in raw_type or "llogari" in raw_type:
                    label = "Account"
                elif "doc" in raw_type or "shkrese" in raw_type or "prove" in raw_type:
                    label = "Document"
                elif "loc" in raw_type or "vend" in raw_type:
                    label = "Location"
                else:
                    label = "Event"

                tx.run(f"""
                    MERGE (e:{label} {{name: $name, case_id: $c_id}})
                    SET e.description = $desc
                    WITH e
                    MATCH (d:Document {{id: $d_id}})
                    MERGE (d)-[:PËRMENDUR_NË_SHKRESË]->(e)
                """, name=name, c_id=c_id, d_id=d_id, desc=desc)

            for rel in rels:
                subj_raw = rel.get("source") or rel.get("subject")
                obj_raw = rel.get("target") or rel.get("object")
                if subj_raw and obj_raw:
                    subj = normalize_text_to_albanian(subj_raw)
                    obj = normalize_text_to_albanian(obj_raw)
                    
                    raw_pred = str(rel.get("relation", "LIDHUR_ME")).upper().replace(" ", "_")
                    pred = GERMAN_ENGLISH_TO_ALBANIAN_MAP.get(raw_pred, raw_pred)

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
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (n) WHERE n.id = $id OR elementId(n) = $id DETACH DELETE n", id=node_id)
        except Exception as e:
            logger.warning(f"Delete Node Error: {e}")

    def delete_document_nodes(self, document_id: str):
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (d:Document {id: $id}) DETACH DELETE d", id=document_id)
        except Exception as e:
            logger.warning(f"Delete Document Nodes Error: {e}")

    def delete_case_nodes(self, case_id: str):
        self._connect()
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run("MATCH (n) WHERE n.case_id = $id DETACH DELETE n", id=case_id)
        except Exception as e:
            logger.warning(f"Delete Case Nodes Error: {e}")

graph_service = GraphService()