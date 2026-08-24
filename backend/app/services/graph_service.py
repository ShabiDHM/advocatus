# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTELLIGENCE V33.0 (ZERO IMPORT ERRORS • DUAL NEO4J & MONGODB ENGINE)

import os
import time
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo.database import Database
from neo4j import GraphDatabase, Driver, basic_auth

from app.core.config import settings

logger = logging.getLogger(__name__)

NEO4J_URI = getattr(settings, "NEO4J_URI", None) or os.getenv("NEO4J_URI", "") or os.getenv("NEO4J_URL", "")
NEO4J_USER = getattr(settings, "NEO4J_USER", None) or os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = getattr(settings, "NEO4J_PASSWORD", None) or os.getenv("NEO4J_PASSWORD", "")


def normalize_text_to_albanian(text: str) -> str:
    """Helper function imported by graph_router."""
    return text.strip() if text else ""


class GraphService:
    _driver: Optional[Driver] = None
    _connection_failed_until: float = 0.0

    def _get_db(self) -> Database:
        from app.core.db import get_db_instance
        return get_db_instance()

    def _connect(self):
        """Lidhet me Neo4j Aura Cloud me protokoll të sigurt neo4j+s://"""
        if time.time() < self._connection_failed_until:
            return

        if self._driver:
            return

        uri = NEO4J_URI.strip()
        if not uri or uri in ["bolt://neo4j:7687", "REPLACE_WITH_AURA_URI"]:
            return

        try:
            self._driver = GraphDatabase.driver(
                uri,
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=30 * 60
            )
            self._driver.verify_connectivity()
            logger.info("✅ [Neo4j Aura Cloud] Connected and Verified Successfully!")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j Aura connection fallback to MongoDB: {e}")
            self._driver = None
            self._connection_failed_until = time.time() + 60

    def create_evidence_edge(self, case_id: str, source_id: str, target_id: str, relation: str, properties: Dict[str, Any]):
        """Krijon nyjen dhe lidhjen në Neo4j Aura dhe në MongoDB."""
        self._connect()

        clean_rel = re.sub(r'[^A-Z0-9_]', '_', relation.upper().replace(" ", "_")) or "LIDHJE_LIGJORE"
        evidence_text = properties.get("evidence_text", "")
        amount_eur = properties.get("amount_eur")
        date_iso = properties.get("date_iso", "")

        # 1. Nëse Neo4j Aura është aktiv, ruaj në Neo4j
        if self._driver:
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
                logger.error(f"Neo4j edge error: {e}")

        # 2. Ruaj gjithashtu në MongoDB për sinkronizim të dyfishtë
        db = self._get_db()
        edge = {
            "id": str(uuid.uuid4()),
            "source": source_id,
            "target": target_id,
            "relation": clean_rel,
            "evidence_text": evidence_text,
            "amount_eur": amount_eur,
            "date_iso": date_iso
        }
        db.case_graphs.update_one(
            {"case_id": case_id},
            {"$push": {"edges": edge}},
            upsert=True
        )

    def get_case_graph(self, case_id: str) -> Dict[str, Any]:
        """
        Kthen grafin nga Neo4j Aura ose nga MongoDB me strukturën e saktë 'nodes' dhe 'edges'.
        """
        self._connect()

        # 1. Nëse Neo4j Aura është aktiv, lexo direkt nga Neo4j
        if self._driver:
            nodes_dict = {}
            edges_list = []
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
                                    raw_label = list(node.labels)[0] if node.labels else "PERSON"
                                    nodes_dict[n_id] = {
                                        "id": n_id,
                                        "label": node.get('name') or node.get('label') or n_id,
                                        "type": raw_label.upper(),
                                        "description": node.get('description', ''),
                                        "val": 20
                                    }
                        
                        if r and n and m:
                            n_source = str(n.get("id") or n.element_id)
                            m_target = str(m.get("id") or m.element_id)
                            edges_list.append({
                                "id": str(r.id if hasattr(r, 'id') else uuid.uuid4()),
                                "source": n_source,
                                "target": m_target,
                                "relation": type(r).__name__.replace("_", " "),
                                "evidence_text": r.get("evidence_text", ""),
                                "date_iso": r.get("date_iso", ""),
                                "amount_eur": r.get("amount_eur")
                            })

                if nodes_dict:
                    return {
                        "nodes": list(nodes_dict.values()),
                        "edges": edges_list,
                        "links": edges_list
                    }
            except Exception as e:
                logger.error(f"Neo4j Aura Fetch Error: {e}")

        # 2. Fallback i menjëhershëm nga MongoDB
        db = self._get_db()
        graph_rec = db.case_graphs.find_one({"case_id": case_id})

        if graph_rec and graph_rec.get("nodes") and len(graph_rec["nodes"]) > 0:
            return {
                "nodes": graph_rec.get("nodes", []),
                "edges": graph_rec.get("edges", []),
                "links": graph_rec.get("edges", [])
            }

        # 3. Gjenero automatikisht nga shkresat e MongoDB-së
        return self._generate_from_documents(case_id)

    def _generate_from_documents(self, case_id: str) -> Dict[str, Any]:
        db = self._get_db()
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        case = db.cases.find_one({"_id": c_oid}) or {}
        client_name = case.get("client_name") or case.get("client", {}).get("name") or "Pala Kliente"
        opposing_name = case.get("opposing_party") or case.get("opponent") or "Pala Kundërshtare"
        case_title = case.get("title") or case.get("case_name") or "Lënda Ligjore"

        nodes_dict: Dict[str, Dict[str, Any]] = {}
        edges_list: List[Dict[str, Any]] = []

        root_id = "trungu_i_lendes"
        nodes_dict[root_id] = {
            "id": root_id,
            "label": case_title,
            "type": "TRUNGU_I_LENDES",
            "description": f"Dosja: {case_title}",
            "metadata": {"is_root": True}
        }

        client_id = "klienti_kryesor"
        nodes_dict[client_id] = {
            "id": client_id,
            "label": client_name,
            "type": "PERSON",
            "description": "Klienti ynë"
        }
        edges_list.append({
            "id": str(uuid.uuid4()),
            "source": root_id,
            "target": client_id,
            "relation": "PËRFAQËSON",
            "evidence_text": client_name
        })

        if opposing_name and opposing_name != "Pala Kundërshtare":
            opp_id = "pala_kundershtare"
            nodes_dict[opp_id] = {
                "id": opp_id,
                "label": opposing_name,
                "type": "PERSON",
                "description": "Pala kundërshtare"
            }
            edges_list.append({
                "id": str(uuid.uuid4()),
                "source": client_id,
                "target": opp_id,
                "relation": "KONFLIKT_GJYQËSOR",
                "evidence_text": f"{client_name} vs {opposing_name}"
            })

        doc_cursor = db.documents.find({
            "$or": [{"case_id": case_id}, {"case_id": c_oid}],
            "status": {"$ne": "DELETED"}
        })
        for idx, doc in enumerate(doc_cursor, 1):
            doc_id = str(doc["_id"])
            doc_name = doc.get("file_name") or doc.get("title") or f"Dokument #{idx}"
            summary = doc.get("summary") or doc.get("extracted_text", "")[:250]
            node_type = "EVIDENCE" if any(k in doc_name.lower() for k in ["test", "raport", "ekspertiz", "audio", "video"]) else "DOCUMENT"

            nodes_dict[doc_id] = {
                "id": doc_id,
                "label": doc_name,
                "type": node_type,
                "description": summary
            }
            edges_list.append({
                "id": str(uuid.uuid4()),
                "source": root_id,
                "target": doc_id,
                "relation": "ADMINISTRUAR",
                "evidence_text": doc_name
            })

        graph_payload = {
            "case_id": case_id,
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
            "links": edges_list,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        db.case_graphs.update_one({"case_id": case_id}, {"$set": graph_payload}, upsert=True)
        return graph_payload

    def delete_case_nodes(self, case_id: str):
        self._connect()
        if self._driver:
            try:
                with self._driver.session() as session:
                    session.run("MATCH (n {case_id: $id}) DETACH DELETE n", id=case_id)
            except Exception as e:
                logger.warning(f"Neo4j delete error: {e}")

        db = self._get_db()
        db.case_graphs.delete_many({"case_id": case_id})

graph_service = GraphService()