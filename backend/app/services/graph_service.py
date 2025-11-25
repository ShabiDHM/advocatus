# FILE: backend/app/services/graph_service.py
# PHOENIX PROTOCOL - GRAPH INTERFACE (SYNTAX FIXED)
# 1. FIX: Corrected Cypher query syntax inside Python f-strings.
# 2. SAFETY: Added optional chaining for driver.

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
        # Lazy connection on first use
        pass

    def _connect(self):
        if self._driver: return
        try:
            self._driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Verify connection
            self._driver.verify_connectivity()
            logger.info("✅ Connected to Neo4j Graph Database.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()

    def ingest_entities_and_relations(self, case_id: str, document_id: str, entities: List[Dict], relations: List[Dict]):
        """
        Creates nodes and relationships from AI-extracted data.
        """
        self._connect()
        if not self._driver: return

        def _tx_ingest(tx, c_id, d_id, ents, rels):
            # 1. Create Document Node
            tx.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.case_id = $case_id
            """, doc_id=d_id, case_id=c_id)

            # 2. Create Entities
            for ent in ents:
                label = ent.get("type", "Entity").capitalize()
                name = ent.get("name", "").strip()
                if not name: continue
                
                allowed_labels = ["Person", "Organization", "Location", "Date", "Money", "Law", "Entity"]
                if label not in allowed_labels: label = "Entity"

                # Use string interpolation for label (Cypher limitation), but safe due to allow-list above
                query = f"""
                MERGE (e:{label} {{name: $name}})
                MERGE (d:Document {{id: $doc_id}})
                MERGE (d)-[:MENTIONS]->(e)
                """
                tx.run(query, name=name, doc_id=d_id)

            # 3. Create Relationships
            for rel in rels:
                subj = rel.get("subject", "").strip()
                obj = rel.get("object", "").strip()
                predicate = rel.get("relation", "RELATED_TO").upper().replace(" ", "_")
                
                if not subj or not obj: continue

                # CORRECTED SYNTAX: Removed double brackets
                query = f"""
                MATCH (a {{name: $subj}})
                MATCH (b {{name: $obj}})
                MERGE (a)-[:{predicate}]->(b)
                """
                try:
                    tx.run(query, subj=subj, obj=obj)
                except Exception as e:
                    logger.warning(f"Graph Rel Error: {e}")

        try:
            with self._driver.session() as session:
                session.execute_write(_tx_ingest, case_id, document_id, entities, relations)
            logger.info(f"🕸️  Graph Ingestion Complete: {len(entities)} Entities, {len(relations)} Relations.")
        except Exception as e:
            logger.error(f"Graph Transaction Failed: {e}")

    def find_hidden_connections(self, query_entity: str) -> List[str]:
        """
        Finds indirect connections. 
        """
        self._connect()
        if not self._driver: return []
        
        query = """
        MATCH (a {name: $name})-[r]-(b)
        RETURN type(r) as relation, b.name as target, labels(b) as type
        LIMIT 10
        """
        try:
            with self._driver.session() as session:
                result = session.run(query, name=query_entity)
                connections = []
                for record in result:
                    target_type = record['type'][0] if record['type'] else "Entity"
                    connections.append(f"{record['relation']} -> {record['target']} ({target_type})")
                return connections
        except Exception:
            return []

# Global Instance
graph_service = GraphService()